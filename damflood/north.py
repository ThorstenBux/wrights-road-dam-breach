"""Eyre River flood at the north embankment: helpers for scripts/22-25.

River flood hydrograph, DEM fetch that keeps the LiDAR gap mask, embankment toe sampling, normal-depth rating of a
cross-section, depression filling and single / multiple flow-direction routing of bank overflow over the LiDAR.
Exploratory and self-contained – the main pipeline does not import this module.
Screening model, not a certified assessment.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import numpy as np
from scipy import ndimage


def gamma_hydrograph(peak: float, base: float, t_peak_s: float, shape: float = 3.0, t_start_s: float = 0.0) -> Callable[[float], float]:
    """Single-peaked flood hydrograph Q(t) = base + (peak - base) * (x * exp(1 - x))**shape with x = (t - start) / t_peak:
    `base` before `t_start_s`, exactly `peak` at `t_start_s + t_peak_s`, smooth recession after it."""
    if t_peak_s <= 0 or peak < base:
        raise ValueError("need t_peak_s > 0 and peak >= base")

    def Q(t: float) -> float:
        x = (t - t_start_s) / t_peak_s
        if x <= 0:
            return float(base)
        return float(base + (peak - base) * (x * np.exp(1.0 - x)) ** shape)
    return Q


def hydrograph_volume(Q: Callable[[float], float], t_end_s: float, dt: float = 60.0) -> float:
    t = np.arange(0.0, t_end_s + dt, dt)
    q = np.array([Q(v) for v in t])
    return float(((q[1:] + q[:-1]) / 2 * np.diff(t)).sum())


def fetch_dem_with_gaps(bbox_nztm, res_m: float, out_path: Path, gaps_path: Path, bucket: str, collection: str) -> dict:
    """As terrain.fetch_dem, but the cells without any LiDAR return are written to `gaps_path` (1 = gap) before they
    are filled, so coverage holes in a new area are visible instead of silently interpolated."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.merge import merge
    from . import terrain
    items = terrain.tiles_for_bbox(terrain.stac_items(bucket, collection, bbox_nztm), bbox_nztm)
    if not items:
        raise RuntimeError("No DEM tiles intersect the requested bbox")
    W, S, E, N = bbox_nztm
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")
    srcs = [rasterio.open("/vsicurl/" + it["tiff"]) for it in items]
    try:
        arr, transform = merge(srcs, bounds=(W, S, E, N), res=(res_m, res_m), resampling=Resampling.average, nodata=-9999.0)
    finally:
        for s in srcs:
            s.close()
    arr = arr[0].astype("float32"); gaps = (arr == -9999.0) | ~np.isfinite(arr)
    if gaps.any():
        arr = terrain.fill_nodata(arr, gaps)
    prof = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, crs="EPSG:2193", transform=transform,
                compress="deflate", tiled=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", dtype="float32", nodata=-9999.0, **prof) as dst:
        dst.write(arr, 1); dst.update_tags(SOURCE=f"LINZ {collection} (CC BY 4.0, ECan/LINZ)", VERTICAL_DATUM="NZVD2016")
    with rasterio.open(gaps_path, "w", dtype="uint8", nodata=255, **prof) as dst:
        dst.write(gaps.astype("uint8"), 1)
    return {"tiles": len(items), "shape": list(arr.shape), "gap_cells": int(gaps.sum()), "gap_share": float(gaps.mean())}


def gap_report(gaps: np.ndarray, res_m: float, transform, min_cells: int = 25) -> list[dict]:
    """Connected LiDAR gaps of at least `min_cells` cells: area and bounding box (NZTM), largest first."""
    lab, n = ndimage.label(gaps)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        cells = int((lab[sl] == i).sum())
        if cells < min_cells:
            continue
        r, c = sl
        out.append({"area_km2": cells * res_m ** 2 / 1e6,
                    "bbox_nztm": [transform.c + c.start * res_m, transform.f - r.stop * res_m,
                                  transform.c + c.stop * res_m, transform.f - r.start * res_m]})
    return sorted(out, key=lambda d: -d["area_km2"])


