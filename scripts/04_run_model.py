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
    hydro = sc.get("hydrology") or {}
    pre = float(hydro.get("pre_breach_h", 0.0)) * 3600   # spin-up before the breach opens (storm scenarios)
    Q = lambda t, Q_raw=Q_raw, t0=t0, pre=pre: (Q_raw(t - pre + t0) if t >= pre else 0.0)
    print(f"[run] hydrograph time offset: simulation t={pre:.0f} s (breach opens) corresponds to t={t0:.0f} s in {hyd.name}")
    run_cfg = site["run"][mode]; mesh_cfg = site["mesh"][mode]
    finaltime = (a.finaltime_h or run_cfg["finaltime_h"]) * 3600 + pre; yieldstep = a.yieldstep_s or run_cfg["yieldstep_s"]
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

    # inlet patch just outside the embankment toe (one per external breach)
    L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
    def inlet_poly(loc, outward):
        loc = np.array(loc, float); d = np.array(outward, float); d /= np.linalg.norm(d)
        t = np.array([-d[1], d[0]]); c = loc + d * (10 + Wd / 2)
        return [c - t * L / 2 - d * Wd / 2, c + t * L / 2 - d * Wd / 2, c + t * L / 2 + d * Wd / 2, c - t * L / 2 + d * Wd / 2]
    external = [b for b in sc.get("breaches", []) if not b.get("feeds")]
    if external:
        polys = []
        for b in external:
            hb = out_dir / f"hydrograph_{b['name']}{a.tag}.csv"
            if not hb.exists():
                hb = out_dir / f"hydrograph_{b['name']}.csv"
            Qb_raw = read_hydrograph_csv(hb); Qb = lambda t, Qb_raw=Qb_raw, t0=t0: Qb_raw(t + t0)
            poly = inlet_poly(b["location_nztm"], b["outward_dir"]); polys.append(poly)
            model.add_inlet(domain, offset, poly, Qb, label=f"breach_{a.scenario}_{b['name']}")
        poly = polys[0]
    else:
        poly = inlet_poly(sc["breach_location_nztm"], sc["outward_dir"])
        model.add_inlet(domain, offset, poly, Q, label=f"breach_{a.scenario}")

    # storm hydrology: uniform net rain + rivers already in flood at the domain edge
    river_polys = []
    if hydro:
        net = float(hydro.get("rain_mm_h", 0.0)) - float(hydro.get("infiltration_mm_h", 0.0))
        if net > 0:
            model.add_rain(domain, net / 1000.0 / 3600.0)
        for rv in hydro.get("river_inflows", []):
            loc = rv["location_nztm"][mode] if isinstance(rv["location_nztm"], dict) else rv["location_nztm"]
            fd = rv["flow_dir"][mode] if isinstance(rv["flow_dir"], dict) else rv["flow_dir"]
            rp = inlet_poly(loc, fd); river_polys.append(rp)
            qr = float(rv["q_m3s"]); model.add_inlet(domain, offset, rp, lambda t, qr=qr: qr, label=f"river_{rv['name'].replace(' ', '_')}")
    meta = {"scenario": a.scenario, "mode": mode, "bbox": bbox, "pre_breach_s": pre, "hydrology": hydro or None,
            "river_inlet_polygons": [[list(map(float, p)) for p in pp] for pp in river_polys], "dem": str(dem_path), "hydrograph": str(hyd),
            "triangles": int(domain.number_of_triangles), "manning_n": manning, "finaltime_s": finaltime,
            "yieldstep_s": yieldstep, "inlet_polygon": [list(map(float, p)) for p in poly],
            "inlet_polygons": [[list(map(float, p)) for p in pp] for pp in (polys if external else [poly])],
            "flow_algorithm": mesh_cfg.get("flow_algorithm", "DE0"), "time_offset_s": t0,
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out_dir / f"run_meta_{mode}{a.tag}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, yieldstep, out_dir / f"run_log_{mode}{a.tag}.json")
    print(f"[run] done -> {sww}")


if __name__ == "__main__":
    main()
