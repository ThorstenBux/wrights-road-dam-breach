#!/usr/bin/env python
"""EXPLORATORY: breach onto running races with every culvert open vs every culvert blocked, on a dry and on a wet plain.

Runs of scripts/12_run_races.py --case dewater_breach --crossings open|blocked [--rain-mm-h 10] --tag _cmp, plus for the
wet pair the same without the breach (--case dewater --rain-mm-h 10 --finaltime-s <same>) as the baseline, so that
arrival and depth are the water ADDED by the breach. Same mesh in all of them (the culvert state only changes bed levels).
Writes outputs/races/culverts_<dry|wet>{.png,_roads.csv} and culverts_summary.json.
Screening model, not a certified assessment.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tag", default="_cmp"); ap.add_argument("--res", type=float, default=10.0)
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    rc, site, dam = config.load_yaml("races.yaml"), config.site(), config.dam()
    out = config.OUTPUTS / "races"; bbox = rc["domain"]["bbox_nztm"]; thr = site["run"]["depth_threshold_m"]
    ext = [bbox[0], bbox[2], bbox[1], bbox[3]]
    cond = gpd.read_file(out / "races_conditioning.gpkg"); crossings = cond[cond.kind == "crossing"]; lines = cond[cond.kind == "thalweg"]
    roads = gpd.read_file(config.DATA_RAW / "osm_domain.gpkg", layer="roads").cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    summary = {"note": "exploratory screening – not a certified assessment"}
    for wetness in ("dry", "wet"):
        sfx = a.tag + ("_wet" if wetness == "wet" else ""); grids = {}
        for cr in ("open", "blocked"):
            p = out / f"races_dewater_breach_{cr}{sfx}.sww"
            if not p.exists():
                print(f"[culverts] {p.name} missing"); break
            meta = json.loads((out / f"run_meta_races_dewater_breach_{cr}{sfx}.json").read_text())
            bp = out / f"races_dewater_{cr}{sfx}.sww"
            base = post.SWW(bp) if (wetness == "wet" and bp.exists()) else None
            s = post.SWW(p); mx = s.maxima(depth_threshold=thr, t_breach=meta["t_breach_s"], baseline=base)
            D, tr = s.grid(np.where(mx["max_excess"] > thr, mx["max_excess"], 0.0), bbox, a.res)
            A, _ = s.grid(np.where(mx["max_excess"] > thr, mx["arrival_h"], np.nan), bbox, a.res)
            D = np.where(np.isfinite(D) & (D > thr), D, np.nan)
            grids[cr] = (D, A); rasters = {}
            for key, arr in (("max_depth", D), ("arrival_h", A)):
                rasters[key] = post.write_tif(out / f"culverts_{key}_{cr}{sfx}.tif", arr, tr)
            rt = post.road_table(roads, rasters, dam["consequence"]["roads_of_interest"])
            grids[cr + "_roads"] = rt.set_index("road")[["first_arrival_h", "max_depth_m"]]
        else:
            (Do, Ao), (Db, Ab) = grids["open"], grids["blocked"]; cell = a.res ** 2
            both = np.isfinite(Ao) & np.isfinite(Ab); dA = np.where(both, Ab - Ao, np.nan) * 60
            wetc = np.isfinite(Do) | np.isfinite(Db); dD = np.where(wetc, np.nan_to_num(Db) - np.nan_to_num(Do), np.nan)
            near = []
            for _, c in crossings.iterrows():
                j, i = int((c.geometry.x - bbox[0]) / a.res), int((bbox[3] - c.geometry.y) / a.res); w = int(80 / a.res)
                near.append({"race": c.race, "E": round(c.geometry.x), "N": round(c.geometry.y), "fill_height_m": round(float(c.hump_m), 2),
                             "max_depth_change_within_80m_m": round(float(np.nanmax(np.nan_to_num(dD[max(i - w, 0):i + w + 1, max(j - w, 0):j + w + 1]))), 2)})
            summary[wetness] = {
                "breach_flood_area_km2_open": float(np.isfinite(Do).sum() * cell / 1e6), "breach_flood_area_km2_blocked": float(np.isfinite(Db).sum() * cell / 1e6),
                "only_flooded_with_blocked_culverts_km2": float((np.isfinite(Db) & ~np.isfinite(Do)).sum() * cell / 1e6),
                "only_flooded_with_open_culverts_km2": float((np.isfinite(Do) & ~np.isfinite(Db)).sum() * cell / 1e6),
                "arrival_change_min_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dA, [5, 50, 95])],
                "depth_change_m_percentiles_1_5_50_95_99": [float(v) for v in np.nanpercentile(dD, [1, 5, 50, 95, 99])],
                "area_deeper_by_0.1m_km2": float((dD > 0.1).sum() * cell / 1e6), "area_shallower_by_0.1m_km2": float((dD < -0.1).sum() * cell / 1e6),
                "crossings": sorted(near, key=lambda r: -r["max_depth_change_within_80m_m"])[:10]}
            tab = grids["open_roads"].join(grids["blocked_roads"], lsuffix=" open", rsuffix=" blocked"); tab.round(2).to_csv(out / f"culverts_{wetness}_roads.csv")
            fig, axs = plt.subplots(1, 2, figsize=(20, 7))
            for ax, arr, lab, l in ((axs[0], dA, "arrival, culverts blocked minus open (min)", 30), (axs[1], dD, "breach-added peak depth, blocked minus open (m)", 0.3)):
                roads.plot(ax=ax, color="0.6", lw=0.3); im = ax.imshow(arr, extent=ext, cmap="RdBu_r", vmin=-l, vmax=l, zorder=2); plt.colorbar(im, ax=ax, shrink=0.7)
                lines.plot(ax=ax, color="k", lw=0.6, zorder=3); crossings.plot(ax=ax, color="k", markersize=6, zorder=4)
                ax.add_patch(plt.Polygon(site["site"]["footprint_nztm"], fc="0.8", ec="k")); ax.set_xlim(ext[:2]); ax.set_ylim(ext[2:]); ax.set_title(lab, fontsize=9); ax.tick_params(labelsize=6)
            fig.suptitle(f"East breach onto running races, {wetness} plain: every culvert blocked vs open (dots = crossings) – exploratory screening, not a certified assessment", fontsize=10)
            fig.tight_layout(); fig.savefig(out / f"culverts_{wetness}.png", dpi=110); plt.close(fig)
            print(wetness, json.dumps({k: v for k, v in summary[wetness].items() if k != "crossings"}, indent=1)); print(tab.round(2).to_string())
    (out / "culverts_summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
