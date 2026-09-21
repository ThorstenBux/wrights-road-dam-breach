#!/usr/bin/env python
"""EXPLORATORY: 2D run with the water races (MR4, R2, R3) in the mesh – emergency dewatering down the races,
with or without the east breach afterwards.

Cases (same mesh, same terrain, same breach hydrograph, so the runs can be differenced):
  dewater         races carry the dewatering flows for `dewater_h`; no breach          (the EAP App. F.6 case)
  dewater_breach  as above, then the east breach opens
  breach_dry      no dewatering flow; the breach opens at the same model time onto dry races

Reads config/races.yaml, writes to outputs/races/; nothing here is used by scripts 01-10.
Screening model, not a certified assessment.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, model, races, terrain  # noqa: E402
from damflood.breach import read_hydrograph_csv  # noqa: E402

CASES = ("dewater", "dewater_breach", "breach_dry")


def split_footprint(fp, share):   # as scripts/04_run_model.py
    NW, NE, SE, SW = [np.array(p, float) for p in fp]
    n1 = NW + (NE - NW) * share; s1 = SW + (SE - SW) * share
    return [NW, n1, s1, SW], [n1, NE, SE, s1]


def circle(cx, cy, r, n=24):
    return [[cx + r * np.cos(a), cy + r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def strip(xy, i0, i1, halfwidth):
    """Rectangle along the race between stations i0 and i1."""
    a, b = xy[i0], xy[i1]
    t = (b - a) / np.linalg.norm(b - a); n = np.array([-t[1], t[0]]) * halfwidth
    return [a - n, b - n, b + n, a + n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", choices=CASES, default="dewater")
    ap.add_argument("--crossings", choices=("open", "blocked"), default="open")
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--hydrograph", type=Path, default=None, help="breach hydrograph CSV (default: script 11 output)")
    ap.add_argument("--dewater-h", type=float, default=None)
    ap.add_argument("--after-breach-h", type=float, default=None)
    ap.add_argument("--finaltime-s", type=float, default=None, help="override the run length (smoke tests)")
    ap.add_argument("--yieldstep-s", type=float, default=None)
    ap.add_argument("--shelterbelts", action="store_true",
                    help="add tree shelterbelts (LiDAR canopy height) as extra roughness; outputs get the _trees suffix")
    ap.add_argument("--rain-mm-h", type=float, default=0.0,
                    help="steady rain on the whole domain for the whole run, no infiltration (wet worst case); outputs get the _wet suffix")
    ap.add_argument("--mesh-only", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    rc, site, dam, sc = config.load_yaml("races.yaml"), config.site(), config.dam(), config.scenario(a.scenario)
    dom, cond, run = rc["domain"], rc["conditioning"], rc["run"]
    bbox = dom["bbox_nztm"]
    dewater_s = (run["dewater_h"] if a.dewater_h is None else a.dewater_h) * 3600
    after_s = (run["after_breach_h"] if a.after_breach_h is None else a.after_breach_h) * 3600
    finaltime = a.finaltime_s or (dewater_s + (after_s if a.case != "dewater" else 0.0))
    yieldstep = a.yieldstep_s or run["yieldstep_s"]
    out_dir = config.OUTPUTS / "races"; out_dir.mkdir(parents=True, exist_ok=True)
    if a.shelterbelts:
        a.tag += "_trees"
    if a.rain_mm_h > 0:
        a.tag += "_wet"
    name = f"races_{a.case}_{a.crossings}{a.tag}"

    dem_path = config.DATA_DERIVED / f"dem_races_{dom['dem_res_m']:g}m.tif"
    if not dem_path.exists():
        terrain.fetch_dem(bbox, dom["dem_res_m"], dem_path, site["dem"]["bucket"], site["dem"]["collection"])
    gpkg = config.DATA_RAW / "osm_domain.gpkg"
    if not gpkg.exists():
        raise SystemExit(f"{gpkg} not found – run scripts/02_fetch_vectors.py")
    ww = gpd.read_file(gpkg, layer="waterways")

    # terrain: ponds as solid blocks (as script 04), then the race beds
    dem = terrain.DEM(dem_path)
    fp = site["site"]["footprint_nztm"]
    for poly, pond in zip(split_footprint(fp, site["site"]["pond1_share_of_width"]), ("pond1", "pond2")):
        dem.arr = terrain.burn_solid_block(dem, [list(map(float, p)) for p in poly], dam["ponds"][pond]["crest_mRL"])
    lidar = terrain.DEM(dem_path)   # thalwegs are read from the untouched LiDAR
    footprint = Polygon(fp)
    thalwegs, summary = [], {}
    for rname, r in rc["races"].items():
        line = races.clip_to_bbox(races.follow_chain(ww, r["start_osm_id"]), bbox)
        th = races.snap_thalweg(lidar, line, rname, cond["station_m"], cond["snap_search_m"], cond["crossing_hump_m"])
        if footprint.buffer(5).intersects(th.line):
            raise SystemExit(f"race {rname} runs through the pond footprint – start the chain further downstream")
        dem.arr = races.burn_bed(dem, dem.arr, th, r["bed_width_m"], crossings_open=(a.crossings == "open"))
        cap = races.bankfull_capacity(th, r["bed_width_m"], run["race_manning_n"])
        summary[rname] = {"length_km": th.s[-1] / 1000, "crossings": len(th.crossings), **cap,
                          "dewater_q_m3s": r["dewater_q_m3s"]}
        print(f"[races] {rname}: {th.s[-1]/1000:.1f} km, {len(th.crossings)} crossings ({a.crossings}), "
              f"bank-full ~{cap['bankfull_Q_m3s']:.0f} m3/s (LiDAR water surface as bed), dewatering {r['dewater_q_m3s']} m3/s")
        thalwegs.append(th)
    burned = out_dir / f"dem_{name}.tif"
    dem.write(burned, dem.arr)
    gpd.GeoDataFrame(
        [{"race": th.name, "kind": "thalweg", "geometry": th.line} for th in thalwegs] +
        [{"race": th.name, "kind": "crossing", "hump_m": c["hump_m"], "geometry": Point(c["x"], c["y"])}
         for th in thalwegs for c in th.crossings], crs=2193).to_file(out_dir / "races_conditioning.gpkg", driver="GPKG")

    mesh = {"max_area_m2": dom["max_area_m2"], "flow_algorithm": run["flow_algorithm"]}
    # no interior refinement regions: breaklines crossing a region boundary leave pockets without an area limit
    refine = []
    domain, offset = races.build_domain(
        burned, bbox, mesh, refine, [e for th, r in zip(thalwegs, rc["races"].values()) for e in th.bed_edges(r["bed_width_m"])],
        out_dir, name, run["manning_n"],
        race_friction=run["race_manning_n"], race_halfwidths=[r["bed_width_m"] + 3 for r in rc["races"].values() for _ in (0, 1)])
    if a.shelterbelts:
        from damflood import shelterbelts
        sb = rc["shelterbelts"]
        dsm_path = config.DATA_DERIVED / f"dsm_races_{dom['dem_res_m']:g}m.tif"
        if not dsm_path.exists():
            terrain.fetch_dem(bbox, dom["dem_res_m"], dsm_path, site["dem"]["bucket"], sb["dsm_collection"])
        mask, _ = shelterbelts.canopy_mask(terrain.DEM(dsm_path), lidar, sb["min_height_m"],
                                           gpd.read_file(gpkg, layer="buildings"))
        fr = domain.quantities["friction"].centroid_values
        n = shelterbelts.triangle_friction(mask, lidar, domain.get_centroid_coordinates(absolute=True), domain.areas,
                                           run["manning_n"], sb["manning_n"])
        keep = np.isclose(fr, run["race_manning_n"])            # the race beds keep their own roughness
        domain.set_quantity("friction", np.where(keep, fr, n), location="centroids")
        summary["shelterbelts"] = {"canopy_km2": float(mask.sum() * lidar.res ** 2 / 1e6), "manning_n": sb["manning_n"],
                                   "triangles_with_trees": int((n > run["manning_n"] * 1.02).sum()),
                                   "median_n_where_trees": float(np.median(n[n > run["manning_n"] * 1.02]))}
        print(f"[races] shelterbelts: {summary['shelterbelts']}")
    if a.mesh_only:
        return

    # dewatering inflows at the head of each race (none for breach_dry)
    Qs = []
    if a.case != "breach_dry":
        for th, r in zip(thalwegs, rc["races"].values()):
            q = float(r["dewater_q_m3s"])
            Qd = lambda t, q=q: q if t < dewater_s else 0.0
            model.add_inlet(domain, offset, strip(th.xy, 2, 10, r["bed_width_m"] / 2 + 3), Qd, label=f"dewater_{th.name}")
            Qs.append(Qd)
    # the breach (none for dewater)
    if a.case != "dewater":
        hyd = a.hydrograph or (config.OUTPUTS / "dewatering" / a.scenario /
                               f"hydrograph_dewater{dewater_s/3600:g}h_high.csv")
        if not hyd.exists():
            raise SystemExit(f"{hyd} not found – run scripts/11_dewatering_sensitivity.py --write-hydrograph {dewater_s/3600:g}")
        Q_raw = read_hydrograph_csv(hyd)
        t0 = float(json.loads(hyd.with_suffix(".json").read_text()).get("t_init_s") or 0.0)
        Qb = lambda t: Q_raw(t - dewater_s + t0) if t >= dewater_s else 0.0
        L, Wd = dam["breach_defaults"]["inlet_polygon_size_m"]
        loc = np.array(sc["breach_location_nztm"], float); d = np.array(sc["outward_dir"], float); d /= np.linalg.norm(d)
        tt = np.array([-d[1], d[0]]); c = loc + d * (10 + Wd / 2)
        poly = [c - tt * L / 2 - d * Wd / 2, c + tt * L / 2 - d * Wd / 2, c + tt * L / 2 + d * Wd / 2, c - tt * L / 2 + d * Wd / 2]
        model.add_inlet(domain, offset, poly, Qb, label=f"breach_{a.scenario}")
        Qs.append(Qb)
    Q = lambda t: sum(q(t) for q in Qs)
    if a.rain_mm_h > 0:
        model.add_rain(domain, a.rain_mm_h / 1000.0 / 3600.0)

    meta = {"case": a.case, "rain_mm_h": a.rain_mm_h, "crossings": a.crossings, "scenario": a.scenario, "bbox": bbox, "t_breach_s": dewater_s,
            "finaltime_s": finaltime, "yieldstep_s": yieldstep, "triangles": int(domain.number_of_triangles),
            "races": summary, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Exploratory screening run, not a certified assessment. Race names, the R2/R3 split, culvert "
                    "treatment (open cut or fully blocked) and bed levels (LiDAR water surface) are assumptions."}
    (out_dir / f"run_meta_{name}.json").write_text(json.dumps(meta, indent=2))
    sww = model.run(domain, Q, finaltime, yieldstep, out_dir / f"run_log_{name}.json")
    print(f"[races] done -> {sww}")


if __name__ == "__main__":
    main()
