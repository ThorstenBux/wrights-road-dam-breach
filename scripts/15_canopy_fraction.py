#!/usr/bin/env python
"""EXPLORATORY: tree-canopy fraction raster for a whole model domain (shelterbelts as roughness).

Canopy = LINZ 1 m DSM - DEM >= min height, worked out in tiles at 2 m and aggregated to the share of each
10 m cell under tall trees -> data/derived/canopy_fraction_<mode>_10m.tif (+ mean canopy height).
Settings: config/races.yaml `shelterbelts`. Nothing in scripts 01-10 reads the result.
Screening model, not a certified assessment.
"""
import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, shelterbelts, terrain, vectors  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    config.add_mode_arg(ap)
    ap.add_argument("--tile-km", type=float, default=8.0)
    ap.add_argument("--work-res", type=float, default=2.0)
    ap.add_argument("--out-res", type=float, default=10.0)
    a = ap.parse_args()
    site, sb = config.site(), config.load_yaml("races.yaml")["shelterbelts"]
    mode = config.mode_from_args(a); ms = config.mode_settings(mode)
    W, S, E, N = ms["bbox"]
    k = int(round(a.out_res / a.work_res))
    nx, ny = int((E - W) // a.out_res), int((N - S) // a.out_res)
    frac = np.zeros((ny, nx), "float32"); height = np.zeros((ny, nx), "float32")
    gpkg = config.DATA_RAW / ("osm_shakedown.gpkg" if mode == "shakedown" else "osm_domain.gpkg")
    blds = vectors.load(gpkg, "buildings") if gpkg.exists() else None
    step = a.tile_km * 1000
    with tempfile.TemporaryDirectory() as tmp:
        for x0 in np.arange(W, E, step):
            for y0 in np.arange(S, N, step):
                tb = [x0, y0, min(x0 + step, E), min(y0 + step, N)]
                dem_p, dsm_p = Path(tmp) / "dem.tif", Path(tmp) / "dsm.tif"
                terrain.fetch_dem(tb, a.work_res, dem_p, site["dem"]["bucket"], site["dem"]["collection"], verbose=False)
                terrain.fetch_dem(tb, a.work_res, dsm_p, site["dem"]["bucket"], sb["dsm_collection"], verbose=False)
                dem, dsm = terrain.DEM(dem_p), terrain.DEM(dsm_p)
                sub = blds.cx[tb[0]:tb[2], tb[1]:tb[3]] if blds is not None else None
                mask, chm = shelterbelts.canopy_mask(dsm, dem, sb["min_height_m"], sub)
                h, w = (mask.shape[0] // k) * k, (mask.shape[1] // k) * k
                f = mask[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))
                hs = chm[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3)) / np.maximum(mask[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3)), 1)
                j0 = int(round((tb[0] - W) / a.out_res)); i0 = int(round((N - tb[3]) / a.out_res))   # rows from the north
                frac[i0:i0 + f.shape[0], j0:j0 + f.shape[1]] = f; height[i0:i0 + f.shape[0], j0:j0 + f.shape[1]] = hs
                print(f"[canopy] tile {tb}: {mask.sum() * a.work_res ** 2 / 1e6:.2f} km2 of canopy", flush=True)
    tr = from_origin(W, N, a.out_res, a.out_res)
    out = config.DATA_DERIVED / f"canopy_fraction_{mode}_{a.out_res:g}m.tif"
    post.write_tif(out, frac, tr); post.write_tif(out.with_name(out.name.replace("fraction", "height")), height, tr)
    tall = height[frac > 0]
    print(f"[canopy] {mode}: {frac.sum() * a.out_res ** 2 / 1e6:.1f} km2 of canopy = {100 * frac.mean():.1f} % of the domain; "
          f"median height {np.median(tall):.1f} m -> {out}")


if __name__ == "__main__":
    main()
