"""Terrain preparation: LiDAR DEM from LINZ open data (AWS `nz-elevation`
bucket, no API key needed), nodata filling, and burning the proposed pond
embankments into the pre-construction ground surface.

The LINZ elevation data are Cloud-Optimised GeoTIFFs (EPSG:2193, NZVD2016,
1 m) indexed by STAC collections, e.g.
https://nz-elevation.s3.ap-southeast-2.amazonaws.com/canterbury/canterbury_2020-2023/dem_1m/2193/collection.json
Licence: CC BY 4.0, (c) Environment Canterbury Regional Council / LINZ.
"""
from __future__ import annotations

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.transform import from_origin
from scipy import ndimage

from . import config

_TO_LL = Transformer.from_crs(2193, 4326, always_xy=True)


def _get_json(url: str, cache_dir: Path, retries: int = 5) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / url.rsplit("/", 1)[-1]
    if cached.exists():
        return json.loads(cached.read_text())
    import time
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                txt = r.read().decode()
            cached.write_text(txt)
            return json.loads(txt)
        except Exception as exc:  # connection resets are common when many tiles are requested
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


# LINZ Topo50 sheet grid in NZTM: sheets are 24 km (E) x 36 km (N); the 1:10,000 tiles used for
# LiDAR are a 5 x 5 subdivision (4.8 km x 7.2 km) named <SHEET>_10000_<row><col>, rows counted from
# the sheet's northern edge.  Anchor derived from tile BW22_10000_0504 (E 1530400-1535200, N 5190000-5197200).
_SHEET_E0, _SHEET_N_TOP, _SHEET_COL0, _SHEET_ROW0 = 1516000.0, 5226000.0, 22, 48  # 48 == "BW"


