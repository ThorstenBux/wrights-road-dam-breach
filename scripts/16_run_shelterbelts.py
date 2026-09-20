#!/usr/bin/env python
"""EXPLORATORY: a standard scenario run (as scripts/04_run_model.py) with tree shelterbelts as extra roughness.

Same DEM, mesh, inlet and hydrograph as script 04, so the result can be differenced against the existing run of
the same tier; only the friction differs (equivalent n per triangle from the canopy-fraction raster of
scripts/15_canopy_fraction.py). Outputs follow the project's tag convention – outputs/<scenario>/
<scenario>_<mode>_trees<nnn>.sww – so scripts 05/06 work on them with --tag; no existing file is overwritten.
Single-breach scenarios without a hydrology block only. Screening model, not a certified assessment.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, model, shelterbelts, terrain  # noqa: E402
from damflood.breach import read_hydrograph_csv  # noqa: E402


def circle(cx, cy, r, n=24):   # as scripts/04_run_model.py
    return [[cx + r * np.cos(a), cy + r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def split_footprint(fp, share):   # as scripts/04_run_model.py
    NW, NE, SE, SW = [np.array(p, float) for p in fp]
    n1 = NW + (NE - NW) * share; s1 = SW + (SE - SW) * share
    return [NW, n1, s1, SW], [n1, NE, SE, s1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="east")
    config.add_mode_arg(ap)
    ap.add_argument("--tree-n", type=float, default=None, help="Manning n under trees (default races.yaml shelterbelts.manning_n)")
    ap.add_argument("--no-trees", action="store_true", help="baseline on the identical mesh (tag _treesnone)")
    ap.add_argument("--finaltime-h", type=float)
    ap.add_argument("--mesh-only", action="store_true")
    a = ap.parse_args()
    site, dam, sc = config.site(), config.dam(), config.scenario(a.scenario)
    if sc.get("breaches") or sc.get("hydrology"):
        raise SystemExit("multi-breach / storm scenarios are not supported here")
    sb = config.load_yaml("races.yaml")["shelterbelts"]
    n_tree = a.tree_n or float(sb["manning_n"])
    mode = config.mode_from_args(a); ms = config.mode_settings(mode)
    bbox, dem_path, mesh_cfg, run_cfg = ms["bbox"], ms["dem_path"], ms["mesh"], ms["run"]
    canopy = config.DATA_DERIVED / f"canopy_fraction_{mode}_10m.tif"
    for p in (dem_path, canopy):
        if not p.exists():
            raise SystemExit(f"{p} not found (scripts/01_fetch_dem.py / scripts/15_canopy_fraction.py --mode {mode})")
    if a.no_trees:
        n_tree = float(dam["friction"]["default_manning_n"])
    tag = "_treesnone" if a.no_trees else f"_trees{int(round(n_tree * 100)):03d}"
    out_dir = config.scenario_dir(a.scenario)
    Q_raw = read_hydrograph_csv(out_dir / "hydrograph.csv")
    t0 = float(json.loads((out_dir / "breach_summary.json").read_text()).get("t_init_s") or 0.0)
    Q = lambda t: Q_raw(t + t0)
    finaltime = (a.finaltime_h or run_cfg["finaltime_h"]) * 3600; n0 = dam["friction"]["default_manning_n"]

    dem = terrain.DEM(dem_path); fp = site["site"]["footprint_nztm"]
    for poly, pond in zip(split_footprint(fp, site["site"]["pond1_share_of_width"]), ("pond1", "pond2")):
        dem.arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in poly], dam["ponds"][pond]["crest_mRL"])
    burned = out_dir / f"dem_burned_{mode}{tag}.tif"; dem.write(burned, dem.arr)
    cx, cy = site["site"]["footprint_centroid_nztm"]
    refine = [(circle(cx, cy, site["mesh"]["site_refine_radius_m"]), mesh_cfg["site_area_m2"]),
              (site["mesh"]["corridor_polygon_nztm"], mesh_cfg["corridor_area_m2"])]
    name = f"{a.scenario}_{mode}{tag}"
    domain, offset = model.build_domain(burned, bbox, mesh_cfg, refine, out_dir, name, n0)

    # equivalent n per triangle: canopy share in a window about the size of the triangle
    frac = terrain.DEM(canopy); c = domain.get_centroid_coordinates(absolute=True); side = np.sqrt(domain.areas)
    n = np.full(len(side), float(n0))
    for lo, hi, win in ((0, 25, 20.0), (25, 50, 40.0), (50, 1e9, 70.0)):
        sel = (side >= lo) & (side < hi)
        if sel.any():
            sm = terrain.DEM.__new__(terrain.DEM); sm.transform = frac.transform
            sm.arr = ndimage.uniform_filter(frac.arr, size=max(int(round(win / frac.res)), 1), mode="nearest")
            n[sel] = shelterbelts.equivalent_manning(sm.sample(c[sel, 0], c[sel, 1]), n0, n_tree)
    domain.set_quantity("friction", n, location="centroids")
    wt = n > n0 * 1.02
    stats = {"tree_n": n_tree, "triangles_with_trees": int(wt.sum()), "share_of_triangles": float(wt.mean()),
             "median_n_where_trees": float(np.median(n[wt])) if wt.any() else None, "max_n": float(n.max())}
    print(f"[trees] {stats}")
    if a.mesh_only:
        return

    L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
    loc = np.array(sc["breach_location_nztm"], float); d = np.array(sc["outward_dir"], float); d /= np.linalg.norm(d)
    t = np.array([-d[1], d[0]]); cc = loc + d * (10 + Wd / 2)
    poly = [cc - t * L / 2 - d * Wd / 2, cc + t * L / 2 - d * Wd / 2, cc + t * L / 2 + d * Wd / 2, cc - t * L / 2 + d * Wd / 2]
    model.add_inlet(domain, offset, poly, Q, label=f"breach_{a.scenario}")
    meta = {"scenario": a.scenario, "mode": mode, "bbox": bbox, "pre_breach_s": 0.0, "hydrology": None, "dem": str(dem_path),
            "triangles": int(domain.number_of_triangles), "manning_n": n0, "shelterbelts": stats, "finaltime_s": finaltime,
            "yieldstep_s": run_cfg["yieldstep_s"], "inlet_polygon": [list(map(float, p)) for p in poly],
            "flow_algorithm": mesh_cfg.get("flow_algorithm", "DE0"), "time_offset_s": t0, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Exploratory run with tree shelterbelts as roughness – screening model, not a certified assessment."}
    (out_dir / f"run_meta_{mode}{tag}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, run_cfg["yieldstep_s"], out_dir / f"run_log_{mode}{tag}.json")
    print(f"[trees] done -> {sww}")


if __name__ == "__main__":
    main()
