#!/usr/bin/env python
"""Render PNG maps for every hazard raster of a scenario (max speed, depth x velocity, arrival time,
hazard class, time of peak) with road names, so results survive without the GeoTIFFs."""
import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, vectors  # noqa: E402

LAYERS = {
    "max_speed": ("max flow speed (m/s)", "YlOrRd", None),
    "max_dv": ("max depth × velocity (m²/s)", "PuRd", None),
    "arrival_h": ("arrival time of water > 0.1 m (h after breach opens)", "viridis", None),
    "t_peak_h": ("time of peak depth (h after breach opens)", "cividis", None),
    "hazard": ("flood hazard class H1–H6 (ARR 2019 / NZSOLD Table 2.5)", "RdYlGn_r", (1, 6)),
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--scenario", default="east"); config.add_mode_arg(ap)
    a = ap.parse_args(); mode = config.mode_from_args(a)
    site, dam = config.site(), config.dam(); out = config.scenario_dir(a.scenario)
    roads = vectors.load(config.DATA_RAW / "osm_domain.gpkg", "roads")
    fp = [list(map(float, p)) for p in site["site"]["footprint_nztm"]]
    bls = config.breach_points(a.scenario)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from shapely.geometry import box
    import geopandas as gpd
    for key, (label, cmap, lim) in LAYERS.items():
        tif = out / f"{key}_{mode}.tif"
        if not tif.exists():
            print("missing", tif); continue
        with rasterio.open(tif) as ds:
            arr = ds.read(1); arr = np.where(arr == ds.nodata, np.nan, arr); b = ds.bounds
        fig, ax = plt.subplots(figsize=(12, 8)); ax.set_xlim(b.left, b.right); ax.set_ylim(b.bottom, b.top)
        vmin, vmax = lim if lim else (0, float(np.nanpercentile(arr, 99)) if np.isfinite(arr).any() else 1)
        im = ax.imshow(np.ma.masked_invalid(arr), extent=(b.left, b.right, b.bottom, b.top), cmap=cmap, vmin=vmin, vmax=vmax, zorder=3)
        rc = gpd.clip(roads, box(b.left, b.bottom, b.right, b.top))
        major = rc[rc["highway"].isin(["primary", "secondary", "tertiary", "unclassified", "residential"])]
        rc[~rc.index.isin(major.index)].plot(ax=ax, color="0.75", linewidth=0.3, zorder=4); major.plot(ax=ax, color="0.35", linewidth=0.6, zorder=5)
        post._road_labels(ax, rc, b, dam["consequence"]["roads_of_interest"])
        xs, ys = zip(*(fp + [fp[0]])); ax.plot(xs, ys, "-", color="#e8542a", lw=1.4, zorder=7, label="pond footprint")
        for i, bl in enumerate(bls): ax.plot(bl[0], bl[1], marker="v", color="#e8542a", ms=7, zorder=8, label="breach" if i == 0 else None)
        ax.set_title(f"Wrights Road ponds – {a.scenario} breach ({mode}): {label}"); ax.set_xlabel("NZTM E (m)"); ax.set_ylabel("NZTM N (m)")
        ax.set_aspect("equal"); ax.ticklabel_format(style="plain", useOffset=False); ax.tick_params(labelsize=7); ax.legend(loc="lower right", fontsize=7)
        cb = fig.colorbar(im, ax=ax, label=label, shrink=0.8)
        if key == "hazard": cb.set_ticks([1, 2, 3, 4, 5, 6]); cb.set_ticklabels(["H1", "H2", "H3", "H4", "H5", "H6"])
        fig.tight_layout(); png = out / f"{key}_{mode}.png"; fig.savefig(png, dpi=170); plt.close(fig); print("wrote", png.name)


if __name__ == "__main__":
    main()
