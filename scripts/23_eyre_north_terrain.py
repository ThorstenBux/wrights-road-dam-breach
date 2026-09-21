#!/usr/bin/env python
"""EXPLORATORY: can an Eyre River flood reach the north embankment at all? Terrain check WITHOUT a 2D model.

1. Bank-full capacity of the Eyre on the reach beside and up-river of the ponds (2 m LiDAR sections, the functions of
   scripts/20_eyre_capacity.py) and the normal-depth level for a list of SENSITIVITY flows (config/north.yaml).
2. Where would water that leaves the RIGHT (south) bank go? Steepest-descent paths over the depression-filled 20 m DEM
   from just outside the right-bank crest of every section; closest approach to the north embankment.
3. Levels: river bed / right-bank crest against the natural ground at the embankment toe and the crest levels, and how
   deep water could stand against the embankment before it drains away round the ponds (fill depth at the toe).
Writes outputs/north_eyre/eyre_north_sections.csv, terrain_check.json, terrain_check.png.
Screening model, not a certified assessment.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, north, terrain, vectors, wet  # noqa: E402

_spec = importlib.util.spec_from_file_location("eyre_capacity", Path(__file__).with_name("20_eyre_capacity.py"))
cap = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cap)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chunk-km", type=float, default=4.0)
    ap.add_argument("--half-width", type=float, default=600.0, help="section half width (the bed is wider here than down-river)")
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    site, dam, ncfg, wcfg = config.site(), config.dam(), config.load_yaml("north.yaml"), config.load_yaml("wet.yaml")["eyre"]
    bbox = ncfg["domain"]["bbox_nztm"]; out = config.OUTPUTS / "north_eyre"; out.mkdir(parents=True, exist_ok=True)
    gpkg = config.DATA_RAW / ncfg["domain"]["osm_name"]
    if not gpkg.exists():
        gpkg = config.DATA_RAW / "osm_domain.gpkg"          # the Eyre geometry in it already extends beyond its bbox
    hw = a.half_width
    line = wet.river_line(vectors.load(gpkg, "waterways"), ncfg["eyre"]["name"], bbox, margin=hw + 50)
    smooth = line.simplify(60.0)
    fp = np.array(site["site"]["footprint_nztm"], float); NW, NE = fp[0], fp[1]
    emb = LineString([NW, NE]); s_site = line.project(Point(*((NW + NE) / 2)))
    s0 = max(s_site - ncfg["eyre"]["reach_chainage_from_site_km"] * 1000, 0.0)
    s1 = min(s_site + ncfg["eyre"]["reach_chainage_below_site_km"] * 1000, line.length)
    sp, res, n = wcfg["section_spacing_m"], wcfg["capacity_dem_res_m"], wcfg["manning_n"]
    stations = np.arange(s0 + sp / 2, s1, sp); flows = [float(q) for q in ncfg["eyre"]["flows_m3s"]]

    # --- 1. sections -------------------------------------------------------------------------------------------
    cache = config.DATA_DERIVED / "eyre_dem"; cache.mkdir(parents=True, exist_ok=True)
    rows = []; per_chunk = max(int(round(a.chunk_km * 1000 / sp)), 1)
    for c0 in range(0, len(stations), per_chunk):
        st = stations[c0:c0 + per_chunk]; pts = [line.interpolate(d) for d in st]
        bb = [min(p.x for p in pts) - hw - 60, min(p.y for p in pts) - hw - 60, max(p.x for p in pts) + hw + 60, max(p.y for p in pts) + hw + 60]
        bb = [float(np.floor(v / res) * res) for v in bb]
        p = cache / f"eyre_north_{int(bb[0])}_{int(bb[1])}_{int(bb[2])}_{int(bb[3])}_{res:g}m.tif"    # keyed by extent: stations move with the domain
        if not p.exists():
            terrain.fetch_dem(bb, res, p, site["dem"]["bucket"], site["dem"]["collection"], verbose=False)
        dem = terrain.DEM(p); print(f"[north] chunk {c0 // per_chunk}: {len(st)} sections", flush=True)
        for d, pt in zip(st, pts):
            q = smooth.project(pt); p0, p1 = smooth.interpolate(max(q - 40, 0)), smooth.interpolate(min(q + 40, smooth.length))
            tx, ty = p1.x - p0.x, p1.y - p0.y; L = np.hypot(tx, ty); lx, ly = -ty / L, tx / L      # unit vector to the LEFT bank
            s = np.arange(-hw, hw + res, res); z = dem.sample(pt.x + s * lx, pt.y + s * ly)       # s > 0 = left bank
            rows.append({"chainage_m": float(d), "E": pt.x, "N": pt.y, "_s": s - s[0], "_z": z[::-1], "_l": (lx, ly)})   # stored left -> right
    th = np.array([r["_z"].min() for r in rows]); ch = np.array([r["chainage_m"] for r in rows])
    for i, r in enumerate(rows):
        near = np.abs(ch - ch[i]) <= 1000
        slope = max(-np.polyfit(ch[near], th[near], 1)[0], 1e-4)
        s, z = r["_s"], r["_z"]
        r.update(cap.section_capacity(s, z, n, slope, wcfg["thalweg_search_m"])); r["slope"] = float(slope)
        mid = np.abs(s - s.mean()) <= wcfg["thalweg_search_m"]; i0 = int(np.argmin(np.where(mid, z, np.inf)))
        ir = i0 + int(np.argmax(z[i0:])); lx, ly = r["_l"]                                         # right-bank crest position
        off = (s[ir] - s.mean()) + 30.0                                                           # 30 m beyond it, away from the river
        r["right_crest_E"], r["right_crest_N"] = r["E"] - off * lx, r["N"] - off * ly
        for Q in flows:
            h = cap.stage_for(s, z, n, slope, Q, r["thalweg_mRL"])
            r[f"level_{Q:g}_mRL"] = r["thalweg_mRL"] + h
            r[f"over_right_{Q:g}_m"] = r["thalweg_mRL"] + h - r["crest_right_mRL"]
            r[f"over_left_{Q:g}_m"] = r["thalweg_mRL"] + h - r["crest_left_mRL"]

    # --- 2. where does right-bank overflow go? -------------------------------------------------------------------
    d20 = terrain.DEM(config.DATA_DERIVED / ncfg["domain"]["dem_name"]); tr = d20.transform
    print("[north] filling depressions of the 20 m DEM ...", flush=True)
    filled = north.fill_depressions(d20.arr)
    rc = lambda x, y: (int((y - tr.f) / tr.e), int((x - tr.c) / tr.a))
    xy = lambda p: np.c_[tr.c + (p[:, 1] + 0.5) * tr.a, tr.f + (p[:, 0] + 0.5) * tr.e]
    paths = []
    for r in rows:
        p = xy(north.trace_downhill(filled, *rc(r["right_crest_E"], r["right_crest_N"])))
        dist = np.array([emb.distance(Point(*q)) for q in p[::3]]) if len(p) else np.array([np.inf])
        r["path_min_dist_to_north_embankment_m"] = float(dist.min()); r["path_length_km"] = float(len(p) * tr.a / 1000)
        r["path_end_E"], r["path_end_N"] = (float(p[-1, 0]), float(p[-1, 1])) if len(p) else (np.nan, np.nan)
        paths.append(p)

    # --- 3. levels at the embankment -----------------------------------------------------------------------------
    ecfg = ncfg["embankment"]; toe = north.embankment_samples(NW, NE, ecfg["sample_spacing_m"], ecfg["toe_offset_m"])
    toe_z = d20.sample(toe[:, 0], toe[:, 1]); r_, c_ = zip(*[rc(x, y) for x, y in toe])
    pond_depth = filled[list(r_), list(c_)] - d20.arr[list(r_), list(c_)]
    share = site["site"]["pond1_share_of_width"]; s_toe = np.arange(len(toe)) * ecfg["sample_spacing_m"]
    crest = np.where(s_toe < share * emb.length, dam["ponds"]["pond1"]["crest_mRL"], dam["ponds"]["pond2"]["crest_mRL"])
    # the reverse question: from which ground can water run to the north embankment at all? D8 = its catchment in the usual
    # sense; "any path" = every cell with SOME descending route to it (generous outer bound for spreading sheet flow).
    print("[north] upslope area of the north embankment ...", flush=True)
    import shapely
    from shapely.geometry import Polygon
    yy, xx = np.mgrid[0:d20.arr.shape[0], 0:d20.arr.shape[1]]; X, Y = tr.c + (xx + 0.5) * tr.a, tr.f + (yy + 0.5) * tr.e
    pts = shapely.points(X.ravel(), Y.ravel())
    target = (shapely.distance(pts, emb).reshape(X.shape) < 150.0) & ~shapely.contains(Polygon(fp), pts).reshape(X.shape)
    up8, upany = north.upslope_mask(filled, target), north.upslope_mask(filled, target, multiple=True)
    near_emb = shapely.distance(pts, emb).reshape(X.shape) < 250.0
    print("[north] spreading the overflow of the sections inside that area ...", flush=True)
    for r in rows:
        cell = rc(r["right_crest_E"], r["right_crest_N"])
        r["right_bank_in_d8_catchment"] = bool(up8[cell]); r["right_bank_in_anypath_area"] = bool(upany[cell])
        r["mfd_share_at_north_embankment"] = 0.0
        if upany[cell]:       # one unit of overflow, passed on to ALL lower neighbours: how much passes within 250 m of the embankment?
            src = np.zeros(d20.arr.shape); src[cell] = 1.0
            r["mfd_share_at_north_embankment"] = float(north.spread_downhill(filled, src)[near_emb].max())
    near_pt = line.interpolate(s_site); i_near = int(np.argmin(np.abs(ch - s_site)))

    for r in rows:
        for k in ("_s", "_z", "_l"):
            r.pop(k)
    df = pd.DataFrame(rows); df["chainage_rel_site_km"] = (df["chainage_m"] - s_site) / 1000
    df.round(3).to_csv(out / "eyre_north_sections.csv", index=False)
    hit = df[df["path_min_dist_to_north_embankment_m"] < 250]
    summ = {"note": "exploratory screening – not a certified assessment. Static terrain check: no volumes, no losses, no momentum; "
                    "flows are sensitivity values without a return period.",
            "reach_km": [float(s0 / 1000), float(s1 / 1000)], "sections": int(len(df)), "section_half_width_m": hw, "manning_n": n,
            "river_point_nearest_embankment_nztm": [near_pt.x, near_pt.y], "distance_river_to_embankment_km": float(emb.distance(line) / 1000),
            "river_thalweg_at_nearest_point_mRL": float(df["thalweg_mRL"].iloc[i_near]),
            "right_crest_at_nearest_point_mRL": float(df["crest_right_mRL"].iloc[i_near]),
            "toe_ground_mRL_min_median_max": [float(toe_z.min()), float(np.median(toe_z)), float(toe_z.max())],
            "embankment_height_above_toe_m_min_max": [float((crest - toe_z).min()), float((crest - toe_z).max())],
            "max_static_ponding_depth_at_toe_m": float(pond_depth.max()),
            "capacity_m3s_percentiles_5_25_50_75": [float(v) for v in np.percentile(df["capacity_m3s"], [5, 25, 50, 75])],
            "limiting_bank_share_right": float((df["limiting_bank"] == "right").mean()),
            "sections_whose_right_bank_overflow_path_passes_within_250m_of_north_embankment": int(len(hit)),
            "their_chainage_rel_site_km": [round(float(v), 2) for v in hit["chainage_rel_site_km"]],
            "closest_path_approach_m": float(df["path_min_dist_to_north_embankment_m"].min()),
            "north_embankment_d8_catchment_km2": float(up8.sum() * tr.a ** 2 / 1e6),
            "north_embankment_anypath_area_km2": float(upany.sum() * tr.a ** 2 / 1e6),
            "sections_with_right_bank_in_anypath_area": int(df["right_bank_in_anypath_area"].sum()),
            "their_chainage_rel_site_km_from_to": ([float(df.loc[df["right_bank_in_anypath_area"], "chainage_rel_site_km"].min()),
                                                    float(df.loc[df["right_bank_in_anypath_area"], "chainage_rel_site_km"].max())]
                                                   if df["right_bank_in_anypath_area"].any() else None),
            "their_E_from_to": ([float(df.loc[df["right_bank_in_anypath_area"], "E"].min()), float(df.loc[df["right_bank_in_anypath_area"], "E"].max())]
                                if df["right_bank_in_anypath_area"].any() else None),
            "their_capacity_m3s_min_median": ([float(df.loc[df["right_bank_in_anypath_area"], "capacity_m3s"].min()),
                                               float(df.loc[df["right_bank_in_anypath_area"], "capacity_m3s"].median())]
                                              if df["right_bank_in_anypath_area"].any() else None),
            "largest_mfd_share_of_right_bank_overflow_at_north_embankment": float(df["mfd_share_at_north_embankment"].max()),
            "by_flow": {}}
    for Q in flows:
        o = df[df[f"over_right_{Q:g}_m"] > 0]; oh = o[o["path_min_dist_to_north_embankment_m"] < 250]
        summ["by_flow"][f"{Q:g}"] = {"sections_over_right_bank": int(len(o)), "sections_over_left_bank": int((df[f"over_left_{Q:g}_m"] > 0).sum()),
                                     "of_those_right_with_path_to_embankment": int(len(oh)),
                                     "normal_depth_m_median_max": [float((df[f"level_{Q:g}_mRL"] - df["thalweg_mRL"]).median()), float((df[f"level_{Q:g}_mRL"] - df["thalweg_mRL"]).max())],
                                     "chainage_rel_site_km_over_right": [round(float(v), 2) for v in o["chainage_rel_site_km"]]}
    (out / "terrain_check.json").write_text(json.dumps(summ, indent=2))

    fig = plt.figure(figsize=(15, 10)); ax = fig.add_axes([0.04, 0.41, 0.92, 0.52])
    W, S, E, N = bbox; sub = d20.arr
    ax.imshow(sub, extent=[d20.bounds.left, d20.bounds.right, d20.bounds.bottom, d20.bounds.top], cmap="terrain", vmin=60, vmax=420)
    ax.contour(np.linspace(d20.bounds.left, d20.bounds.right, sub.shape[1]), np.linspace(d20.bounds.top, d20.bounds.bottom, sub.shape[0]), sub,
               levels=np.arange(100, 420, 5), colors="k", linewidths=0.25)
    ax.imshow(np.where(upany, 1.0, np.nan), extent=[d20.bounds.left, d20.bounds.right, d20.bounds.bottom, d20.bounds.top], cmap="Reds", alpha=0.3, vmin=0, vmax=1.3)
    ax.imshow(np.where(up8, 1.0, np.nan), extent=[d20.bounds.left, d20.bounds.right, d20.bounds.bottom, d20.bounds.top], cmap="Purples", alpha=0.9, vmin=0, vmax=1.2)
    for p, r in zip(paths, rows):
        if len(p):
            ax.plot(p[:, 0], p[:, 1], color="#c53030" if r["path_min_dist_to_north_embankment_m"] < 250 else "#2b6cb0", lw=0.6, alpha=0.8)
    ax.plot(*line.xy, color="navy", lw=1.5); ax.plot(*np.r_[fp, fp[:1]].T, color="m", lw=2)
    ax.set_xlim(W, 1546000); ax.set_ylim(5193000, N); ax.set_aspect("equal")
    ax.set_title("Blue lines: where water leaving the RIGHT (south) bank of the Eyre would run (steepest descent, filled 20 m LiDAR). Purple: catchment of the north embankment. "
                 "Red shade: all ground with SOME downhill route to it.\nContours 5 m. Exploratory screening, not a certified assessment", fontsize=9)
    ax2 = fig.add_axes([0.06, 0.06, 0.88, 0.30]); km = df["chainage_rel_site_km"]
    ax2.plot(km, df["thalweg_mRL"], color="navy", label="Eyre bed (LiDAR thalweg)")
    ax2.plot(km, df["crest_right_mRL"], color="#c05621", lw=0.8, label="right (south) bank crest within the section")
    ax2.plot(km, df["crest_left_mRL"], color="#2f855a", lw=0.8, label="left (north) bank crest")
    ax2.axhspan(float(toe_z.min()), float(toe_z.max()), color="m", alpha=0.25, label="natural ground at the north embankment toe")
    ax2.axhline(dam["ponds"]["pond2"]["crest_mRL"], color="m", ls="--", lw=0.8, label="Pond 2 crest 224.3 / Pond 1 crest 228.0")
    ax2.axhline(dam["ponds"]["pond1"]["crest_mRL"], color="m", ls="--", lw=0.8)
    ax2.set_xlabel("distance along the Eyre relative to the point nearest the ponds (km, negative = up-river)"); ax2.set_ylabel("m NZVD2016")
    ax2.legend(fontsize=7, ncol=3); ax2.grid(alpha=0.3)
    fig.savefig(out / "terrain_check.png", dpi=120)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
