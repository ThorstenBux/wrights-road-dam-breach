#!/usr/bin/env python
"""EXPLORATORY: what do the scripts/24 runs say – Eyre flood at the north embankment, and what a breach adds to the river flood.

For every run found (outputs/<scenario>/<scenario>_north_q<peak>...sww) and its no-breach baseline on the same mesh:
  embankment   depth and duration of water against the north embankment (two rows of gauges outside it)
  river        discharge through cross-sections of the Eyre every 2 km, water leaving over the left (north) and right
               (south) bank lines per km, rise of the peak flood level in the river – with minus without the breach
  consequence  breach-added flooded area, buildings, and arrival of the breach water at the roads of interest
               (+ North Eyre Road, Dixons Road, South Eyre Road)
Writes outputs/north_eyre/north_report.{json,md}, roads / buildings CSV per run and figures. The rasters are 20 m.
Embankment stability under external flooding, seepage and stopbank erosion / failure are NOT modelled – only where and how
much water goes. Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, north, post, vectors, wet  # noqa: E402

EXTRA_ROADS = ["North Eyre Road", "Dixons Road", "Harmans Gorge Road", "Depot Road", "Warren Road", "Steffens Road", "Tram Road"]
RES = 20.0


class Run:
    def __init__(self, scenario, tag):
        self.scenario, self.tag = scenario, tag; d = config.OUTPUTS / scenario
        self.sww_path = d / f"{scenario}{tag}.sww"; self.meta = json.loads((d / f"run_meta{tag}.json").read_text())
        self.pre = float(self.meta["pre_breach_s"]); self.key = f"{scenario}{tag}"

    def baseline_tag(self):
        return north.run_tag(self.meta["mode"], self.meta["inflows"][0]["peak_m3s"] if self.meta["inflows"] else 0.0,
                             self.meta["rain_mm_h"], no_breach=True)


def find_runs(domain_tag):
    runs = []
    for p in sorted(config.OUTPUTS.glob(f"*/*_{domain_tag}_q*.sww")):
        sc = p.parent.name; tag = p.stem[len(sc):]
        if (p.parent / f"run_meta{tag}.json").exists() and (p.parent / f"run_log{tag}.json").exists():    # run_log = finished
            runs.append(Run(sc, tag))
    return runs


def gauge_stats(sww: post.SWW, pts, pre, thr=(0.05, 0.10, 0.30)):
    ts = sww.timeseries([tuple(p) for p in pts]); t = ts["t_s"].to_numpy(); d = ts.drop(columns="t_s").to_numpy()
    dt = np.gradient(t); mx = np.nanmax(d, axis=0); worst = int(np.nanargmax(mx))
    out = {"max_depth_m": float(np.nanmax(mx)), "median_of_gauge_maxima_m": float(np.nanmedian(mx)),
           "share_of_gauges_ever_gt_0p05m": float((mx > 0.05).mean()),
           "first_time_gt_0p05m_h_after_run_start": (float(t[(d > 0.05).any(axis=1)][0] / 3600) if (d > 0.05).any() else None),
           "depth_at_breach_time_max_m": float(np.nanmax(d[int(np.searchsorted(t, pre - 1e-6))]))}
    for h in thr:
        out[f"longest_duration_gt_{h:g}m_h"] = float(((d > h) * dt[:, None]).sum(axis=0).max() / 3600)
    return out, t, d[:, worst]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skip-rasters", action="store_true", help="reuse the rasters of an earlier call")
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    import rasterio
    site, dam, ncfg, wcfg = config.site(), config.dam(), config.load_yaml("north.yaml"), config.load_yaml("wet.yaml")["eyre"]
    dom = ncfg["domain"]; bbox = dom["bbox_nztm"]; thr = site["run"]["depth_threshold_m"]
    out = config.OUTPUTS / "north_eyre"; ras = out / "rasters"; ras.mkdir(parents=True, exist_ok=True)
    gpkg = config.DATA_RAW / dom["osm_name"]; roads, bld = vectors.load(gpkg, "roads"), vectors.load(gpkg, "buildings")
    road_names = dam["consequence"]["roads_of_interest"] + EXTRA_ROADS
    runs = sorted(find_runs(dom["tag"]), key=lambda r: (r.meta["breach"], r.key))      # baselines first: the breach runs read their rasters
    by_key = {r.key: r for r in runs}
    print("[report] runs:", [r.key for r in runs])
    res = {"note": "exploratory screening – not a certified assessment. River peaks are sensitivity values; embankment stability, seepage and "
                   "stopbank erosion / failure are not modelled.", "runs": {}}

    fp = np.array(site["site"]["footprint_nztm"], float); ecfg = ncfg["embankment"]
    gauges = {f"{off:g}m": north.embankment_samples(fp[0], fp[1], ecfg["sample_spacing_m"], off) for off in ecfg["gauge_offsets_m"]}
    eyre = wet.river_line(vectors.load(gpkg, "waterways"), wcfg["name"], bbox, margin=wcfg["refine_half_width_m"] + 100)
    sm = eyre.simplify(60.0); hw = wcfg["refine_half_width_m"]; sections = {}
    for d in np.arange(1000, eyre.length, 2000):
        q = sm.project(eyre.interpolate(d)); p0, p1 = sm.interpolate(max(q - 60, 0)), sm.interpolate(min(q + 60, sm.length))
        tx, ty = p1.x - p0.x, p1.y - p0.y; L = np.hypot(tx, ty); lx, ly = -ty / L, tx / L; c = eyre.interpolate(d)
        sections[f"x{d / 1000:04.1f}"] = [(c.x + hw * lx, c.y + hw * ly), (c.x - hw * lx, c.y - hw * ly)]          # left bank -> right bank
    left = wet.offset_line(eyre, wcfg["bank_offset_m"]); right = wet.offset_line(eyre, -wcfg["bank_offset_m"])
    lines = {**sections, "bank_left": left, "bank_right": list(right.coords)[::-1]}                                # right bank drawn upstream: leaving = positive
    bank_km = lambda name, s: (np.asarray(s) if name == "bank_left" else right.length - np.asarray(s)) / 1000
    from shapely.geometry import Point
    km_site = eyre.project(Point(*fp[:2].mean(axis=0))) / 1000
    res["eyre"] = {"length_in_domain_km": eyre.length / 1000, "km_nearest_the_ponds": km_site,
                   "km_of_roads": {nm: eyre.project(roads[roads["name"].fillna("") == nm].geometry.union_all().intersection(eyre.buffer(30)).centroid) / 1000
                                   for nm in ("Depot Road", "Warren Road", "Poyntzs Road", "Downs Road", "Two Chain Road", "South Eyre Road")
                                   if (roads["name"].fillna("") == nm).any() and not roads[roads["name"].fillna("") == nm].geometry.union_all().intersection(eyre.buffer(30)).is_empty}}

    flux = {}
    def fluxes(r: Run):
        if r.key not in flux:
            print(f"[report] transects {r.key}", flush=True)
            flux[r.key] = wet.Transects(post.SWW(r.sww_path), lines, spacing=20.0).integrate(t_from=0.0)
        return flux[r.key]

    def per_km(f, nm):
        k_ = np.floor(bank_km(nm, f["s"][nm])).astype(int); nb = int(np.ceil(eyre.length / 1000)) + 1
        return np.bincount(k_, weights=f["out"][nm], minlength=nb)[:nb] / 1e6

    fig_g, ax_g = plt.subplots(figsize=(10, 4.5))
    for r in runs:
        sww = post.SWW(r.sww_path); is_base = not r.meta["breach"]; rr = {"meta": {k: r.meta[k] for k in ("scenario", "rain_mm_h", "hydrograph_tag", "breach", "triangles", "pre_breach_s")},
                                                                         "river_peak_m3s": r.meta["inflows"][0]["peak_m3s"] if r.meta["inflows"] else 0.0,
                                                                         "river_volume_Mm3": r.meta["inflows"][0]["volume_Mm3"] if r.meta["inflows"] else 0.0}
        base = None
        if not is_base:
            bk = f"north{r.baseline_tag()}"
            if bk not in by_key:
                print(f"[report] {r.key}: baseline {bk} missing – skipped"); continue
            base = by_key[bk]; rr["baseline"] = bk
        # embankment gauges (river / rain water only matters in the baselines; with a north breach the gauges sit in the breach jet)
        rr["north_embankment"] = {}
        for gname, pts in gauges.items():
            st, t, dworst = gauge_stats(sww, pts, r.pre); rr["north_embankment"][gname] = st
            if is_base and gname == f"{ecfg['gauge_offsets_m'][0]:g}m":
                ax_g.plot(t / 3600, dworst, label=r.key.replace("north_north_", "").replace("_nobreach", ""))
        # maxima and rasters
        keys = ("max_depth", "max_speed", "max_dv", "arrival_h", "max_excess")
        paths = {k: ras / f"{k}_{r.key}.tif" for k in keys}
        if not (a.skip_rasters and all(p.exists() for p in paths.values())):
            print(f"[report] maxima {r.key}", flush=True)
            mx = sww.maxima(depth_threshold=thr, t_breach=r.pre, baseline=post.SWW(base.sww_path) if base else None)
            for k in keys:
                v = mx[k] if k != "arrival_h" else np.where(mx["max_excess"] > thr, mx[k], np.nan)
                arr, tr = sww.grid(v, bbox, RES); post.write_tif(paths[k], arr, tr)
        with rasterio.open(paths["max_depth"]) as ds:
            dmax = ds.read(1); dmax = np.where(dmax == ds.nodata, np.nan, dmax)
        with rasterio.open(paths["max_excess"]) as ds:
            ex = ds.read(1); ex = np.where(ex == ds.nodata, np.nan, ex)
        rr["wet_area_km2_gt_0p1m"] = float((dmax > thr).sum() * RES ** 2 / 1e6)
        if is_base:
            rr["buildings"] = {k: v for k, v in post.building_table(bld, paths, dam["consequence"]["persons_per_dwelling"], dam["consequence"]["at_risk_depth_m"])[1].items() if k.startswith("buildings")}
            rt = post.road_table(roads, paths | {"arrival_h": paths["max_depth"]}, road_names)[["road", "points_inundated_gt_0.1m", "max_depth_m"]]
        else:
            rr["breach_added_area_km2_gt_0p1m"] = float((ex > thr).sum() * RES ** 2 / 1e6)
            bt, bs = post.building_table(bld, paths | {"max_depth": paths["max_excess"]}, dam["consequence"]["persons_per_dwelling"], dam["consequence"]["at_risk_depth_m"])
            rr["buildings_breach_added"] = {k: v for k, v in bs.items() if k.startswith("buildings")}
            bt[bt["max_depth_m"] > thr].to_csv(out / f"buildings_{r.key}.csv", index=False)
            rt = post.road_table(roads, paths | {"max_depth": paths["max_excess"]}, road_names)
        rt.round(2).to_csv(out / f"roads_{r.key}.csv", index=False)
        rr["roads"] = {row["road"]: {k: (None if pd.isna(v) else round(float(v), 2)) for k, v in row.items() if k in ("first_arrival_h", "max_depth_m", "points_inundated_gt_0.1m")}
                       for _, row in rt.iterrows() if "max_depth_m" in row and not pd.isna(row.get("max_depth_m"))}
        # the river
        f = fluxes(r); t = np.asarray(sww.time, float); xs = sorted(sections)
        rr["eyre"] = {"section_km": [float(n[1:]) for n in xs], "peak_Q_m3s": [round(float(f["Q"][n].max()), 1) for n in xs],
                      "left_bank_leaving_Mm3_per_km": [round(float(v), 3) for v in per_km(f, "bank_left")],
                      "right_bank_leaving_Mm3_per_km": [round(float(v), 3) for v in per_km(f, "bank_right")]}
        if base is not None:
            b = fluxes(base); after = t >= r.pre
            dQ = {n: f["Q"][n] - b["Q"][n] for n in xs}
            rr["eyre"]["added_peak_Q_m3s"] = [round(float(dQ[n][after].max()), 1) for n in xs]
            rr["eyre"]["added_volume_Mm3"] = [round(float(np.trapezoid(dQ[n][after], t[after]) / 1e6), 3) for n in xs]
            reached = [float(n[1:]) for n in xs if dQ[n][after].max() > 1.0]
            rr["eyre"]["first_river_km_with_added_flow_gt_1m3s"] = min(reached) if reached else None
            for nm in ("bank_left", "bank_right"):
                dl = per_km(f, nm) - per_km(b, nm)
                rr["eyre"][f"{nm}_added_leaving_Mm3_total"] = round(float(dl.sum()), 3)
                rr["eyre"][f"{nm}_added_leaving_Mm3_per_km"] = [round(float(v), 3) for v in dl]
                newly = [int(k) for k in np.nonzero((per_km(b, nm) < 0.01) & (per_km(f, nm) > 0.05))[0]]
                rr["eyre"][f"{nm}_km_spilling_only_with_breach"] = newly
            # rise of the peak flood level in the river corridor (max depth with minus without, within 150 m of the centreline)
            with rasterio.open(ras / f"max_depth_{base.key}.tif") as ds:
                d0 = ds.read(1); d0 = np.where(d0 == ds.nodata, np.nan, d0); T = ds.transform
            ch = np.arange(0, eyre.length, 100.0); rise = []
            for d_ in ch:
                p = eyre.interpolate(d_); i, j = int((T.f - p.y) / RES), int((p.x - T.c) / RES); w = int(150 / RES)
                win = (np.nan_to_num(dmax[i - w:i + w + 1, j - w:j + w + 1]) - np.nan_to_num(d0[i - w:i + w + 1, j - w:j + w + 1]))
                rise.append(float(win.max()) if win.size else 0.0)
            rise = np.array(rise)
            rr["eyre"]["max_rise_of_peak_level_m"] = float(rise.max()); rr["eyre"]["km_of_max_rise"] = float(ch[rise.argmax()] / 1000)
            rr["eyre"]["river_km_with_rise_gt_0p1m"] = float((rise > 0.1).sum() * 0.1)
        res["runs"][r.key] = rr
        (out / "north_report.json").write_text(json.dumps(res, indent=1))

    ax_g.axvline(ncfg["hydrograph"]["pre_breach_h"], color="k", ls=":", lw=0.8); ax_g.set_xlabel("hours after the start of the river flood (dotted: breach time in the paired runs)")
    ax_g.set_ylabel(f"depth {ecfg['gauge_offsets_m'][0]} m outside the north embankment (m)\nworst gauge"); ax_g.legend(fontsize=7); ax_g.grid(alpha=0.3)
    ax_g.set_title("River / rain water against the north embankment, no breach – exploratory screening, not a certified assessment", fontsize=9)
    fig_g.tight_layout(); fig_g.savefig(out / "north_embankment_gauges.png", dpi=130)

    # maps: river-only maximum depth (top) and what each breach adds (bottom)
    def show(ax, path, title, vmax, cmap):
        with rasterio.open(path) as ds:
            z = ds.read(1); z = np.where((z == ds.nodata) | (z <= thr), np.nan, z); b = ds.bounds
        ax.imshow(z, extent=[b.left, b.right, b.bottom, b.top], cmap=cmap, vmin=0, vmax=vmax); ax.plot(*eyre.xy, color="navy", lw=0.4)
        ax.add_patch(plt.Polygon(fp, fc="0.6", ec="k", lw=0.5)); ax.set_title(title, fontsize=8); ax.set_xticks([]); ax.set_yticks([])
        for nm, c in (("North Eyre Road", "m"), ("South Eyre Road", "0.4")):
            roads[roads["name"].fillna("") == nm].plot(ax=ax, color=c, lw=0.6)
        ax.set_xlim(bbox[0], bbox[2]); ax.set_ylim(bbox[1] + 3000, bbox[3])
    bases = [r for r in runs if not r.meta["breach"]]; brs = [r for r in runs if r.meta["breach"] and r.key in res["runs"]]
    if bases:
        fig, axs = plt.subplots(len(bases), 1, figsize=(11, 4.6 * len(bases)), squeeze=False)
        for ax, r in zip(axs[:, 0], bases):
            show(ax, ras / f"max_depth_{r.key}.tif", f"{r.key}: maximum depth, no breach (m, > 0.1 m; magenta = North Eyre Road)", 1.5, "Blues")
        fig.suptitle("Eyre flood alone – exploratory screening, not a certified assessment", fontsize=9); fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(out / "north_river_only_depth.png", dpi=120)
    if brs:
        fig, axs = plt.subplots(len(brs), 1, figsize=(11, 4.6 * len(brs)), squeeze=False)
        for ax, r in zip(axs[:, 0], brs):
            show(ax, ras / f"max_excess_{r.key}.tif", f"{r.key}: depth ADDED by the breach to the same flood without it (m, > 0.1 m)", 1.5, "OrRd")
        fig.suptitle("What the breach adds – exploratory screening, not a certified assessment", fontsize=9); fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(out / "north_breach_added_depth.png", dpi=120)
        fig, axs = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        for r in brs:
            e = res["runs"][r.key]["eyre"]; lab = r.key.replace("_north_", " ")
            axs[0].plot(e["section_km"], e["added_peak_Q_m3s"], marker="o", ms=3, label=lab)
            x = np.arange(len(e["bank_left_added_leaving_Mm3_per_km"])) + 0.5
            axs[1].step(x, e["bank_left_added_leaving_Mm3_per_km"], where="mid", label=f"{lab}: left (north) bank")
        for r in bases:
            e = res["runs"][r.key]["eyre"]; axs[0].plot(e["section_km"], e["peak_Q_m3s"], color="0.6", lw=0.8, ls="--")
        axs[0].set_ylabel("m³/s (grey dashed: peak river flow, no breach)"); axs[0].set_yscale("symlog", linthresh=10); axs[0].legend(fontsize=7); axs[0].grid(alpha=0.3)
        axs[0].axvline(km_site, color="m", lw=0.8); axs[1].axvline(km_site, color="m", lw=0.8)
        axs[1].set_ylabel("breach-added water leaving over\nthe LEFT (north) bank line (Mm³ per km)"); axs[1].set_xlabel("distance along the Eyre from where it enters the domain (km; magenta = nearest the ponds)")
        axs[1].legend(fontsize=7); axs[1].grid(alpha=0.3)
        axs[0].set_title("What the breach adds to the Eyre in flood – exploratory screening, not a certified assessment", fontsize=9)
        fig.tight_layout(); fig.savefig(out / "north_eyre_added.png", dpi=130)
    print(f"[report] wrote {out / 'north_report.json'}")


if __name__ == "__main__":
    main()
