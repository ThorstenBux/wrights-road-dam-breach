#!/usr/bin/env python
"""EXPLORATORY: Eyre River flood on the domain extended north and west to the river (config/north.yaml), with or without a breach.

scripts/18_run_wet_worstcase.py for the larger domain, with the river as a HYDROGRAPH (rise, peak, recession) entering
where the Eyre leaves the foothills instead of a constant inflow at the old north edge. Switches:
  --scenario north|east|quake   breach hydrograph(s) from outputs/<scenario>/ (scripts/03_breach_hydrograph.py)
  --hydrograph-tag _full        breach hydrograph variant (north: `_full` = breach cut down to the Pond 2 floor, A16)
  --river-peak 300              peak of the Eyre flood in m3/s (a SENSITIVITY value unless the docs note says otherwise); 0 = no river
  --rain-mm-h 10                steady rain on the whole domain, no infiltration (A9); default none
  --pre-breach-h 8              river (and rain) run this long before the breach opens
  --no-breach                   the same flood without the breach: the baseline for everything the breach adds
All runs share one mesh and one roughness (no trees), so any run can be differenced against its baseline.
Outputs: outputs/<scenario>/<scenario>_north_q<peak>[_rain<r>][<hydrograph-tag>][_nobreach].sww (+ run_meta / run_log).
No file of the main pipeline is overwritten. Screening model, not a certified assessment.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, model, north, terrain, vectors, wet  # noqa: E402
from damflood.breach import read_hydrograph_csv  # noqa: E402


def circle(cx, cy, r, n=24):   # as scripts/04_run_model.py
    return [[cx + r * np.cos(a), cy + r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def split_footprint(fp, share):   # as scripts/04_run_model.py
    NW, NE, SE, SW = [np.array(p, float) for p in fp]
    n1 = NW + (NE - NW) * share; s1 = SW + (SE - SW) * share
    return [NW, n1, s1, SW], [n1, NE, SE, s1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="north")
    ap.add_argument("--hydrograph-tag", default="")
    ap.add_argument("--river-peak", type=float, required=True)
    ap.add_argument("--rain-mm-h", type=float, default=0.0)
    ap.add_argument("--pre-breach-h", type=float, default=None)
    ap.add_argument("--no-breach", action="store_true")
    ap.add_argument("--finaltime-h", type=float, help="hours AFTER the breach opens")
    ap.add_argument("--mesh-only", action="store_true")
    a = ap.parse_args()
    site, dam, sc, ncfg = config.site(), config.dam(), config.scenario(a.scenario), config.load_yaml("north.yaml")
    wcfg = config.load_yaml("wet.yaml")["eyre"]; dom, mesh_cfg, hcfg = ncfg["domain"], ncfg["mesh"], ncfg["hydrograph"]
    bbox = dom["bbox_nztm"]; dem_path = config.DATA_DERIVED / dom["dem_name"]; gpkg = config.DATA_RAW / dom["osm_name"]
    for p in (dem_path, gpkg):
        if not p.exists():
            raise SystemExit(f"{p} not found (scripts/22_north_domain.py)")
    n0 = float(dam["friction"]["default_manning_n"])
    pre = float(hcfg["pre_breach_h"] if a.pre_breach_h is None else a.pre_breach_h) * 3600
    finaltime = (a.finaltime_h or ncfg["run"]["finaltime_h"]) * 3600 + pre
    tag = north.run_tag(dom["tag"], a.river_peak, a.rain_mm_h, a.hydrograph_tag, a.no_breach)
    out_dir = config.scenario_dir(a.scenario)
    summ = json.loads((out_dir / f"breach_summary{a.hydrograph_tag}.json").read_text())
    t0 = float(summ.get("t_init_s") or 0.0)

    dem = terrain.DEM(dem_path); fp = site["site"]["footprint_nztm"]
    for poly, pond in zip(split_footprint(fp, site["site"]["pond1_share_of_width"]), ("pond1", "pond2")):
        dem.arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in poly], dam["ponds"][pond]["crest_mRL"])
    burned = config.DATA_DERIVED / f"dem_burned_{dom['tag']}.tif"          # the same for every run of this script
    if not burned.exists():
        dem.write(burned, dem.arr)
    cx, cy = site["site"]["footprint_centroid_nztm"]
    eyre = wet.river_line(vectors.load(gpkg, "waterways"), wcfg["name"], bbox, margin=100.0)
    refine = [(circle(cx, cy, site["mesh"]["site_refine_radius_m"]), mesh_cfg["site_area_m2"]),      # earlier regions take precedence
              (wet.river_strip(eyre, wcfg["refine_half_width_m"]), min(wcfg["refine_area_m2"], mesh_cfg["corridor_area_m2"])),
              (site["mesh"]["corridor_polygon_nztm"], mesh_cfg["corridor_area_m2"]),
              (mesh_cfg["foreground_polygon_nztm"], mesh_cfg["foreground_area_m2"])]
    domain, offset = model.build_domain(burned, bbox, mesh_cfg, refine, out_dir, f"{a.scenario}{tag}", n0)
    if a.mesh_only:
        return

    L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
    def inlet_poly(loc, outward, L=L, Wd=Wd):   # as scripts/04_run_model.py
        loc = np.array(loc, float); d = np.array(outward, float); d /= np.linalg.norm(d)
        t = np.array([-d[1], d[0]]); c = loc + d * (10 + Wd / 2)
        return [c - t * L / 2 - d * Wd / 2, c + t * L / 2 - d * Wd / 2, c + t * L / 2 + d * Wd / 2, c - t * L / 2 + d * Wd / 2]

    # breach inlets: one per external breach, every one of them delayed by the spin-up (as scripts/18)
    external = [b for b in sc.get("breaches", []) if not b.get("feeds")]
    parts = ([(b["name"], out_dir / f"hydrograph_{b['name']}.csv", b["location_nztm"], b["outward_dir"]) for b in external]
             or [("", out_dir / f"hydrograph{a.hydrograph_tag}.csv", sc["breach_location_nztm"], sc["outward_dir"])])
    Qs, polys = [], []
    for bname, csv, loc, outward in parts:
        Qb = wet.delayed(read_hydrograph_csv(csv), pre, t0, on=not a.no_breach); Qs.append(Qb)
        polys.append(inlet_poly(loc, outward))
        model.add_inlet(domain, offset, polys[-1], Qb, label=f"breach_{a.scenario}" + (f"_{bname}" if bname else ""))
    Q = lambda t: sum(q(t) for q in Qs)

    rivers = []
    if a.river_peak > 0:
        loc, fd = north.river_inlet(eyre, hcfg["inlet_chainage_m"])
        Qr = north.gamma_hydrograph(a.river_peak, float(hcfg["base_m3s"]), float(hcfg["time_to_peak_h"]) * 3600, float(hcfg["shape"]))
        rp = inlet_poly(loc, fd, L=float(hcfg["inlet_size_m"][0]), Wd=float(hcfg["inlet_size_m"][1]))
        model.add_inlet(domain, offset, rp, Qr, label="river_Eyre")
        rivers.append({"name": wcfg["name"], "peak_m3s": a.river_peak, "base_m3s": hcfg["base_m3s"], "time_to_peak_h": hcfg["time_to_peak_h"],
                       "shape": hcfg["shape"], "location_nztm": [float(v) for v in loc], "flow_dir": [float(v) for v in fd],
                       "volume_Mm3": north.hydrograph_volume(Qr, finaltime) / 1e6, "polygon": [list(map(float, p)) for p in rp]})
    if a.rain_mm_h > 0:
        model.add_rain(domain, a.rain_mm_h / 1000.0 / 3600.0)
    meta = {"scenario": a.scenario, "mode": dom["tag"], "bbox": bbox, "pre_breach_s": pre, "rain_mm_h": a.rain_mm_h, "inflows": rivers,
            "hydrograph_tag": a.hydrograph_tag, "breach": not a.no_breach, "dem": str(dem_path), "triangles": int(domain.number_of_triangles),
            "manning_n": n0, "finaltime_s": finaltime, "yieldstep_s": ncfg["run"]["yieldstep_s"],
            "inlet_polygon": [list(map(float, p)) for p in polys[0]], "inlet_polygons": [[list(map(float, p)) for p in pp] for pp in polys],
            "flow_algorithm": mesh_cfg.get("flow_algorithm", "DE0"), "time_offset_s": t0, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Exploratory Eyre-flood run on the north-extended domain – screening model, not a certified assessment."}
    (out_dir / f"run_meta{tag}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, ncfg["run"]["yieldstep_s"], out_dir / f"run_log{tag}.json")
    print(f"[north] done -> {sww}")


if __name__ == "__main__":
    main()
