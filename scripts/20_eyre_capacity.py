#!/usr/bin/env python
"""EXPLORATORY: bank-full capacity of the Eyre River from LiDAR cross-sections – where would a river already in flood spill first?

Cross-sections of the 2 m LiDAR DEM every `section_spacing_m` along the OSM centreline inside the full domain. At each:
thalweg, the confining crest on each side (highest ground between the thalweg and the end of the section), bank-full
level = the lower crest, and the Manning capacity of the section below it (slope from the thalweg over +-1 km).
No 2D model involved – this is the check on what the 20 m mesh of scripts/18 can and cannot resolve.
Writes outputs/wet/eyre_capacity.{csv,png,json}. Settings: config/wet.yaml `eyre`.
Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, terrain, vectors, wet  # noqa: E402


def section_capacity(s, z, n, slope, search):
    """Bank-full level, area, wetted perimeter and Manning capacity of one cross-section (s across, z ground).
    The thalweg is looked for within `search` m of the mapped centreline (the middle of the section)."""
    mid = np.abs(s - s.mean()) <= search
    i0 = int(np.argmin(np.where(mid, z, np.inf))); zl, zr = float(z[:i0 + 1].max()), float(z[i0:].max())
    level = min(zl, zr)
    # the wetted part connected to the thalweg: walk out from it until the ground reaches the bank-full level
    a = i0
    while a > 0 and z[a - 1] < level:
        a -= 1
    b = i0
    while b < len(z) - 1 and z[b + 1] < level:
        b += 1
    d = np.maximum(level - z[a:b + 1], 0.0); ds = np.gradient(s[a:b + 1]) if b > a else np.array([0.0])
    area = float((d * ds).sum()); wp = float(np.hypot(np.diff(s[a:b + 1]), np.diff(z[a:b + 1])).sum()) if b > a else 0.0
    R = area / wp if wp > 0 else 0.0
    Q = area * R ** (2 / 3) * np.sqrt(max(slope, 1e-5)) / n if area > 0 else 0.0
    return {"thalweg_mRL": float(z[i0]), "crest_left_mRL": zl, "crest_right_mRL": zr, "bankfull_mRL": level,
            "limiting_bank": "left" if zl <= zr else "right", "bankfull_depth_m": level - float(z[i0]),
            "top_width_m": float(s[b] - s[a]), "area_m2": area, "capacity_m3s": float(Q)}


def stage_for(s, z, n, slope, Q, z0):
    """Water level (above the thalweg z0) that carries Q in the section if it were walled at its ends (normal depth)."""
    ds = np.gradient(s)
    for h in np.arange(0.05, 8.0, 0.05):
        d = np.maximum(z0 + h - z, 0.0); wetc = d > 0
        area = float((d * ds).sum()); wp = float(ds[wetc].sum())
        if wp > 0 and area * (area / wp) ** (2 / 3) * np.sqrt(max(slope, 1e-5)) / n >= Q:
            return float(h)
    return float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flows", type=float, nargs="+", default=[150.0, 300.0])
    ap.add_argument("--chunk-km", type=float, default=4.0)
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    site, cfg = config.site(), config.load_yaml("wet.yaml")["eyre"]
    bbox = config.mode_settings("extended")["bbox"]
    gpkg = config.DATA_RAW / "osm_domain.gpkg"
    line = wet.river_line(vectors.load(gpkg, "waterways"), cfg["name"], bbox, margin=cfg["section_half_width_m"] + 50)
    smooth = line.simplify(60.0)   # section direction from the smoothed line, position from the mapped one
    sp, hw, res, n = cfg["section_spacing_m"], cfg["section_half_width_m"], cfg["capacity_dem_res_m"], cfg["manning_n"]
    stations = np.arange(sp / 2, line.length, sp)
    cache = config.DATA_DERIVED / "eyre_dem"; cache.mkdir(parents=True, exist_ok=True)
    rows = []
    per_chunk = max(int(round(a.chunk_km * 1000 / sp)), 1)
    for c0 in range(0, len(stations), per_chunk):
        st = stations[c0:c0 + per_chunk]; pts = [line.interpolate(d) for d in st]
        bb = [min(p.x for p in pts) - hw - 60, min(p.y for p in pts) - hw - 60, max(p.x for p in pts) + hw + 60, max(p.y for p in pts) + hw + 60]
        bb = [float(np.floor(v / res) * res) for v in bb]
        p = cache / f"eyre_{c0:03d}_{res:g}m.tif"
        if not p.exists():
            terrain.fetch_dem(bb, res, p, site["dem"]["bucket"], site["dem"]["collection"], verbose=False)
        dem = terrain.DEM(p); print(f"[eyre] chunk {c0 // per_chunk}: {len(st)} sections", flush=True)
        for d, pt in zip(st, pts):
            q = smooth.project(pt); p0, p1 = smooth.interpolate(max(q - 40, 0)), smooth.interpolate(min(q + 40, smooth.length))
            tx, ty = p1.x - p0.x, p1.y - p0.y; L = np.hypot(tx, ty); lx, ly = -ty / L, tx / L      # unit vector to the LEFT bank
            s = np.arange(-hw, hw + res, res)                                                  # s < 0 = right bank, s > 0 = left
            z = dem.sample(pt.x + s * lx, pt.y + s * ly)
            rows.append({"chainage_m": float(d), "E": pt.x, "N": pt.y, "_s": s - s[0], "_z": z[::-1]})   # stored left -> right
    th = np.array([r["_z"].min() for r in rows]); ch = np.array([r["chainage_m"] for r in rows])
    for i, r in enumerate(rows):
        near = np.abs(ch - ch[i]) <= 1000
        slope = max(-np.polyfit(ch[near], th[near], 1)[0], 1e-4) if near.sum() > 2 else 1e-3
        s, z = r.pop("_s"), r.pop("_z")
        r.update(section_capacity(s, z, n, slope, cfg["thalweg_search_m"])); r["slope"] = float(slope)
        for Q in a.flows:
            h = stage_for(s, z, n, slope, Q, r["thalweg_mRL"])
            r[f"stage_{Q:g}_m"] = h; r[f"freeboard_{Q:g}_m"] = r["bankfull_depth_m"] - h
    df = pd.DataFrame(rows)
    out = config.OUTPUTS / "wet"; out.mkdir(parents=True, exist_ok=True)
    df.round(3).to_csv(out / "eyre_capacity.csv", index=False)
    summ = {"note": "exploratory screening – not a certified assessment. Capacity of the section confined by the highest ground within "
                    f"{hw} m each side; LiDAR bed (check for water on the survey day); Manning n {n}.",
            "sections": int(len(df)), "length_km": float(line.length / 1000), "median_slope": float(df["slope"].median()),
            "capacity_m3s_percentiles_5_25_50_75": [float(v) for v in np.percentile(df["capacity_m3s"], [5, 25, 50, 75])],
            "limiting_bank_share_left": float((df["limiting_bank"] == "left").mean())}
    for Q in a.flows:
        short = df[df["capacity_m3s"] < Q]
        summ[f"sections_below_{Q:g}_m3s"] = int(len(short)); summ[f"share_below_{Q:g}_m3s"] = float(len(short) / len(df))
        summ[f"chainage_km_below_{Q:g}_m3s"] = [round(float(v) / 1000, 2) for v in short["chainage_m"]]
    (out / "eyre_capacity.json").write_text(json.dumps(summ, indent=2))

    roads = vectors.load(gpkg, "roads"); cross = {}
    for nm in config.dam()["consequence"]["roads_of_interest"]:
        sub = roads[roads["name"].fillna("").str.lower() == nm.lower()]
        if not sub.empty and sub.geometry.intersects(line).any():
            x = sub.geometry.intersection(line); x = x[~x.is_empty].iloc[0]
            cross[nm] = line.project(x.centroid) / 1000
    fig, axs = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    ax = axs[0]; km = df["chainage_m"] / 1000
    col = np.where(df["limiting_bank"] == "left", "#2b6cb0", "#c05621")
    ax.bar(km, df["capacity_m3s"], width=sp / 1000 * 0.9, color=col)
    for Q, ls in zip(a.flows, ("--", ":")):
        ax.axhline(Q, color="k", ls=ls, lw=1, label=f"{Q:g} m³/s")
    ax.set_yscale("log"); ax.set_ylabel("bank-full capacity (m³/s)"); ax.legend(fontsize=8, loc="upper right")
    ax.set_title("Eyre River inside the model domain: bank-full capacity from 2 m LiDAR sections "
                 "(blue = left/north bank is the lower one, orange = right/south) – exploratory screening, not a certified assessment", fontsize=9)
    ax2 = axs[1]
    ax2.plot(km, df["bankfull_depth_m"], color="0.3", label="bank-full depth (m)")
    for Q, c in zip(a.flows, ("#2f855a", "#9b2c2c")):
        ax2.plot(km, df[f"stage_{Q:g}_m"], color=c, lw=1, label=f"normal depth at {Q:g} m³/s")
    ax2.set_ylabel("m above thalweg"); ax2.set_xlabel("distance along the Eyre from the north edge of the domain (km)"); ax2.legend(fontsize=8)
    for nm, k in cross.items():
        for x_ in axs:
            x_.axvline(k, color="0.6", lw=0.6)
        ax.text(k, ax.get_ylim()[1], nm.replace(" Road", " Rd"), rotation=90, va="top", ha="right", fontsize=7)
    fig.tight_layout(); fig.savefig(out / "eyre_capacity.png", dpi=130)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
