#!/usr/bin/env python
"""EXPLORATORY: animated 3D view of a race / shelterbelt run (scripts/12_run_races.py).

Writes outputs/races/viewer/<run>/{index.html,data.js}. The viewer is a COPY of webgl/index.html patched at
export time with two extra layers – the water races (cyan lines) and the tree shelterbelts (green blocks at
canopy height) – so webgl/index.html and the published docs/ viewers stay untouched.

The races are 3-9 m wide, far below a display cell, so each display cell shows the DEEPEST water inside it
(sampled on a finer grid): the races read as continuous lines, at the price of looking wider than they are.
Screening model, not a certified assessment.
"""
import argparse
import base64
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, vectors  # noqa: E402

ANCHOR = "  const tmpV = new THREE.Vector3();"
EXTRA_JS = r"""
  // ---------- EXPLORATORY layers (injected by scripts/14_export_races_webgl.py): races and tree shelterbelts ----------
  {
    const raceMat = new THREE.LineBasicMaterial({ color: 0x35e0ff });
    const baseLines = rebuildLines;
    rebuildLines = function () {
      baseLines();
      (F.races || []).forEach(r => linesGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(r.pts.map(p => toScene(p[0], p[1], 3.5))), raceMat)));
    };
    rebuildLines();
    (F.races || []).forEach((r, i) => {
      const el = document.createElement('div'); el.className = 'rl'; el.textContent = r.name + ' race'; el.style.color = '#35e0ff'; document.body.appendChild(el);
      const p = r.pts[Math.floor(r.pts.length / 3)]; labels.unshift({ el, xk: p[0], yk: p[1], lift: 12, rank: -10 - i, w: 0 });
    });
    if (F.meta.no_breach) { const k = labels.findIndex(L => L.el.textContent.indexOf('breach') >= 0); if (k >= 0) { labels[k].el.remove(); labels.splice(k, 1); } }
    const T = F.trees || [];
    if (T.length) {
      const tGeo = new THREE.BoxGeometry(1, 1, 1); tGeo.translate(0, 0.5, 0);
      const tMesh = new THREE.InstancedMesh(tGeo, new THREE.MeshLambertMaterial({ color: 0x2f7d3a, transparent: true, opacity: 0.85 }), T.length);
      scene.add(tMesh);
      const tm = new THREE.Matrix4(), tq = new THREE.Quaternion(), tS = new THREE.Vector3(), tP = new THREE.Vector3();
      const placeTrees = function () {
        const c = (F.meta.tree_cell || 10) / 1000;
        T.forEach((t, i) => { tP.set(t[0], zk(sampleElev(t[0], t[1])), H - t[1]); tS.set(c, t[2] / 1000 * fscale(), c); tm.compose(tP, tq, tS); tMesh.setMatrixAt(i, tm); });
        tMesh.instanceMatrix.needsUpdate = true;
      };
      const basePlace = placeBuildings;
      placeBuildings = function () { basePlace(); placeTrees(); };
      placeTrees();
    }
    const note = document.getElementById('desc');
    if (note && F.meta.layers_note) note.textContent += ' ' + F.meta.layers_note;
  }
"""


