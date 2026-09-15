#!/usr/bin/env python
"""Export an ANUGA run to a compact dataset for the WebGL 3D flood animation.

Writes outputs/<scenario>/webgl/data.js defining window.FLOOD = {
  meta: {scenario, bbox, nx, ny, cell, z0, zscale, dscale, times_h, q_m3s, area_km2, footprint, offset_h},
  dem:   base64 Uint16 (elevation = z0 + v * zscale),
  frames:[base64 Uint8 per timestep] (depth = v * dscale, 0 = dry),
  roads: [{name, pts:[[x,y],...]}]   (grid-relative km coords)
}
"""
import argparse
import base64
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, vectors  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--production", action="store_true")
    ap.add_argument("--cell", type=float, default=60.0, help="grid cell size (m)")
    ap.add_argument("--every", type=int, default=1, help="use every n-th timestep")
    ap.add_argument("--max-depth", type=float, default=6.0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--max-speed", type=float, default=6.0)
    ap.add_argument("--out", default="webgl", help="output folder name under outputs/<scenario>/")
    a = ap.parse_args()
    site, dam = config.site(), config.dam()
    mode = "production" if a.production else "shakedown"
    out_dir = config.scenario_dir(a.scenario)
    sww_path = out_dir / f"{a.scenario}_{mode}{a.tag}.sww"
    bbox = site["domain"]["bbox_nztm"] if a.production else site["domain"]["shakedown_bbox_nztm"]
    W, S, E, N = bbox
    sww = post.SWW(sww_path)
    # grid
    xs = np.arange(W + a.cell / 2, E, a.cell); ys = np.arange(S + a.cell / 2, N, a.cell)  # south->north
    X, Y = np.meshgrid(xs, ys)
    from matplotlib.tri import LinearTriInterpolator
    interp_e = LinearTriInterpolator(sww.tri, sww.elev)
    Z = np.ma.filled(interp_e(X, Y), np.nan)
    if np.isnan(Z).any():
        from scipy import ndimage
        m = np.isnan(Z); idx = ndimage.distance_transform_edt(m, return_distances=False, return_indices=True); Z = Z[tuple(idx)]
    z0 = float(np.floor(Z.min())); zscale = (Z.max() - z0) / 65000.0
    dem_u16 = np.round((Z - z0) / zscale).astype("<u2")
    st = sww.ds.variables["stage"]; xm = sww.ds.variables["xmomentum"]; ym = sww.ds.variables["ymomentum"]
    dscale = a.max_depth / 255.0; sscale = a.max_speed / 255.0
    frames, speeds, times, q, area = [], [], [], [], []
    hyd = np.genfromtxt(out_dir / "hydrograph.csv", delimiter=",", names=True)
    meta_path = out_dir / f"run_meta_{mode}.json"
    rmeta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    t_off = float(rmeta.get("time_offset_s", 0.0)); pre = float(rmeta.get("pre_breach_s", 0.0))
    for k in range(0, len(sww.time), a.every):
        s = np.ma.filled(LinearTriInterpolator(sww.tri, st[k, :])(X, Y), np.nan)
        d = np.nan_to_num(s - Z); d[d < 0.05] = 0.0
        frames.append(base64.b64encode(np.round(np.clip(d, 0, a.max_depth) / dscale).astype("u1").tobytes()).decode())
        mx_ = np.ma.filled(LinearTriInterpolator(sww.tri, xm[k, :])(X, Y), 0.0); my_ = np.ma.filled(LinearTriInterpolator(sww.tri, ym[k, :])(X, Y), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            v = np.where(d > 0.05, np.hypot(mx_, my_) / np.maximum(d, 1e-6), 0.0)
        speeds.append(base64.b64encode(np.round(np.clip(np.nan_to_num(v), 0, a.max_speed) / sscale).astype("u1").tobytes()).decode())
        t = float(sww.time[k]) - pre; times.append(round(t / 3600, 3))
        q.append(round(float(np.interp(t + t_off, hyd["t_s"], hyd["Q_out_m3s"])) if t >= 0 else 0.0, 1))
        area.append(round(float((d > 0.1).sum() * a.cell * a.cell / 1e6), 2))
    # roads (clip + simplify), footprint
    gpkg = config.DATA_RAW / "osm_domain.gpkg"
    roads_out = []
    if gpkg.exists():
        import geopandas as gpd
        from shapely.geometry import box
        roads = vectors.load(gpkg, "roads")
        roads = roads[roads["highway"].isin(["primary", "secondary", "tertiary", "unclassified", "residential"])]
        clipped = gpd.clip(roads, box(W, S, E, N))
        for _, r in clipped.iterrows():
            geoms = [r.geometry] if r.geometry.geom_type == "LineString" else list(getattr(r.geometry, "geoms", []))
            for g in geoms:
                g = g.simplify(15.0)
                roads_out.append({"name": r["name"] if isinstance(r["name"], str) else "",
                                  "pts": [[round((x - W) / 1000, 3), round((y - S) / 1000, 3)] for x, y in g.coords]})
    # buildings: minimum rotated rectangle per footprint -> centre (km), size (m), angle (rad), height (m)
    blds_out = []
    if gpkg.exists():
        import geopandas as gpd
        from shapely.geometry import box
        blds = gpd.clip(vectors.load(gpkg, "buildings"), box(W, S, E, N))
        dwelling_types = {"house", "residential", "yes", "detached", "farm", "bungalow", "apartments", "semidetached_house", "cabin"}
        for _, r in blds.iterrows():
            g = r.geometry
            if g.is_empty or g.area < 12:
                continue
            try:
                mrr = g.buffer(0).minimum_rotated_rectangle
                bx, by = mrr.exterior.coords.xy
            except Exception:
                continue
            if len(bx) < 4:
                continue
            dx, dy = bx[1] - bx[0], by[1] - by[0]; l1 = (dx * dx + dy * dy) ** 0.5
            l2 = ((bx[2] - bx[1]) ** 2 + (by[2] - by[1]) ** 2) ** 0.5
            ang = float(np.arctan2(dy, dx)) if l1 > 0 else 0.0
            c = g.centroid
            btype = r["building"] if isinstance(r["building"], str) else "yes"
            big = g.area > 400  # sheds / barns / dairy sheds
            h = 4.0 if btype in ("shed", "barn", "farm_auxiliary", "greenhouse") else (6.5 if big else 5.0)
            blds_out.append([round((c.x - W) / 1000, 4), round((c.y - S) / 1000, 4), round(max(l1, 3), 1), round(max(l2, 3), 1),
                             round(ang, 3), h, 1 if (btype in dwelling_types and not big) else 0])
    fp = [[round((x - W) / 1000, 3), round((y - S) / 1000, 3)] for x, y in site["site"]["footprint_nztm"]]
    sc = dam["scenarios"][a.scenario]; bl = sc["breach_location_nztm"]
    bpts = config.breach_points(a.scenario)
    bnames = [b["name"] for b in sc.get("breaches", []) if not b.get("feeds") and b.get("location_nztm")] or [a.scenario]
    meta = {"scenario": a.scenario, "description": sc["description"], "title": sc.get("title"), "seismic": bool(sc.get("seismic")),
            "hydrology": sc.get("hydrology"), "pre_breach_h": pre / 3600,
            "breaches_km": [{"name": n, "km": [round((x - W) / 1000, 3), round((y - S) / 1000, 3)]} for n, (x, y) in zip(bnames, bpts)],
            "mode": mode, "bbox": bbox,
            "nx": len(xs), "ny": len(ys), "cell": a.cell, "z0": z0, "zscale": zscale, "dscale": dscale, "sscale": sscale,
            "times_h": times, "q_m3s": q, "area_km2": area, "footprint_km": fp,
            "breach_km": [round((bl[0] - W) / 1000, 3), round((bl[1] - S) / 1000, 3)],
            "offset_h": round(t_off / 3600, 2), "roads_named": sorted({r["name"] for r in roads_out if r["name"]}),
            "peak_q": max(q), "zmin": float(Z.min()), "zmax": float(Z.max())}
    wdir = out_dir / a.out; wdir.mkdir(exist_ok=True)
    meta["buildings_total"] = len(blds_out); meta["dwellings"] = int(sum(b[6] for b in blds_out))
    js = ("window.FLOOD=" + json.dumps({"meta": meta, "dem": base64.b64encode(dem_u16.tobytes()).decode(),
                                        "frames": frames, "speeds": speeds, "roads": roads_out, "buildings": blds_out}) + ";")
    (wdir / "data.js").write_text(js)
    print(f"[webgl] {len(frames)} frames, grid {meta['nx']}x{meta['ny']} @ {a.cell} m, roads {len(roads_out)}, buildings {len(blds_out)}, "
          f"data.js {len(js)/1e6:.1f} MB -> {wdir/'data.js'}")


if __name__ == "__main__":
    main()
