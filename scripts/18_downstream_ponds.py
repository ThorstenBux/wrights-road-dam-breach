#!/usr/bin/env python
"""EXPLORATORY: could the breach flood knock out other ponds downstream, and would that matter?

Screens every mapped pond / reservoir (OSM `natural=water`, `landuse=reservoir`) that the scenario's flood reaches,
measures its banks on the 1 m LiDAR DEM, compares them with the modelled flood level outside, and routes a
rough knock-on breach for each pond with the same level-pool code as script 03. Reads existing 2D outputs only;
it never touches the scenario outputs used by scripts 04-10.  Screening model, not a certified assessment.

Run (about a minute; fetches small 1 m LiDAR patches):
    python scripts/18_downstream_ponds.py --scenario east [--root <checkout with data/ and outputs/*.tif>]
Writes outputs/downstream_ponds/<scenario>/ponds.csv, knockon.csv, knockon_hydrographs.csv, downstream_ponds.png.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask as rmask
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, terrain  # noqa: E402
from damflood.breach import (BreachEvent, BreachGeometry, Reservoir, froehlich_1995_peak,  # noqa: E402
                             hydrograph_summary, route)

NOTE = "Screening-level estimate, not a certified assessment. Pond banks from 1 m LiDAR, volumes assumed."
MIN_AREA_M2 = 15_000      # ponds smaller than 1.5 ha are listed but not routed
OVERTOP_PCT = 5.0         # share of bank length over which the flood must top the crest to count as overtopped
FREEBOARD_M = 0.5         # 'full' case: water 0.5 m below the lowest bank crest
WET_M = 0.05              # depth that counts as flooded


def clip(path: Path, geom, band=1):
    with rasterio.open(path) as r:
        try:
            a, _ = rmask(r, [geom], crop=True, filled=True, nodata=np.nan, indexes=band)
        except ValueError:
            return np.array([])
        a = a.astype(float)
        if r.nodata is not None:
            a[a == r.nodata] = np.nan
    return a[np.isfinite(a)]


def bank_crest(dem_path: Path, poly, step=5.0, radius=12.0):
    """Crest level along the bank: at points every `step` m on the outline, the highest DEM cell within `radius`.
    Returns (points, crest levels)."""
    ring = poly.exterior
    pts, out = [], []
    for s in np.arange(0, ring.length, step):
        pt = ring.interpolate(s)
        v = clip(dem_path, pt.buffer(radius))
        if v.size:
            pts.append(pt); out.append(v.max())
    return pts, np.array(out)


class Surface:
    """Peak flood water level (burned bed + max depth) on the 2D output grid, sampled next to a bank point."""

    def __init__(self, bed_tif: Path, depth_tif: Path):
        from rasterio.warp import Resampling, reproject
        with rasterio.open(bed_tif) as b, rasterio.open(depth_tif) as d:
            dep = d.read(1).astype(float)
            self.t = d.transform
            dep[(dep < WET_M) | (dep == d.nodata)] = np.nan
            bed = np.full(dep.shape, np.nan)           # bed onto the depth grid (they differ in resolution)
            reproject(b.read(1).astype(float), bed, src_transform=b.transform, src_crs=b.crs,
                      dst_transform=d.transform, dst_crs=d.crs, resampling=Resampling.bilinear)
        self.wse = bed + dep
        self.res = abs(self.t.a)

    def within(self, zone):
        """All flood levels inside a polygon."""
        from rasterio.features import geometry_mask
        m = ~geometry_mask([zone], self.wse.shape, self.t)
        v = self.wse[m]
        return v[np.isfinite(v)]

    def next_to(self, pt, poly, reach=40.0):
        """Highest flood level within `reach` m of the bank point, outside the pond (nan if dry)."""
        v = self.within(pt.buffer(reach).difference(poly.buffer(10)))
        return float(v.max()) if v.size else np.nan


def knockon(area, surface, ground, crest, pool, invert, dt, hours):
    """Route an overtopping-type breach of a vertical-sided pond from `pool` down to `invert`."""
    if pool - invert < 0.1:
        return None
    floor = min(invert, ground) - 5.0          # below-ground part of the pond; never released
    res = Reservoir("pond", fsl=max(pool, surface), invert=floor, area_fsl=area,
                    volume_fsl=area * (max(pool, surface) - floor), crest=max(crest, pool + 0.01))
    geom = BreachGeometry.from_froehlich_2008(res, invert, "overtopping", pool_level=pool)
    r = route(BreachEvent(res, geom, initial_level=pool, start_time=0.0), t_end=hours * 3600, dt=dt)
    s = hydrograph_summary(r)
    V_w = res.volume_above(invert, pool)
    return {"peak_Q_m3s": s["peak_Q_m3s"], "time_to_peak_h": s["time_to_peak_s"] / 3600,
            "released_m3": s["volume_released_m3"], "froehlich1995_peak_m3s": froehlich_1995_peak(V_w, pool - invert),
            "B_bot_m": geom.bottom_width, "t_f_h": geom.formation_time / 3600, "_r": r}


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = []
    for r in rows:
        keys += [k for k in r if not k.startswith("_") and k not in keys]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in keys})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--tier", default="shakedown", help="which 2D outputs to read (shakedown | extended)")
    ap.add_argument("--root", type=Path, default=config.ROOT,
                    help="checkout holding data/raw/osm_domain.gpkg and outputs/<scenario>/*.tif")
    ap.add_argument("--cluster-km", type=float, nargs=2, default=[4.0, 5.5],
                    help="distance band (km from the site) summed as 'the cluster'")
    ap.add_argument("--dt", type=float, default=2.0)
    ap.add_argument("--hours", type=float, default=16.0)
    a = ap.parse_args()

    site, dem_cfg = config.site(), config.site()["dem"]
    sdir = a.root / "outputs" / a.scenario
    depth_tif, speed_tif = sdir / f"max_depth_{a.tier}.tif", sdir / f"max_speed_{a.tier}.tif"
    arr_tif, bed_tif = sdir / f"arrival_h_{a.tier}.tif", sdir / f"dem_burned_{a.tier}.tif"
    out = config.OUTPUTS / "downstream_ponds" / a.scenario
    lidar = config.DATA_RAW / "lidar_ponds"
    out.mkdir(parents=True, exist_ok=True); lidar.mkdir(parents=True, exist_ok=True)

    centre = Point(*site["site"]["centre_nztm"])
    water = gpd.read_file(a.root / "data" / "raw" / "osm_domain.gpkg", layer="water").to_crs(2193)
    water["geometry"] = water.geometry.buffer(0)
    water = water[water.geometry.area > 0].copy()
    # OSM often maps the same pond twice (e.g. natural=water + landuse=reservoir): keep one per outline
    water["key"] = water.geometry.centroid.apply(lambda p: (round(p.x, -1), round(p.y, -1)))
    water = water.sort_values("kind").drop_duplicates("key")

    flood = Surface(bed_tif, depth_tif)
    ponds, knock, hyd, banks, outlines = [], [], {}, [], {}
    for _, w in water.iterrows():
        poly = w.geometry if w.geometry.geom_type == "Polygon" else max(w.geometry.geoms, key=lambda g: g.area)
        near = poly.buffer(60).difference(poly.buffer(15))     # ground just outside the banks
        dep = clip(depth_tif, poly.buffer(60))
        if not dep.size or dep.max() < WET_M:
            continue
        area, dist = poly.area, poly.centroid.distance(centre) / 1000
        wse = flood.within(near)
        arr = clip(arr_tif, poly.buffer(60))
        row = {"osm_id": w.osm_id, "kind": w.kind, "name": w["name"] if isinstance(w["name"], str) else "",
               "area_ha": area / 1e4, "dist_km": dist, "x": poly.centroid.x, "y": poly.centroid.y,
               "max_depth_m": float(dep.max()), "max_speed_ms": float(np.nanmax(clip(speed_tif, poly.buffer(60)))),
               "arrival_h": float(np.nanmin(arr)) if arr.size else np.nan,
               "flood_wse_max_mRL": float(wse.max()) if wse.size else np.nan,
               "flood_wse_med_mRL": float(np.median(wse)) if wse.size else np.nan}
        if area >= MIN_AREA_M2:
            W, S, E, N = poly.buffer(80).bounds
            patch = lidar / f"pond_{w.osm_id}.tif"
            if not patch.exists():
                terrain.fetch_dem((W, S, E, N), 1.0, patch, dem_cfg["bucket"], dem_cfg["collection"], verbose=False)
            inner = poly.buffer(-15) if poly.buffer(-15).area > 0.2 * area else poly
            surface = float(np.median(clip(patch, inner)))
            cpts, crest = bank_crest(patch, poly)
            local = np.array([flood.next_to(pt, poly) for pt in cpts])
            margin = crest - local                      # >0: bank stays above the flood next to it
            wet = np.isfinite(margin)
            banks += [{"osm_id": w.osm_id, "x": pt.x, "y": pt.y, "crest_mRL": float(cr), "flood_mRL": float(fl),
                       "margin_m": float(mg)} for pt, cr, fl, mg in zip(cpts, crest, local, margin)]
            ground = clip(patch, poly.buffer(45).difference(poly.buffer(25)))
            row.update({"surface_mRL": surface, "crest_low_mRL": float(np.percentile(crest, 5)),
                        "crest_med_mRL": float(np.median(crest)), "ground_out_med_mRL": float(np.median(ground)),
                        "ground_out_low_mRL": float(np.percentile(ground, 5))})
            row["overtop_margin_m"] = float(np.nanmin(margin)) if wet.any() else np.nan
            row["bank_overtopped_pct"] = 100.0 * float((margin[wet] < 0).sum()) / len(margin)
            row["max_overtop_depth_m"] = float(max(-np.nanmin(margin), 0)) if wet.any() else 0.0
            row["bank_height_m"] = row["crest_med_mRL"] - row["ground_out_med_mRL"]
            row["perched_now_Mm3"] = area * max(surface - row["ground_out_med_mRL"], 0) / 1e6
            full = row["crest_low_mRL"] - FREEBOARD_M
            row["perched_full_Mm3"] = area * max(full - row["ground_out_med_mRL"], 0) / 1e6
            g, c = row["ground_out_med_mRL"], row["crest_med_mRL"]
            tw = max(g, row["flood_wse_med_mRL"]) if np.isfinite(row["flood_wse_med_mRL"]) else g
            for case, pool, inv in (("surveyed level, dry toe", surface, g),
                                    ("full (0.5 m freeboard), dry toe", max(full, surface), g),
                                    ("surveyed level, flood tailwater", surface, tw)):
                k = knockon(area, surface, g, c, pool, inv, a.dt, a.hours)
                rec = {"osm_id": w.osm_id, "kind": w.kind, "area_ha": area / 1e4, "dist_km": dist, "case": case,
                       "pool_mRL": pool, "breach_invert_mRL": inv, "head_m": pool - inv,
                       "in_cluster": a.cluster_km[0] <= dist <= a.cluster_km[1]}
                if k is None:
                    rec.update({"peak_Q_m3s": 0.0, "released_m3": 0.0})
                else:
                    hyd[(w.osm_id, case)] = k.pop("_r")
                    rec.update(k)
                knock.append(rec)
        ponds.append(row)
        outlines[w.osm_id] = (poly, w.kind)

    ponds.sort(key=lambda r: r["dist_km"])
    write_csv(out / "ponds.csv", ponds)
    write_csv(out / "knockon.csv", knock)

    # cluster sums: each pond fails when the flood first reaches it (arrival time), all three cases
    arrival = {p["osm_id"]: p["arrival_h"] for p in ponds}
    t = np.arange(0, 18 * 3600 + 1, 60.0)
    summary = {"scenario": a.scenario, "tier": a.tier, "cluster_km": a.cluster_km, "note": NOTE, "cases": {}}
    hrows = {"t_h": t / 3600}
    for case in sorted({k["case"] for k in knock}):
        ks = [k for k in knock if k["case"] == case and k["in_cluster"]]
        q = np.zeros_like(t)
        for k in ks:
            r = hyd.get((k["osm_id"], case))
            if r is not None:
                q += np.interp(t - arrival[k["osm_id"]] * 3600, r["t"], r["Q_out"], left=0, right=0)
        hrows[case] = q
        summary["cases"][case] = {"ponds": len(ks), "released_Mm3": sum(k["released_m3"] for k in ks) / 1e6,
                                  "sum_of_peaks_m3s": sum(k["peak_Q_m3s"] for k in ks),
                                  "combined_peak_m3s": float(q.max()), "combined_peak_t_h": float(t[q.argmax()] / 3600)}
    main_hyd = np.genfromtxt(a.root / "outputs" / a.scenario / "hydrograph.csv", delimiter=",", names=True)
    summary["main_breach"] = {"peak_Q_m3s": float(main_hyd["Q_out_m3s"].max()),
                              "released_Mm3": float(np.trapezoid(main_hyd["Q_out_m3s"], main_hyd["t_s"]) / 1e6)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    with open(out / "knockon_hydrographs.csv", "w", newline="") as fh:
        wr = csv.writer(fh); keys = list(hrows)
        wr.writerow(keys)
        for i in range(len(t)):
            wr.writerow([f"{hrows[k][i]:.3f}" for k in keys])
    write_csv(out / "bank_points.csv", banks)
    plot(out, ponds, hrows, summary, depth_tif, centre)
    zoom_map(out, a.root, ponds, outlines, banks, depth_tif, arr_tif, a.cluster_km, centre)
    print(json.dumps(summary, indent=2))


def plot(out, ponds, hrows, summary, depth_tif, centre):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.25, 1]})
    with rasterio.open(depth_tif) as r:
        d = r.read(1).astype(float); d[(d < WET_M) | (d == r.nodata)] = np.nan
        ext = (r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top)
    im = ax.imshow(d, extent=ext, cmap="Blues", vmin=0, vmax=2)
    fig.colorbar(im, ax=ax, shrink=0.7, label="max flood depth (m)")
    for p in ponds:
        m, pct = p.get("overtop_margin_m", np.nan), p.get("bank_overtopped_pct", 0.0)
        col = ("grey" if not np.isfinite(m) else "red" if pct >= OVERTOP_PCT
               else "orange" if m < 0.5 else "green")
        ax.scatter(p["x"], p["y"], s=max(p["area_ha"], 0.3) * 12, facecolor="none", edgecolor=col, lw=1.5)
        if p["area_ha"] >= MIN_AREA_M2 / 1e4:
            ax.annotate(f"{p['area_ha']:.0f} ha", (p["x"], p["y"]), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.plot(centre.x, centre.y, "k*", ms=12)
    xs, ys = [p["x"] for p in ponds], [p["y"] for p in ponds]
    ax.set_xlim(min(xs + [centre.x]) - 1500, max(xs) + 1500); ax.set_ylim(min(ys) - 1500, max(ys + [centre.y]) + 1500)
    ax.set_title(f"Ponds reached by the flood. Red: flood over ≥{OVERTOP_PCT:g} % of the bank; orange: over or\n"
                 "within 0.5 m of the bank at isolated points; green: ≥0.5 m below; grey: <1.5 ha, not measured", fontsize=9)
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.set_xlabel("NZTM E (m)"); ax.set_ylabel("NZTM N (m)")
    for case, q in hrows.items():
        if case != "t_h":
            bx.plot(hrows["t_h"], q, label=case)
    bx.set_xlabel("hours after the main breach opens"); bx.set_ylabel("knock-on outflow, cluster sum (m³/s)")
    mb = summary["main_breach"]
    bx.set_title(f"Knock-on breaches of the {summary['cluster_km'][0]:g}–{summary['cluster_km'][1]:g} km cluster "
                 f"(each fails on flood arrival)\nmain breach for scale: peak {mb['peak_Q_m3s']:,.0f} m³/s, "
                 f"{mb['released_Mm3']:.1f} Mm³", fontsize=9)
    bx.legend(fontsize=8); bx.grid(alpha=0.3)
    fig.text(0.01, 0.01, NOTE, fontsize=7, color="grey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "downstream_ponds.png", dpi=130)


def zoom_map(out, root, ponds, outlines, banks, depth_tif, arr_tif, cluster_km, centre):
    """Close-up of the 4-5.5 km group: flood depth, arrival contours, roads, buildings, pond outlines and the
    bank stretches the peak flood tops."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    group = [p for p in ponds if cluster_km[0] <= p["dist_km"] <= cluster_km[1] and p["area_ha"] * 1e4 >= MIN_AREA_M2]
    if not group:
        return
    W = min(outlines[p["osm_id"]][0].bounds[0] for p in group) - 900
    S = min(outlines[p["osm_id"]][0].bounds[1] for p in group) - 900
    E = max(outlines[p["osm_id"]][0].bounds[2] for p in group) + 900
    N = max(outlines[p["osm_id"]][0].bounds[3] for p in group) + 900
    gpkg = root / "data" / "raw" / "osm_domain.gpkg"
    roads = gpd.read_file(gpkg, layer="roads", bbox=(W, S, E, N))
    bldg = gpd.read_file(gpkg, layer="buildings", bbox=(W, S, E, N))
    fig, ax = plt.subplots(figsize=(11, 10))
    with rasterio.open(depth_tif) as r:
        win = rasterio.windows.from_bounds(W, S, E, N, r.transform)
        d = r.read(1, window=win).astype(float); d[(d < WET_M) | (d == r.nodata)] = np.nan
        ext = rasterio.windows.bounds(win, r.transform)
    with rasterio.open(arr_tif) as r:
        win2 = rasterio.windows.from_bounds(W, S, E, N, r.transform)
        t_arr = r.read(1, window=win2).astype(float); t_arr[(t_arr == r.nodata) | (t_arr < 0)] = np.nan
        ext2 = rasterio.windows.bounds(win2, r.transform)
    im = ax.imshow(d, extent=(ext[0], ext[2], ext[1], ext[3]), cmap="Blues", vmin=0, vmax=2, zorder=1)
    ys = np.linspace(ext2[3], ext2[1], t_arr.shape[0]); xs = np.linspace(ext2[0], ext2[2], t_arr.shape[1])
    cs = ax.contour(xs, ys, t_arr, levels=[1.0, 1.25, 1.5, 1.75, 2.0], colors="0.35", linewidths=0.6,
                    linestyles="dashed", zorder=2)
    ax.clabel(cs, fmt=lambda v: f"{v:g} h", fontsize=7)
    roads.plot(ax=ax, color="0.55", lw=0.8, zorder=3)
    for name, g in roads.dropna(subset=["name"]).groupby("name"):
        seg = max((x.intersection(box(W + 150, S + 150, E - 150, N - 150)) for x in g.geometry), key=lambda x: x.length)
        if seg.length > 400 and seg.geom_type == "LineString":
            p = seg.interpolate(0.5, normalized=True)
            ax.text(p.x, p.y, name, fontsize=7, color="0.25", ha="center", va="center", zorder=6,
                    bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.5))
    bldg.plot(ax=ax, color="0.15", zorder=4)
    colours = {"wastewater": "#b5651d", "reservoir": "#2a9d8f", "pond": "#2a9d8f", "basin": "#7a7a7a"}
    letters = iter("ABCDEFGHIJ")
    legend_rows = []
    for p in sorted(ponds, key=lambda q: q["dist_km"]):
        poly, kind = outlines[p["osm_id"]]
        if not poly.intersects(box(W, S, E, N)):
            continue
        measured = p["area_ha"] * 1e4 >= MIN_AREA_M2
        gpd.GeoSeries([poly]).plot(ax=ax, facecolor="none", edgecolor=colours.get(kind, "k"),
                                   lw=2.2 if measured else 1, hatch="///" if kind == "wastewater" else None, zorder=5)
        if measured:
            L = next(letters)
            c = poly.representative_point()
            ax.text(c.x, c.y, L, fontsize=13, weight="bold", ha="center", va="center", color=colours.get(kind, "k"),
                    zorder=7, bbox=dict(fc="white", ec="none", alpha=0.75, pad=1))
            legend_rows.append(f"{L}: {kind}, {p['area_ha']:.0f} ha, {p['dist_km']:.1f} km, flood arrives "
                               f"{p['arrival_h']:.1f} h, {p.get('bank_overtopped_pct', 0):.0f} % of bank topped")
    b = [q for q in banks if np.isfinite(q["margin_m"])]
    top = [q for q in b if q["margin_m"] < 0]
    near = [q for q in b if 0 <= q["margin_m"] < 0.5]
    ax.scatter([q["x"] for q in near], [q["y"] for q in near], s=9, c="orange", zorder=8)
    ax.scatter([q["x"] for q in top], [q["y"] for q in top], s=12, c="red", zorder=9)
    ax.set_xlim(W, E); ax.set_ylim(S, N); ax.set_aspect("equal")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.set_xlabel("NZTM E (m)"); ax.set_ylabel("NZTM N (m)")
    fig.colorbar(im, ax=ax, shrink=0.6, label="peak flood depth (m), east breach")
    handles = [Patch(fc="none", ec=colours["reservoir"], lw=2, label="reservoir / pond (OSM)"),
               Patch(fc="none", ec=colours["wastewater"], lw=2, hatch="///", label="wastewater pond (OSM / Topo50)"),
               Line2D([], [], marker="o", ls="", color="red", ms=4, label="bank topped by the peak flood"),
               Line2D([], [], marker="o", ls="", color="orange", ms=4, label="bank within 0.5 m of the flood"),
               Line2D([], [], color="0.35", ls="--", lw=0.8, label="flood arrival, h after breach opens"),
               Patch(fc="0.15", label="building (OSM)")]
    ax.legend(handles=handles, loc="lower left", fontsize=8, framealpha=0.95)
    ax.set_title(f"Ponds {cluster_km[0]:g}–{cluster_km[1]:g} km downstream of the Wrights Road ponds, "
                 "with the east-breach flood", fontsize=11)
    fig.text(0.02, 0.015, "\n".join(legend_rows + [NOTE + " Flood: 20 m shakedown run; banks: 1 m LiDAR."]),
             fontsize=7.5, va="bottom", family="monospace")
    fig.tight_layout(rect=(0, 0.02 + 0.016 * len(legend_rows), 1, 1))
    fig.savefig(out / "downstream_ponds_map.png", dpi=140)


if __name__ == "__main__":
    main()