def b64(a):
    return base64.b64encode(a.tobytes()).decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True, help="run name without the races_ prefix, e.g. dewater_open, dewater_breach_open_trees")
    ap.add_argument("--cell", type=float, default=20.0, help="display cell (m)")
    ap.add_argument("--fine", type=int, default=4, help="sub-samples per display cell side (deepest value is shown)")
    ap.add_argument("--every", type=int, default=2, help="use every n-th output step")
    ap.add_argument("--max-depth", type=float, default=4.0)
    ap.add_argument("--max-speed", type=float, default=6.0)
    ap.add_argument("--bbox", type=float, nargs=4, default=None, metavar=("W", "S", "E", "N"), help="crop (NZTM)")
    ap.add_argument("--no-speed", action="store_true")
    ap.add_argument("--docs", action="store_true", help="write to docs/exploratory/<run>/ (GitHub Pages) instead of outputs/races/viewer/")
    a = ap.parse_args()

    rc, site, dam = config.load_yaml("races.yaml"), config.site(), config.dam()
    out = config.OUTPUTS / "races"
    meta_run = json.loads((out / f"run_meta_races_{a.run}.json").read_text())
    log = json.loads((out / f"run_log_races_{a.run}.json").read_text())
    sww = post.SWW(out / f"races_{a.run}.sww")
    W, S, E, N = a.bbox or rc["domain"]["bbox_nztm"]
    f = a.fine; fc = a.cell / f
    nx, ny = int((E - W) // a.cell), int((N - S) // a.cell)
    xs = W + (np.arange(nx * f) + 0.5) * fc; ys = S + (np.arange(ny * f) + 0.5) * fc          # south -> north
    X, Y = np.meshgrid(xs, ys)
    # barycentric weights once, then every frame is three gathers
    tid = sww.tri.get_trifinder()(X.ravel(), Y.ravel())
    ok = tid >= 0
    v = sww.volumes[np.where(ok, tid, 0)]
    x1, y1, x2, y2, x3, y3 = (sww.x[v[:, 0]], sww.y[v[:, 0]], sww.x[v[:, 1]], sww.y[v[:, 1]], sww.x[v[:, 2]], sww.y[v[:, 2]])
    det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    w1 = ((y2 - y3) * (X.ravel() - x3) + (x3 - x2) * (Y.ravel() - y3)) / det
    w2 = ((y3 - y1) * (X.ravel() - x3) + (x1 - x3) * (Y.ravel() - y3)) / det
    Wt = np.c_[w1, w2, 1 - w1 - w2].astype("float32")
    sample = lambda q: np.where(ok, (np.asarray(q)[v] * Wt).sum(1), np.nan).reshape(X.shape)
    blocks = lambda A: A.reshape(ny, f, nx, f)
    Zf = sample(sww.elev)
    Z = np.nanmean(blocks(Zf), axis=(1, 3))
    if np.isnan(Z).any():
        from scipy import ndimage
        m = np.isnan(Z); idx = ndimage.distance_transform_edt(m, return_distances=False, return_indices=True); Z = Z[tuple(idx)]
    Z = Z.astype("float64")
    z0 = float(np.floor(Z.min())); zscale = float(Z.max() - z0) / 65000.0
    dscale, sscale = a.max_depth / 255.0, a.max_speed / 255.0
    st, xm, ym = (sww.ds.variables[k] for k in ("stage", "xmomentum", "ymomentum"))
    is_breach = meta_run["case"] != "dewater"
    pre = float(meta_run["t_breach_s"]) if is_breach else 0.0
    lt, lq = np.array([r["t_s"] for r in log]), np.array([r["Q_in_m3s"] for r in log])
    frames, speeds, times, q, area = [], [], [], [], []
    for k in range(0, len(sww.time), a.every):
        d = np.nan_to_num(sample(st[k, :]) - Zf); d[d < 0.05] = 0.0
        D = blocks(d).max(axis=(1, 3))
        frames.append(b64(np.round(np.clip(D, 0, a.max_depth) / dscale).astype("u1")))
        if not a.no_speed:
            with np.errstate(divide="ignore", invalid="ignore"):
                sp = np.where(d > 0.05, np.hypot(np.nan_to_num(sample(xm[k, :])), np.nan_to_num(sample(ym[k, :]))) / np.maximum(d, 1e-6), 0.0)
            speeds.append(b64(np.round(np.clip(blocks(sp).max(axis=(1, 3)), 0, a.max_speed) / sscale).astype("u1")))
        t = float(sww.time[k])
        times.append(round((t - pre) / 3600, 3)); q.append(round(float(np.interp(t, lt, lq)), 1))
        area.append(round(float((D > 0.1).sum() * a.cell ** 2 / 1e6), 2))
    km = lambda x, y: [round((x - W) / 1000, 4), round((y - S) / 1000, 4)]

    import geopandas as gpd
    from shapely.geometry import box
    gpkg = config.DATA_RAW / "osm_domain.gpkg"
    roads_out, blds_out = [], []
    roads = vectors.load(gpkg, "roads")
    roads = gpd.clip(roads[roads["highway"].isin(["primary", "secondary", "tertiary", "unclassified", "residential"])], box(W, S, E, N))
    for _, r in roads.iterrows():
        for g in ([r.geometry] if r.geometry.geom_type == "LineString" else list(getattr(r.geometry, "geoms", []))):
            roads_out.append({"name": r["name"] if isinstance(r["name"], str) else "", "pts": [km(x, y) for x, y in g.simplify(10.0).coords]})
    for _, r in gpd.clip(vectors.load(gpkg, "buildings"), box(W, S, E, N)).iterrows():   # as script 07
        g = r.geometry
        if g.is_empty or g.area < 12:
            continue
        bx, by = g.buffer(0).minimum_rotated_rectangle.exterior.coords.xy
        l1 = float(np.hypot(bx[1] - bx[0], by[1] - by[0])); l2 = float(np.hypot(bx[2] - bx[1], by[2] - by[1]))
        btype = r["building"] if isinstance(r["building"], str) else "yes"; big = g.area > 400
        h = 4.0 if btype in ("shed", "barn", "farm_auxiliary", "greenhouse") else (6.5 if big else 5.0)
        dwelling = btype in {"house", "residential", "yes", "detached", "farm", "bungalow", "cabin"} and not big
        blds_out.append(km(g.centroid.x, g.centroid.y) + [round(max(l1, 3), 1), round(max(l2, 3), 1),
                        round(float(np.arctan2(by[1] - by[0], bx[1] - bx[0])), 3), h, int(dwelling)])
    cond = gpd.read_file(out / "races_conditioning.gpkg")
    races_out = [{"name": r.race, "pts": [km(x, y) for x, y in gpd.clip(gpd.GeoSeries([r.geometry], crs=2193), box(W, S, E, N)).iloc[0].simplify(8.0).coords]}
                 for r in cond[cond.kind == "thalweg"].itertuples() if r.geometry.intersects(box(W, S, E, N))]
    trees_out, tree_cell = [], 10.0
    if a.run.endswith("_trees"):
        from damflood import shelterbelts, terrain
        sb = rc["shelterbelts"]; res = rc["domain"]["dem_res_m"]
        lidar = terrain.DEM(config.DATA_DERIVED / f"dem_races_{res:g}m.tif")
        mask, chm = shelterbelts.canopy_mask(terrain.DEM(config.DATA_DERIVED / f"dsm_races_{res:g}m.tif"), lidar,
                                             sb["min_height_m"], vectors.load(gpkg, "buildings"))
        n = int(round(tree_cell / res)); hh, ww = (mask.shape[0] // n) * n, (mask.shape[1] // n) * n
        frac = mask[:hh, :ww].reshape(hh // n, n, ww // n, n).mean(axis=(1, 3))
        top = np.where(mask, chm, np.nan)[:hh, :ww].reshape(hh // n, n, ww // n, n)
        with np.errstate(all="ignore"):
            top = np.nanpercentile(top, 75, axis=(1, 3))
        x0, y1 = lidar.transform.c, lidar.transform.f
        for i, j in zip(*np.nonzero(frac >= 0.3)):
            x, y = x0 + (j + 0.5) * tree_cell, y1 - (i + 0.5) * tree_cell
            if W < x < E and S < y < N:
                trees_out.append(km(x, y) + [round(float(top[i, j]), 1)])

    sc = dam["scenarios"][meta_run["scenario"]]; bl = sc["breach_location_nztm"]
    titles = {"dewater": "Emergency dewatering down the races", "dewater_breach": "East breach after dewatering – races running full",
              "breach_dry": "East breach – dry races"}
    title = titles[meta_run["case"]] + (" – with tree shelterbelts" if trees_out else "")
    rates = ", ".join(f"{k} {v['dewater_q_m3s']:g}" for k, v in rc["races"].items())
    desc = {"dewater": f"EXPLORATORY: dewatering at EAP example rates ({rates} m³/s) for {meta_run['finaltime_s']/3600:g} h, no breach.",
            "dewater_breach": f"EXPLORATORY: {pre/3600:g} h of dewatering ({rates} m³/s), then the east cascade breach (ponds assumed to fail anyway).",
            "breach_dry": "EXPLORATORY: the east cascade breach after dewatering, but routed onto dry races (comparison run)."}[meta_run["case"]]
    desc += f" Culverts and bridges: {meta_run['crossings']}."
    meta = {"scenario": "races", "description": desc, "title": title, "seismic": False, "hydrology": None, "pre_breach_h": pre / 3600,
            "breaches_km": [{"name": "east", "km": km(*bl)}] if is_breach else [], "mode": "exploratory", "bbox": [W, S, E, N],
            "nx": nx, "ny": ny, "cell": a.cell, "z0": z0, "zscale": zscale, "dscale": dscale, "sscale": sscale,
            "times_h": times, "q_m3s": q, "area_km2": area, "footprint_km": [km(x, y) for x, y in site["site"]["footprint_nztm"]],
            "breach_km": km(*bl), "offset_h": 0.0, "roads_named": sorted({r["name"] for r in roads_out if r["name"]}),
            "peak_q": float(lq.max()), "zmin": float(Z.min()), "zmax": float(Z.max()), "tree_cell": tree_cell, "no_breach": not is_breach,
            "buildings_total": len(blds_out), "dwellings": int(sum(b[6] for b in blds_out)),
            "layers_note": "Cyan lines: water races (assumed MR4 / R2 / R3). Each display cell shows the deepest water inside it, so the races look wider than they are."
                           + (" Green blocks: tree shelterbelts at LiDAR canopy height." if trees_out else "")}
    data = {"meta": meta, "dem": b64(np.round((Z - z0) / zscale).astype("<u2")), "frames": frames, "roads": roads_out,
            "buildings": blds_out, "races": races_out, "trees": trees_out}
    if speeds:
        data["speeds"] = speeds
    wdir = (config.ROOT / "docs" / "exploratory" / a.run) if a.docs else (out / "viewer" / a.run)
    wdir.mkdir(parents=True, exist_ok=True)
    js = "window.FLOOD=" + json.dumps(data) + ";"
    (wdir / "data.js").write_text(js)
    html = (config.ROOT / "webgl" / "index.html").read_text()
    if ANCHOR not in html:
        raise SystemExit("webgl/index.html changed: the injection anchor was not found – update ANCHOR in this script")
    html = html.replace("rain + river only", "dewatering only" if meta_run["case"] != "breach_dry" else "before the breach")
    if a.docs:   # one folder deeper than the published scenario viewers
        html = html.replace('href="../', 'href="../../')
    (wdir / "index.html").write_text(html.replace(ANCHOR, EXTRA_JS + "\n" + ANCHOR, 1))
    print(f"[webgl] {a.run}: {len(frames)} frames, grid {nx}x{ny} @ {a.cell:g} m, races {len(races_out)}, tree blocks {len(trees_out)}, "
          f"data.js {len(js)/1e6:.1f} MB -> {wdir}")


if __name__ == "__main__":
    main()
