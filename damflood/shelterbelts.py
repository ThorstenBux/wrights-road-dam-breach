"""Tree shelterbelts from LiDAR: canopy height = surface model (DSM) - ground model (DEM), and an equivalent
Manning n per mesh triangle.

Exploratory and self-contained – the main pipeline does not import this module.
Screening model, not a certified assessment.
"""
from __future__ import annotations

import numpy as np
from rasterio.features import rasterize
from scipy import ndimage

from .terrain import DEM


def canopy_mask(dsm: DEM, dem: DEM, min_height: float = 6.0, buildings=None, building_buffer: float = 4.0,
                min_patch_m2: float = 60.0) -> tuple[np.ndarray, np.ndarray]:
    """Cells under tall vegetation. Returns (mask, canopy height).  Tall = DSM - DEM >= `min_height` (the belts
    here are over 10 m; crops, hedges and pivot irrigators stay below ~5 m).  Buildings (buffered) are removed,
    then a 3x3 opening drops wires and single-cell spikes and patches smaller than `min_patch_m2` are dropped."""
    chm = dsm.arr - dem.arr
    m = chm >= min_height
    if buildings is not None and len(buildings):
        shapes = [(g, 1) for g in buildings.geometry.buffer(building_buffer) if not g.is_empty]
        m &= rasterize(shapes, out_shape=m.shape, transform=dem.transform, fill=0, dtype="uint8") == 0
    m = ndimage.binary_opening(m, structure=np.ones((3, 3), bool))
    lab, n = ndimage.label(m, structure=np.ones((3, 3), int))
    if n:
        size = ndimage.sum_labels(m, lab, index=np.arange(1, n + 1)) * dem.res ** 2
        m &= np.r_[False, size >= min_patch_m2][lab]
    return m, np.where(m, chm, 0.0)


def canopy_fraction(mask: np.ndarray, res: float, window_m: float) -> np.ndarray:
    """Share of canopy cells in a `window_m` square around each cell."""
    return ndimage.uniform_filter(mask.astype("float32"), size=max(int(round(window_m / res)), 1), mode="nearest")


def equivalent_manning(fraction, n_open: float, n_belt: float):
    """Friction slope scales with n^2 x length, so a triangle with a share f of its area under trees
    loses the same head as one with n_eff = sqrt(f n_belt^2 + (1 - f) n_open^2)."""
    f = np.clip(np.asarray(fraction, float), 0.0, 1.0)
    return np.sqrt(f * n_belt ** 2 + (1.0 - f) * n_open ** 2)


def fraction_friction(frac: DEM, centroids_abs: np.ndarray, areas: np.ndarray, n_open: float, n_belt: float,
                      windows=((0, 25, 20.0), (25, 50, 40.0), (50, 1e9, 70.0))) -> tuple[np.ndarray, dict]:
    """Equivalent n per triangle from a canopy-FRACTION raster (scripts/15_canopy_fraction.py): the fraction is
    averaged in a window about the size of the triangle (`windows` = (side from, side to, window m)).
    Returns (n, stats)."""
    side = np.sqrt(np.asarray(areas, float))
    n = np.full(len(side), float(n_open))
    for lo, hi, win in windows:
        sel = (side >= lo) & (side < hi)
        if sel.any():
            sm = DEM.__new__(DEM); sm.transform = frac.transform
            sm.arr = ndimage.uniform_filter(frac.arr, size=max(int(round(win / frac.res)), 1), mode="nearest")
            n[sel] = equivalent_manning(sm.sample(centroids_abs[sel, 0], centroids_abs[sel, 1]), n_open, n_belt)
    wt = n > n_open * 1.02
    stats = {"tree_n": float(n_belt), "triangles_with_trees": int(wt.sum()), "share_of_triangles": float(wt.mean()),
             "median_n_where_trees": float(np.median(n[wt])) if wt.any() else None, "max_n": float(n.max())}
    return n, stats


def triangle_friction(mask: np.ndarray, dem: DEM, centroids_abs: np.ndarray, areas: np.ndarray,
                      n_open: float, n_belt: float) -> np.ndarray:
    """Equivalent n per triangle: canopy share in a window matched to the triangle size (three size classes)."""
    n = np.full(len(areas), float(n_open))
    side = np.sqrt(np.asarray(areas, float))
    for lo, hi, win in ((0, 15, 10.0), (15, 40, 28.0), (40, 1e9, 64.0)):
        sel = (side >= lo) & (side < hi)
        if sel.any():
            frac = DEM.__new__(DEM); frac.arr = canopy_fraction(mask, dem.res, win).astype("float64")
            frac.transform = dem.transform
            n[sel] = equivalent_manning(frac.sample(centroids_abs[sel, 0], centroids_abs[sel, 1]), n_open, n_belt)
    return n
