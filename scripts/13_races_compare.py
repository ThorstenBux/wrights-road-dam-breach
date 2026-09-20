#!/usr/bin/env python
"""EXPLORATORY: post-process the race runs of scripts/12_run_races.py.

  * dewatering only: how far and how fast the races fill, where they spill (the EAP App. F.6 case)
  * breach onto full races vs the same breach onto dry races: difference in arrival time and peak depth

Writes maps / tables to outputs/races/.  Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post  # noqa: E402

NOTE = "exploratory screening – not a certified assessment"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--crossings", choices=("open", "blocked"), default="open")
    ap.add_argument("--res", type=float, default=10.0)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

    rc, site, dam = config.load_yaml("races.yaml"), config.site(), config.dam()
    out = config.OUTPUTS / "races"; bbox = rc["domain"]["bbox_nztm"]; sfx = f"{a.crossings}{a.tag}"
    thr = site["run"]["depth_threshold_m"]
    cond = gpd.read_file(out / "races_conditioning.gpkg")
    lines = cond[cond.kind == "thalweg"].set_index("race").geometry
    crossings = cond[cond.kind == "crossing"]
    roads = gpd.read_file(config.DATA_RAW / "osm_domain.gpkg", layer="roads").cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    ext = [bbox[0], bbox[2], bbox[1], bbox[3]]
    summary = {"note": NOTE}

    def base_map(ax):
        roads.plot(ax=ax, color="0.55", lw=0.4)
        for n, g in lines.items():
            ax.plot(*g.xy, color="k", lw=0.6)
            ax.annotate(n, g.coords[len(g.coords) // 3], fontsize=8, fontweight="bold")
        ax.add_patch(plt.Polygon(site["site"]["footprint_nztm"], fc="0.8", ec="k", lw=0.8))
        ax.set_xlim(ext[:2]); ax.set_ylim(ext[2:]); ax.set_aspect("equal"); ax.tick_params(labelsize=6)

    # ---------------------------------------------------------------- dewatering only
    p = out / f"races_dewater_{sfx}.sww"
    if p.exists():
        s = post.SWW(p); meta = json.loads((out / f"run_meta_races_dewater_{sfx}.json").read_text())
        mx = s.maxima(depth_threshold=thr)
        D, tr = s.grid(mx["max_depth"], bbox, a.res)
        post.write_tif(out / f"dewater_max_depth_{sfx}.tif", D, tr)
        # along-race: peak depth, freeboard to the bank, arrival of the front
        from scipy.spatial import cKDTree
        kd = cKDTree(np.c_[s.x, s.y])
        fig, axs = plt.subplots(len(lines), 1, figsize=(12, 3.2 * len(lines)))
        rows = {}
        for ax, (n, g) in zip(np.atleast_1d(axs), lines.items()):
            xy = np.array(g.coords); ch = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))] / 1000
            # deepest / earliest mesh vertex within 4 m of each station (the bed vertices sit beside the centre line)
            near = kd.query_ball_point(xy, 4.0)
            d = np.array([mx["max_depth"][k].max() if k else np.nan for k in near])
            arr = np.array([np.nanmin(np.r_[mx["arrival_h"][k], 1e9]) if k else 1e9 for k in near])
            wet = d > thr
            reach = float(ch[wet].max()) if wet.any() else 0.0
            rows[n] = {"length_km": float(ch[-1]), "front_reached_km": reach, "reached_end": bool(reach > ch[-1] - 0.05),
                       "median_peak_depth_in_race_m": float(np.nanmedian(d[wet])) if wet.any() else 0.0,
                       "hours_to_end": float(np.min(arr[-6:])) if np.min(arr[-6:]) < 1e5 else None,
                       "dewater_q_m3s": meta["races"][n]["dewater_q_m3s"], "bankfull_est_m3s": meta["races"][n]["bankfull_Q_m3s"]}
            ax.plot(ch, d, "b", lw=0.8, label="peak depth in the race (m)")
            ax2 = ax.twinx(); ax2.plot(ch[arr < 1e5], arr[arr < 1e5], "r", lw=0.8); ax2.set_ylabel("front arrival (h)", color="r")
            for _, c in crossings[crossings.race == n].iterrows():
                ax.axvline(g.project(c.geometry) / 1000, color="k", lw=0.3, alpha=0.4)
            ax.set_title(f"{n}: {rows[n]['dewater_q_m3s']} m3/s for {meta['finaltime_s']/3600:g} h – crossings {a.crossings} (grey lines)", fontsize=9)
            ax.set_xlabel("km along the race"); ax.legend(fontsize=7, loc="upper left")
        fig.suptitle(f"Dewatering only – {NOTE}", fontsize=9); fig.tight_layout()
        fig.savefig(out / f"dewater_long_sections_{sfx}.png", dpi=130); plt.close(fig)
        # spill = water deeper than the threshold more than 15 m from any race centreline
        from shapely import points
        tri_c = np.c_[s.x, s.y]
        deep = np.nonzero(mx["max_depth"] > thr)[0]
        union = lines.unary_union if hasattr(lines, "unary_union") else lines.union_all()
        dist = union.distance(points(tri_c[deep]))
        off = deep[dist > 15.0]
        cell = a.res ** 2
        spill_area = float(np.nansum((D > thr)) * cell)
        buf = gpd.GeoSeries([union.buffer(15.0)], crs=2193)
        from rasterio.features import geometry_mask
        inrace = geometry_mask(buf.geometry, out_shape=D.shape, transform=tr, invert=True)
        summary["dewater"] = {"races": rows, "wet_area_total_km2": spill_area / 1e6,
                              "wet_area_outside_races_km2": float(np.nansum((D > thr) & ~inrace) * cell / 1e6),
                              "max_depth_outside_races_m": float(np.nanmax(np.where(~inrace, D, np.nan))) if (~inrace).any() else 0.0}
        fig, ax = plt.subplots(figsize=(14, 9.5)); base_map(ax)
        im = ax.imshow(np.where(D > thr, D, np.nan), extent=ext, cmap="Blues", vmin=0, vmax=1.5, zorder=3)
        ax.scatter(s.x[off], s.y[off], s=1, color="red", zorder=4, label="water outside the races (> %.1f m)" % thr)
        plt.colorbar(im, ax=ax, shrink=0.6, label="peak depth (m)"); ax.legend(fontsize=8)
        ax.set_title(f"Dewatering only: {sum(r['dewater_q_m3s'] for r in rows.values()):g} m3/s for {meta['finaltime_s']/3600:g} h, crossings {a.crossings} – {NOTE}", fontsize=9)
        fig.tight_layout(); fig.savefig(out / f"dewater_max_depth_{sfx}.png", dpi=130); plt.close(fig)

    # ---------------------------------------------------------------- breach runs: A minus B on the same mesh
    def compare(key, run_a, run_b, lab_a, lab_b, title):
        pa, pb = out / f"races_{run_a}.sww", out / f"races_{run_b}.sww"
        if not (pa.exists() and pb.exists()):
            return
        tb = float(json.loads((out / f"run_meta_races_{run_a}.json").read_text())["t_breach_s"])
        res = {}
        for k, path in ((lab_a, pa), (lab_b, pb)):
            sw = post.SWW(path); mx = sw.maxima(depth_threshold=thr, t_breach=tb)
            res[k] = {q: sw.grid(mx[q], bbox, a.res)[0] for q in ("max_depth", "arrival_h")}
            _, tr = sw.grid(mx["max_depth"], bbox, a.res)
            for q in ("max_depth", "arrival_h"):
                post.write_tif(out / f"{key}_{k}_{q}_{sfx}.tif", res[k][q], tr)
        A, B = res[lab_a], res[lab_b]
        both = np.isfinite(A["arrival_h"]) & np.isfinite(B["arrival_h"])
        dA = np.where(both, A["arrival_h"] - B["arrival_h"], np.nan)            # h; negative = earlier in A
        flooded = (np.nan_to_num(A["max_depth"]) > thr) | (np.nan_to_num(B["max_depth"]) > thr)
        dD = np.where(flooded, np.nan_to_num(A["max_depth"]) - np.nan_to_num(B["max_depth"]), np.nan)
        post.write_tif(out / f"{key}_diff_arrival_h_{sfx}.tif", dA, tr); post.write_tif(out / f"{key}_diff_max_depth_{sfx}.tif", dD, tr)
        cell = a.res ** 2
        summary[key] = {
            "a": lab_a, "b": lab_b,
            "flooded_area_km2": {k: float(np.isfinite(res[k]["arrival_h"]).sum() * cell / 1e6) for k in res},
            "arrival_a_minus_b_min_percentiles_5_50_95": [float(v * 60) for v in np.nanpercentile(dA, [5, 50, 95])],
            "share_of_flooded_cells_arriving_5min_earlier_in_a": float(np.mean(dA[both] < -5 / 60)),
            "share_arriving_5min_later_in_a": float(np.mean(dA[both] > 5 / 60)),
            "share_arriving_30min_later_in_a": float(np.mean(dA[both] > 0.5)),
            "depth_a_minus_b_m_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dD, [5, 50, 95])],
            "flooded_only_in_a_km2": float((np.isfinite(A["arrival_h"]) & ~np.isfinite(B["arrival_h"])).sum() * cell / 1e6),
            "flooded_only_in_b_km2": float((np.isfinite(B["arrival_h"]) & ~np.isfinite(A["arrival_h"])).sum() * cell / 1e6)}
        names = [n for n in dam["consequence"]["roads_of_interest"] if n in set(roads["name"].dropna())]
        tabs = []
        for k in res:
            rasters = {"arrival_h": out / f"{key}_{k}_arrival_h_{sfx}.tif", "max_depth": out / f"{key}_{k}_max_depth_{sfx}.tif"}
            try:
                t = post.road_table(roads, rasters, names); t.insert(0, "run", k); tabs.append(t)
            except Exception as exc:   # road_table expects the pipeline's raster set; keep the maps if it differs
                print(f"[races] road table skipped: {exc}")
        if tabs:
            pd.concat(tabs).to_csv(out / f"{key}_roads_{sfx}.csv", index=False)
        fig, axs = plt.subplots(1, 2, figsize=(20, 7.5))
        lim_t = max(10.0, float(np.nanpercentile(np.abs(dA * 60), 98))) if both.any() else 10.0
        for ax, arr, lab, lim in ((axs[0], dA * 60, f"arrival: {lab_a} minus {lab_b} (min; blue = earlier, red = later)", lim_t),
                                  (axs[1], dD, f"peak depth: {lab_a} minus {lab_b} (m)", 0.3)):
            base_map(ax); im = ax.imshow(arr, extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim, zorder=3)
            plt.colorbar(im, ax=ax, shrink=0.6); ax.set_title(lab, fontsize=9)
        fig.suptitle(f"{title}, crossings {a.crossings} – {NOTE}", fontsize=9)
        fig.tight_layout(); fig.savefig(out / f"{key}_{sfx}.png", dpi=130); plt.close(fig)

    c = a.crossings
    compare("full_vs_dry_races", f"dewater_breach_{c}", f"breach_dry_{c}", "full", "dry",
            "East breach after dewatering: races running full vs dry races (same mesh, same hydrograph)")
    compare("trees_vs_none", f"breach_dry_{c}_trees", f"breach_dry_{c}", "trees", "none",
            "East breach: with tree shelterbelts vs without (dry races)")
    compare("full_vs_dry_races_trees", f"dewater_breach_{c}_trees", f"breach_dry_{c}_trees", "full", "dry",
            "East breach after dewatering, with shelterbelts: races running full vs dry races")

    (out / f"races_summary_{sfx}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
