#!/usr/bin/env python
"""SWW -> hazard rasters, road arrival table, building/PAR table, quick map."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, vectors  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="east")
    config.add_mode_arg(ap)
    ap.add_argument("--sww", type=Path)
    ap.add_argument("--res", type=float)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    site, dam = config.site(), config.dam()
    mode = config.mode_from_args(a); ms = config.mode_settings(mode)
    out_dir = config.scenario_dir(a.scenario)
    sww_path = a.sww or (out_dir / f"{a.scenario}_{mode}{a.tag}.sww")
    if not sww_path.exists():
        raise SystemExit(f"SWW not found: {sww_path}")
    bbox = ms["bbox"]
    res = a.res or site["run"]["output_res_m"]
    thr = site["run"]["depth_threshold_m"]

    print(f"[post] reading {sww_path}")
    sww = post.SWW(sww_path)
    print(f"[post] {len(sww.time)} timesteps, {len(sww.x)} points, {len(sww.volumes)} triangles")
    meta_path0 = out_dir / f"run_meta_{mode}{a.tag}.json"
    if not meta_path0.exists():
        meta_path0 = out_dir / f"run_meta_{mode}.json"
    pre = float(json.loads(meta_path0.read_text()).get("pre_breach_s", 0.0)) if meta_path0.exists() else 0.0
    mx = sww.maxima(depth_threshold=thr, t_breach=pre)
    rasters = {}
    for key in ("max_depth", "max_speed", "max_dv", "arrival_h", "t_peak_h", "hazard"):
        vals = mx[key]
        if key in ("arrival_h", "t_peak_h", "hazard"):
            vals = np.where(mx["max_depth"] > thr, vals, np.nan)
        else:
            vals = np.where(mx["max_depth"] > thr, vals, 0.0)
        arr, tr = sww.grid(vals, bbox, res)
        if key not in ("arrival_h", "t_peak_h", "hazard"):
            arr = np.where(np.isfinite(arr) & (arr > (thr if key == "max_depth" else 0)), arr, np.nan)
        p = out_dir / f"{key}_{mode}{a.tag}.tif"
        post.write_tif(p, arr, tr); rasters[key] = p
        print(f"[post] wrote {p.name}")

    # extent summary
    with __import__("rasterio").open(rasters["max_depth"]) as ds:
        d = ds.read(1); wet = (d != ds.nodata) & (d > thr)
        extent_km2 = float(wet.sum() * res * res / 1e6)
    meta_path = out_dir / f"run_meta_{mode}{a.tag}.json"
    if not meta_path.exists():
        meta_path = out_dir / f"run_meta_{mode}.json"  # tagged post-processing of an untagged run
    t_off = float(json.loads(meta_path.read_text()).get("time_offset_s", 0.0)) if meta_path.exists() else 0.0
    summary = {"scenario": a.scenario, "mode": mode, "time_zero": "external breach initiation",
               "offset_from_pond1_failure_h": round(t_off / 3600, 2), "inundated_area_km2_gt_%.2fm" % thr: round(extent_km2, 2),
               "max_depth_m": float(np.nanmax(mx["max_depth"])), "max_speed_ms": float(np.nanmax(mx["max_speed"])),
               "sim_hours": float((sww.time[-1] - pre) / 3600), "pre_breach_h": pre / 3600}

    gpkg = config.DATA_RAW / "osm_domain.gpkg"
    if not gpkg.exists():
        gpkg = config.DATA_RAW / "osm_shakedown.gpkg"
    roads = bld = None
    if gpkg.exists():
        roads = vectors.load(gpkg, "roads"); bld = vectors.load(gpkg, "buildings")
        rt = post.road_table(roads, rasters, dam["consequence"]["roads_of_interest"])
        if "first_arrival_h" in rt:
            rt["first_arrival_after_pond1_failure_h"] = (rt["first_arrival_h"] + t_off / 3600).round(2)
            rt["first_arrival_h"] = rt["first_arrival_h"].round(2)
        rt.to_csv(out_dir / f"roads_{mode}{a.tag}.csv", index=False)
        print(rt.to_string(index=False))
        bt, bsum = post.building_table(bld, rasters, dam["consequence"]["persons_per_dwelling"], dam["consequence"]["at_risk_depth_m"])
        bt.to_csv(out_dir / f"buildings_{mode}{a.tag}.csv", index=False)
        summary["buildings"] = bsum
        print(json.dumps(bsum, indent=2))
    else:
        print("[post] no OSM gpkg – skipping road/building tables (run scripts/02_fetch_vectors.py)")
    (out_dir / f"post_summary_{mode}{a.tag}.json").write_text(json.dumps(summary, indent=2))
    fp = [list(map(float, p)) for p in site["site"]["footprint_nztm"]]
    post.quick_map(out_dir / f"max_depth_{mode}{a.tag}.png", rasters["max_depth"], footprint=fp, roads=roads,
                   title=f"Wrights Road ponds – {a.scenario} breach ({mode}): max depth, {summary['sim_hours']:.1f} h",
                   priority_roads=dam["consequence"]["roads_of_interest"], breach_xy=config.breach_points(a.scenario))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