def embankment_samples(p0, p1, spacing: float, offset: float) -> np.ndarray:
    """Points `offset` m to the LEFT of the line p0 -> p1, every `spacing` m (for the north embankment drawn NW -> NE
    the left side is outside the ponds, towards the river)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.hypot(*(p1 - p0))); t = (p1 - p0) / L; n = np.array([-t[1], t[0]])
    s = np.arange(spacing / 2, L, spacing)
    return p0[None, :] + s[:, None] * t[None, :] + offset * n[None, :]


def section_rating(s: np.ndarray, z: np.ndarray, n: float, slope: float, levels: np.ndarray) -> np.ndarray:
    """Normal-depth discharge of a whole cross-section at each water level (Manning, single section, every cell
    below the level wet – i.e. an UPPER bound on what the section carries at that level)."""
    ds = np.gradient(s); Q = np.zeros(len(levels))
    for i, lv in enumerate(levels):
        d = np.maximum(lv - z, 0.0); wetc = d > 0
        A = float((d * ds).sum()); P = float(ds[wetc].sum())
        Q[i] = A * (A / P) ** (2 / 3) * np.sqrt(max(slope, 1e-5)) / n if P > 0 else 0.0
    return Q


def fill_depressions(z: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    """Priority-flood depression filling (Barnes et al. 2014) with a small gradient `eps` per cell on the filled flats,
    so that every cell drains to the grid edge along strictly descending neighbours. 8-connected."""
    import heapq
    nr, nc = z.shape
    out = np.full(z.shape, np.inf); done = np.zeros(z.shape, bool)
    done[0, :] = done[-1, :] = done[:, 0] = done[:, -1] = True
    rs, cs = np.nonzero(done); out[rs, cs] = z[rs, cs]
    heap = [(float(z[r, c]), int(r), int(c)) for r, c in zip(rs, cs)]
    heapq.heapify(heap)
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    while heap:
        h, r, c = heapq.heappop(heap)
        for dr, dc in nb:
            rr, cc = r + dr, c + dc
            if 0 <= rr < nr and 0 <= cc < nc and not done[rr, cc]:
                done[rr, cc] = True
                out[rr, cc] = max(float(z[rr, cc]), h + eps)
                heapq.heappush(heap, (out[rr, cc], rr, cc))
    return out


def spread_downhill(filled: np.ndarray, source: np.ndarray, exponent: float = 1.0) -> np.ndarray:
    """Multiple-flow-direction routing (Quinn et al. 1991) of the unit flows in `source` over a depression-filled grid:
    every cell passes what it receives to ALL lower neighbours in proportion to slope**exponent. Returns the flow through
    each cell. Spreads far more than real shallow flow does (no momentum, no channels), so the share that arrives
    somewhere is an upper-leaning indication of where overflow CAN go, not a discharge."""
    nr, nc = filled.shape
    acc = source.astype(float).copy()
    nb = [(-1, -1, 2 ** 0.5), (-1, 0, 1.0), (-1, 1, 2 ** 0.5), (0, -1, 1.0), (0, 1, 1.0), (1, -1, 2 ** 0.5), (1, 0, 1.0), (1, 1, 2 ** 0.5)]
    order = np.argsort(filled, axis=None)[::-1]
    top = filled[source > 0].max() if (source > 0).any() else -np.inf
    for idx in order:
        r, c = divmod(int(idx), nc)
        if filled[r, c] > top or acc[r, c] == 0.0 or r in (0, nr - 1) or c in (0, nc - 1):
            continue
        w = [(max(filled[r, c] - filled[r + dr, c + dc], 0.0) / d) ** exponent for dr, dc, d in nb]
        tot = sum(w)
        if tot <= 0:
            continue
        for (dr, dc, _), wi in zip(nb, w):
            if wi > 0:
                acc[r + dr, c + dc] += acc[r, c] * wi / tot
    return acc


def trace_downhill(filled: np.ndarray, r: int, c: int, max_steps: int = 20000) -> np.ndarray:
    """Steepest-descent (D8) path over a depression-filled grid from cell (r, c) to the grid edge: array of (row, col)."""
    nr, nc = filled.shape
    nb = [(-1, -1, 2 ** 0.5), (-1, 0, 1.0), (-1, 1, 2 ** 0.5), (0, -1, 1.0), (0, 1, 1.0), (1, -1, 2 ** 0.5), (1, 0, 1.0), (1, 1, 2 ** 0.5)]
    path = [(r, c)]
    for _ in range(max_steps):
        if r in (0, nr - 1) or c in (0, nc - 1):
            break
        best, step = 0.0, None
        for dr, dc, d in nb:
            g = (filled[r, c] - filled[r + dr, c + dc]) / d
            if g > best:
                best, step = g, (dr, dc)
        if step is None:
            break
        r, c = r + step[0], c + step[1]; path.append((r, c))
    return np.array(path)


def upslope_mask(filled: np.ndarray, target: np.ndarray, multiple: bool = False) -> np.ndarray:
    """Cells of a depression-filled grid whose water ends up in `target`. multiple=False: along the single steepest
    descent (D8) – the catchment in the usual sense. multiple=True: along ANY descending neighbour – every cell from which
    some downhill path leads to the target, a generous outer bound for shallow overland flow that spreads."""
    nr, nc = filled.shape
    pad = np.pad(filled, 1, mode="constant", constant_values=np.inf)
    nb = [(-1, -1, 2 ** 0.5), (-1, 0, 1.0), (-1, 1, 2 ** 0.5), (0, -1, 1.0), (0, 1, 1.0), (1, -1, 2 ** 0.5), (1, 0, 1.0), (1, 1, 2 ** 0.5)]
    drop = np.stack([(filled - pad[1 + dr:1 + dr + nr, 1 + dc:1 + dc + nc]) / d for dr, dc, d in nb])   # > 0 = downhill
    steepest = drop.argmax(axis=0)
    mask = target.copy().ravel(); order = np.argsort(filled, axis=None)
    offs = [dr * nc + dc for dr, dc, _ in nb]; dropf = drop.reshape(8, -1); st = steepest.ravel()
    for idx in order:                                   # ascending: every lower neighbour is already decided
        if mask[idx]:
            continue
        if multiple:
            mask[idx] = any(dropf[k, idx] > 0 and mask[idx + offs[k]] for k in range(8))
        else:
            k = st[idx]
            mask[idx] = dropf[k, idx] > 0 and mask[idx + offs[k]]
    return mask.reshape(nr, nc)


def run_tag(domain_tag: str, river_peak: float, rain_mm_h: float = 0.0, hydrograph_tag: str = "", no_breach: bool = False) -> str:
    """File tag of a scripts/24 run, e.g. `_north_q300_rain10_full_nobreach`. The baseline of a run is the same tag with
    `_nobreach` and WITHOUT the breach-hydrograph tag (the baseline does not depend on the breach)."""
    tag = f"_{domain_tag}_q{river_peak:g}".replace(".", "p")
    if rain_mm_h > 0:
        tag += f"_rain{rain_mm_h:g}".replace(".", "p")
    return tag + ("_nobreach" if no_breach else hydrograph_tag)


def river_inlet(line, chainage_m: float, span_m: float = 200.0):
    """Inflow point and downstream unit vector on a river centreline (ordered downstream) `chainage_m` from its start."""
    p = line.interpolate(chainage_m); q = line.interpolate(min(chainage_m + span_m, line.length))
    d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return np.array([p.x, p.y]), d
