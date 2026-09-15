#!/usr/bin/env python
"""Run the ANUGA 2D flood routing for a scenario using its breach hydrograph."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, model, terrain  # noqa: E402
from damflood.breach import read_hydrograph_csv  # noqa: E402


def circle(cx, cy, r, n=24):
    return [[cx + r * np.cos(a), cy + r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def split_footprint(fp, share):
    """Split the footprint quad (NW, NE, SE, SW) into Pond 1 (west `share`) and Pond 2."""
    NW, NE, SE, SW = [np.array(p, float) for p in fp]
    n1 = NW + (NE - NW) * share; s1 = SW + (SE - SW) * share
    return [NW, n1, s1, SW], [n1, NE, SE, s1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--production", action="store_true", help="full domain / fine mesh (default: shakedown)")
    ap.add_argument("--dem", type=Path)
    ap.add_argument("--hydrograph", type=Path)
    ap.add_argument("--finaltime-h", type=float)
    ap.add_argument("--yieldstep-s", type=float)
    ap.add_argument("--manning", type=float)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    site, dam = config.site(), config.dam(); sc = config.scenario(a.scenario)
    mode = "production" if a.production else "shakedown"
    bbox = site["domain"]["bbox_nztm"] if a.production else site["domain"]["shakedown_bbox_nztm"]
    res = site["dem"]["resolution_m"] if a.production else site["dem"]["shakedown_resolution_m"]
    dem_path = a.dem or (config.DATA_DERIVED / f"dem_{'full' if a.production else 'shakedown'}_{res:g}m.tif")
    if not dem_path.exists():
        raise SystemExit(f"DEM not found: {dem_path} – run scripts/01_fetch_dem.py{' --full' if a.production else ''}")
    out_dir = config.scenario_dir(a.scenario)
    hyd = a.hydrograph or (out_dir / "hydrograph.csv")
    if not hyd.exists():
        raise SystemExit(f"Hydrograph not found: {hyd} – run scripts/03_breach_hydrograph.py --scenario {a.scenario}")
    Q_raw = read_hydrograph_csv(hyd)
    # Start the 2D simulation when water first leaves the ponds (cascade: Pond 2 breach initiation).
    summ_path = out_dir / "breach_summary.json"
    t0 = float(json.loads(summ_path.read_text()).get("t_init_s") or 0.0) if summ_path.exists() else 0.0
    Q = lambda t, Q_raw=Q_raw, t0=t0: Q_raw(t + t0)
    print(f"[run] hydrograph time offset: simulation t=0 corresponds to t={t0:.0f} s in {hyd.name}")
    run_cfg = site["run"][mode]; mesh_cfg = site["mesh"][mode]
    finaltime = (a.finaltime_h or run_cfg["finaltime_h"]) * 3600; yieldstep = a.yieldstep_s or run_cfg["yieldstep_s"]
    manning = a.manning or dam["friction"]["default_manning_n"]

    # terrain: burn the full ponds as a solid block at crest level
    fp = site["site"]["footprint_nztm"]
    p1, p2 = split_footprint(fp, site["site"]["pond1_share_of_width"])
    dem = terrain.DEM(dem_path)
    arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in p1], dam["ponds"]["pond1"]["crest_mRL"])
    dem.arr = arr
    arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in p2], dam["ponds"]["pond2"]["crest_mRL"])
    burned = out_dir / f"dem_burned_{mode}{a.tag}.tif"
    dem.write(burned, arr)
    print(f"[run] burned ponds into DEM -> {burned}")

    cx, cy = site["site"]["footprint_centroid_nztm"]
    refine = [(circle(cx, cy, site["mesh"]["site_refine_radius_m"]), mesh_cfg["site_area_m2"]),
              (site["mesh"]["corridor_polygon_nztm"], mesh_cfg["corridor_area_m2"])]
    name = f"{a.scenario}_{mode}{a.tag}"
    domain, offset = model.build_domain(burned, bbox, mesh_cfg, refine, out_dir, name, manning)

    # inlet patch just outside the embankment toe
    loc = np.array(sc["breach_location_nztm"], float); d = np.array(sc["outward_dir"], float); d /= np.linalg.norm(d)
    t = np.array([-d[1], d[0]])
    L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
    c = loc + d * (10 + Wd / 2)
    poly = [c - t * L / 2, c + t * L / 2, c + t * L / 2 + d * Wd, c - t * L / 2 + d * Wd]
    poly = [c - t * L / 2 - d * Wd / 2, c + t * L / 2 - d * Wd / 2, c + t * L / 2 + d * Wd / 2, c - t * L / 2 + d * Wd / 2]
    model.add_inlet(domain, offset, poly, Q, label=f"breach_{a.scenario}")

    meta = {"scenario": a.scenario, "mode": mode, "bbox": bbox, "dem": str(dem_path), "hydrograph": str(hyd),
            "triangles": int(domain.number_of_triangles), "manning_n": manning, "finaltime_s": finaltime,
            "yieldstep_s": yieldstep, "inlet_polygon": [list(map(float, p)) for p in poly],
            "flow_algorithm": mesh_cfg.get("flow_algorithm", "DE0"), "time_offset_s": t0,
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out_dir / f"run_meta_{mode}{a.tag}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, yieldstep, out_dir / f"run_log_{mode}{a.tag}.json")
    print(f"[run] done -> {sww}")


if __name__ == "__main__":
    main()
