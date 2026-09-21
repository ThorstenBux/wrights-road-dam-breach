#!/usr/bin/env python
"""EXPLORATORY: wet worst case – a breach scenario (single or multi-breach) with the storm hydrology and tree shelterbelts as independent switches.

As scripts/04_run_model.py / 16_run_shelterbelts.py (same DEM, pond block, site and corridor refinement, inlets),
plus a mesh refinement strip along the Eyre River so its channel and banks are resolved. Switches:
  --scenario east|quake|...   breach hydrograph(s) from outputs/<scenario>/ (scripts/03_breach_hydrograph.py)
  --hydrology storm           rain, river inflows and spin-up from that scenario's `hydrology:` block (omit = dry day)
  --river-q-factor 2          scale the river inflow (the 150 m3/s Eyre flood is an assumption without an AEP)
  --race-outfalls             add the dewatering flow that reaches the Eyre down the races (config/wet.yaml)
  --tree-n 0.20 | --no-trees  shelterbelts as equivalent roughness (scripts/15_canopy_fraction.py)
  --no-breach                 the same run without the breach: the baseline for breach-added depth and arrival
Outputs follow the tag convention – outputs/<scenario>/<scenario>_<mode>_<wet|dry>[_q2][_races]_trees<nnn>[_nobreach].sww –
so scripts 05/06 work with --tag (and --baseline-sww). No existing file is overwritten.
Screening model, not a certified assessment.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, model, shelterbelts, terrain, vectors, wet  # noqa: E402
from damflood.breach import read_hydrograph_csv  # noqa: E402


def circle(cx, cy, r, n=24):   # as scripts/04_run_model.py
    return [[cx + r * np.cos(a), cy + r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def split_footprint(fp, share):   # as scripts/04_run_model.py
    NW, NE, SE, SW = [np.array(p, float) for p in fp]
    n1 = NW + (NE - NW) * share; s1 = SW + (SE - SW) * share
    return [NW, n1, s1, SW], [n1, NE, SE, s1]


def run_tag(hydrology, q_factor, race_outfalls, n_tree, no_trees, no_breach) -> str:
    tag = "_wet" if hydrology else "_dry"
    if hydrology and abs(q_factor - 1.0) > 1e-9:
        tag += f"_q{q_factor:g}".replace(".", "p")
    if hydrology and race_outfalls:
        tag += "_races"
    tag += "_treesnone" if no_trees else f"_trees{int(round(n_tree * 100)):03d}"
    return tag + ("_nobreach" if no_breach else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="east")
    config.add_mode_arg(ap)
    ap.add_argument("--hydrology", default=None, help="scenario whose hydrology block to use, e.g. storm (default: dry day)")
    ap.add_argument("--river-q-factor", type=float, default=1.0)
    ap.add_argument("--race-outfalls", action="store_true")
    ap.add_argument("--tree-n", type=float, default=None, help="Manning n under trees (default races.yaml shelterbelts.manning_n)")
    ap.add_argument("--no-trees", action="store_true")
    ap.add_argument("--no-breach", action="store_true")
    ap.add_argument("--no-eyre-refine", action="store_true")
    ap.add_argument("--finaltime-h", type=float, help="hours AFTER the breach opens")
    ap.add_argument("--mesh-only", action="store_true")
    a = ap.parse_args()
    site, dam, sc = config.site(), config.dam(), config.scenario(a.scenario)
    wcfg = config.load_yaml("wet.yaml")
    hydro = (config.scenario(a.hydrology).get("hydrology") or {}) if a.hydrology else {}
    if a.hydrology and not hydro:
        raise SystemExit(f"scenario '{a.hydrology}' has no hydrology block")
    n0 = float(dam["friction"]["default_manning_n"])
    n_tree = n0 if a.no_trees else (a.tree_n or float(config.load_yaml("races.yaml")["shelterbelts"]["manning_n"]))
    mode = config.mode_from_args(a); ms = config.mode_settings(mode)
    bbox, dem_path, mesh_cfg, run_cfg = ms["bbox"], ms["dem_path"], ms["mesh"], ms["run"]
    canopy = config.DATA_DERIVED / f"canopy_fraction_{mode}_10m.tif"
    for p in [dem_path] + ([] if a.no_trees else [canopy]):
        if not p.exists():
            raise SystemExit(f"{p} not found (scripts/01_fetch_dem.py / scripts/15_canopy_fraction.py --mode {mode})")
    tag = run_tag(bool(hydro), a.river_q_factor, a.race_outfalls, n_tree, a.no_trees, a.no_breach)
    out_dir = config.scenario_dir(a.scenario)
    t0 = float(json.loads((out_dir / "breach_summary.json").read_text()).get("t_init_s") or 0.0)
    pre = float(hydro.get("pre_breach_h", 0.0)) * 3600
    finaltime = (a.finaltime_h or run_cfg["finaltime_h"]) * 3600 + pre

    dem = terrain.DEM(dem_path); fp = site["site"]["footprint_nztm"]
    for poly, pond in zip(split_footprint(fp, site["site"]["pond1_share_of_width"]), ("pond1", "pond2")):
        dem.arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in poly], dam["ponds"][pond]["crest_mRL"])
    burned = out_dir / f"dem_burned_{mode}{tag}.tif"; dem.write(burned, dem.arr)
    cx, cy = site["site"]["footprint_centroid_nztm"]
    refine = [(circle(cx, cy, site["mesh"]["site_refine_radius_m"]), mesh_cfg["site_area_m2"])]
    if not a.no_eyre_refine:   # before the corridor: earlier regions take precedence where they overlap
        eyre = wet.river_line(vectors.load(config.DATA_RAW / "osm_domain.gpkg", "waterways"), wcfg["eyre"]["name"], bbox, margin=100.0)
        refine.append((wet.river_strip(eyre, wcfg["eyre"]["refine_half_width_m"]), min(wcfg["eyre"]["refine_area_m2"], mesh_cfg["corridor_area_m2"])))
    refine.append((site["mesh"]["corridor_polygon_nztm"], mesh_cfg["corridor_area_m2"]))
    name = f"{a.scenario}_{mode}{tag}"
    domain, offset = model.build_domain(burned, bbox, mesh_cfg, refine, out_dir, name, n0)
    stats = None
    if not a.no_trees:
        n, stats = shelterbelts.fraction_friction(terrain.DEM(canopy), domain.get_centroid_coordinates(absolute=True),
                                                  domain.areas, n0, n_tree)
        domain.set_quantity("friction", n, location="centroids")
        print(f"[wet] trees {stats}")
    if a.mesh_only:
        return

    L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
    def inlet_poly(loc, outward):   # as scripts/04_run_model.py
        loc = np.array(loc, float); d = np.array(outward, float); d /= np.linalg.norm(d)
        t = np.array([-d[1], d[0]]); c = loc + d * (10 + Wd / 2)
        return [c - t * L / 2 - d * Wd / 2, c + t * L / 2 - d * Wd / 2, c + t * L / 2 + d * Wd / 2, c - t * L / 2 + d * Wd / 2]

    # breach inlets: one per external breach, every one of them delayed by the spin-up
    external = [b for b in sc.get("breaches", []) if not b.get("feeds")]
    parts = ([(b["name"], out_dir / f"hydrograph_{b['name']}.csv", b["location_nztm"], b["outward_dir"]) for b in external]
             or [("", out_dir / "hydrograph.csv", sc["breach_location_nztm"], sc["outward_dir"])])
    Qs, polys = [], []
    for bname, csv, loc, outward in parts:
        Qb = wet.delayed(read_hydrograph_csv(csv), pre, t0, on=not a.no_breach); Qs.append(Qb)
        polys.append(inlet_poly(loc, outward))
        model.add_inlet(domain, offset, polys[-1], Qb, label=f"breach_{a.scenario}" + (f"_{bname}" if bname else ""))
    Q = lambda t: sum(q(t) for q in Qs)

    # storm hydrology: uniform net rain + rivers already in flood at the domain edge (as scripts/04_run_model.py)
    river_polys, rivers = [], []
    if hydro:
        net = float(hydro.get("rain_mm_h", 0.0)) - float(hydro.get("infiltration_mm_h", 0.0))
        if net > 0:
            model.add_rain(domain, net / 1000.0 / 3600.0)
        outfalls = wcfg["race_outfalls"] if a.race_outfalls else []
        for rv in hydro.get("river_inflows", []):
            key = "production" if mode == "extended" else mode
            loc = rv["location_nztm"][key] if isinstance(rv["location_nztm"], dict) else rv["location_nztm"]
            fd = rv["flow_dir"][key] if isinstance(rv["flow_dir"], dict) else rv["flow_dir"]
            qr = float(rv["q_m3s"]) * a.river_q_factor + sum(float(o["q_m3s"]) for o in outfalls if o.get("to_river_inlet") == rv["name"])
            rp = inlet_poly(loc, fd); river_polys.append(rp); rivers.append({"name": rv["name"], "q_m3s": qr})
            model.add_inlet(domain, offset, rp, lambda t, qr=qr: qr, label=f"river_{rv['name'].replace(' ', '_')}")
        W, S, E, N = bbox
        for o in outfalls:
            if "location_nztm" in o and W < o["location_nztm"][0] < E and S < o["location_nztm"][1] < N:
                rp = inlet_poly(o["location_nztm"], o["flow_dir"]); river_polys.append(rp); qo = float(o["q_m3s"])
                rivers.append({"name": f"race {o['name']} outfall", "q_m3s": qo})
                model.add_inlet(domain, offset, rp, lambda t, qo=qo: qo, label=f"race_{o['name']}")
    meta = {"scenario": a.scenario, "mode": mode, "bbox": bbox, "pre_breach_s": pre, "hydrology": hydro or None,
            "hydrology_from": a.hydrology, "inflows": rivers, "breach": not a.no_breach, "eyre_refined": not a.no_eyre_refine,
            "river_inlet_polygons": [[list(map(float, p)) for p in pp] for pp in river_polys], "dem": str(dem_path),
            "triangles": int(domain.number_of_triangles), "manning_n": n0, "shelterbelts": stats, "finaltime_s": finaltime,
            "yieldstep_s": run_cfg["yieldstep_s"], "inlet_polygon": [list(map(float, p)) for p in polys[0]],
            "inlet_polygons": [[list(map(float, p)) for p in pp] for pp in polys],
            "flow_algorithm": mesh_cfg.get("flow_algorithm", "DE0"), "time_offset_s": t0, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Exploratory wet worst-case run – screening model, not a certified assessment."}
    (out_dir / f"run_meta_{mode}{tag}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, run_cfg["yieldstep_s"], out_dir / f"run_log_{mode}{tag}.json")
    print(f"[wet] done -> {sww}")


if __name__ == "__main__":
    main()