def _row_letters(idx: int) -> str:
    return chr(ord("A") + idx // 26) + chr(ord("A") + idx % 26)


def topo50_tile(x: float, y: float) -> str:
    """Name of the 1:10,000 LiDAR tile containing NZTM point (x, y), e.g. 'BW22_10000_0504'."""
    col_sheet = _SHEET_COL0 + int(np.floor((x - _SHEET_E0) / 24000.0))
    row_sheet = _SHEET_ROW0 + int(np.floor((_SHEET_N_TOP - y) / 36000.0))
    sx = x - (_SHEET_E0 + (col_sheet - _SHEET_COL0) * 24000.0)
    sy = (_SHEET_N_TOP - (row_sheet - _SHEET_ROW0) * 36000.0) - y
    c = int(sx // 4800.0) + 1
    r = int(sy // 7200.0) + 1
    return f"{_row_letters(row_sheet)}{col_sheet:02d}_10000_{r:02d}{c:02d}"


def tile_names_for_bbox(bbox_nztm) -> set[str]:
    W, S, E, N = bbox_nztm
    names = set()
    for x in np.arange(W, E + 4800.0, 4800.0):
        for y in np.arange(S, N + 7200.0, 7200.0):
            names.add(topo50_tile(min(x, E), min(y, N)))
    return names


def stac_items(bucket: str, collection: str, bbox_nztm=None) -> list[dict]:
    """Return [{id, bbox(lonlat), tiff(url)}] for items in a LINZ STAC collection.
    If bbox_nztm is given, only item files whose Topo50 tile name can intersect the
    bbox are fetched (avoids downloading >1000 index files for the big collections)."""
    base = f"{bucket}/{collection}/"
    cache = config.DATA_RAW / "stac" / collection.replace("/", "_")
    coll = _get_json(base + "collection.json", cache)
    hrefs = [l["href"].lstrip("./") for l in coll["links"] if l.get("rel") == "item"]
    if bbox_nztm is not None:
        want = tile_names_for_bbox(bbox_nztm)
        hrefs = [h for h in hrefs if h.rsplit("/", 1)[-1].replace(".json", "") in want]

    def one(h):
        it = _get_json(base + h, cache)
        asset = next(iter(it["assets"].values()))
        return {"id": it["id"], "bbox": it["bbox"], "tiff": base + asset["href"].lstrip("./")}

    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(one, hrefs))


def tiles_for_bbox(items: list[dict], bbox_nztm) -> list[dict]:
    W, S, E, N = bbox_nztm
    xs, ys = zip(*[(W, S), (E, S), (E, N), (W, N)])
    lons, lats = _TO_LL.transform(xs, ys)
    w, s, e, n = min(lons), min(lats), max(lons), max(lats)
    return [it for it in items if it["bbox"][2] > w and it["bbox"][0] < e
            and it["bbox"][3] > s and it["bbox"][1] < n]


def fetch_dem(bbox_nztm, res_m: float, out_path: Path, bucket: str, collection: str,
              verbose: bool = True) -> Path:
    """Mosaic the LINZ 1 m DEM tiles intersecting `bbox_nztm` at `res_m` into a
    single GeoTIFF (EPSG:2193).  Reads remotely via GDAL /vsicurl, using the
    COG overviews so only the needed resolution is transferred."""
    items = tiles_for_bbox(stac_items(bucket, collection, bbox_nztm), bbox_nztm)
    if not items:
        raise RuntimeError("No DEM tiles intersect the requested bbox")
    if verbose:
        print(f"[dem] {len(items)} tiles intersect bbox {bbox_nztm}: {[i['id'] for i in items]}")
    W, S, E, N = bbox_nztm
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")
    srcs = [rasterio.open("/vsicurl/" + it["tiff"]) for it in items]
    try:
        arr, transform = merge(srcs, bounds=(W, S, E, N), res=(res_m, res_m),
                               resampling=Resampling.average, nodata=-9999.0)
        profile = srcs[0].profile.copy()
    finally:
        for s in srcs:
            s.close()
    arr = arr[0].astype("float32")
    nodata = -9999.0
    mask = (arr == nodata) | ~np.isfinite(arr)
    if verbose:
        print(f"[dem] grid {arr.shape[1]} x {arr.shape[0]} @ {res_m} m; nodata cells: {int(mask.sum())}")
    if mask.any():
        arr = fill_nodata(arr, mask)
    profile.update(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                   dtype="float32", transform=transform, nodata=nodata, compress="deflate",
                   tiled=True, crs="EPSG:2193")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(SOURCE=f"LINZ {collection} (CC BY 4.0, ECan/LINZ)", VERTICAL_DATUM="NZVD2016")
    if verbose:
        print(f"[dem] wrote {out_path}  range {np.nanmin(arr):.1f}..{np.nanmax(arr):.1f} m")
    return out_path


def fill_nodata(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Nearest-neighbour fill of masked cells."""
    idx = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
    return arr[tuple(idx)]


class DEM:
    """In-memory DEM with bilinear sampling in map coordinates."""

    def __init__(self, path: Path):
        with rasterio.open(path) as ds:
            self.arr = ds.read(1).astype("float64")
            self.transform = ds.transform
            self.nodata = ds.nodata
            self.bounds = ds.bounds
            self.res = ds.res[0]
            self.crs = ds.crs
        if self.nodata is not None:
            m = self.arr == self.nodata
            if m.any():
                self.arr = fill_nodata(self.arr, m)

    def sample(self, x, y, order: int = 1):
        scalar = np.isscalar(x)
        x = np.atleast_1d(np.asarray(x, dtype=float)); y = np.atleast_1d(np.asarray(y, dtype=float))
        col = (x - self.transform.c) / self.transform.a - 0.5
        row = (y - self.transform.f) / self.transform.e - 0.5
        out = ndimage.map_coordinates(self.arr, [row, col], order=order, mode="nearest")
        return float(out[0]) if scalar else out

    def write(self, path: Path, arr=None) -> Path:
        arr = self.arr if arr is None else arr
        with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                           count=1, dtype="float32", crs=self.crs, transform=self.transform,
                           nodata=-9999.0, compress="deflate", tiled=True) as dst:
            dst.write(arr.astype("float32"), 1)
        return path


def burn_solid_block(dem: DEM, polygon_xy, level: float) -> np.ndarray:
    """Return a copy of the DEM with every cell inside `polygon_xy` raised to
    `level` (never lowered).  Used to represent the full storage ponds as an
    impermeable block at crest level so the routed flood cannot flow back into
    the pond footprint.  For a breach-in-domain model, use the ring version."""
    from shapely.geometry import Polygon
    shape = [(Polygon(polygon_xy), 1)]
    m = rasterize(shape, out_shape=dem.arr.shape, transform=dem.transform, fill=0, dtype="uint8")
    out = dem.arr.copy()
    out[m == 1] = np.maximum(out[m == 1], level)
    return out


def burn_embankment_ring(dem: DEM, polygon_xy, crest_level: float, crest_width: float,
                         ext_slope_h_per_v: float, invert_level: float) -> np.ndarray:
    """Represent the pond as an embankment ring (crest at `crest_level`, outer
    batter at `ext_slope_h_per_v`) around an excavated invert.  Use for models
    that resolve the reservoir explicitly."""
    from shapely.geometry import Polygon
    poly = Polygon(polygon_xy)
    out = dem.arr.copy()
    rows, cols = np.indices(out.shape)
    xs = dem.transform.c + (cols + 0.5) * dem.transform.a
    ys = dem.transform.f + (rows + 0.5) * dem.transform.e
    from shapely import vectorized  # shapely>=2
    inside = vectorized.contains(poly, xs, ys)
    ring = poly.exterior
    # signed distance outside the crest line
    import shapely
    d = shapely.distance(ring, shapely.points(xs.ravel(), ys.ravel())).reshape(out.shape)
    crest = d <= crest_width / 2.0
    batter = (~inside) & (d > crest_width / 2.0)
    z_batter = crest_level - (d - crest_width / 2.0) / ext_slope_h_per_v
    out[crest] = np.maximum(out[crest], crest_level)
    out[batter] = np.maximum(out[batter], z_batter[batter])
    out[inside & ~crest] = invert_level
    return out
