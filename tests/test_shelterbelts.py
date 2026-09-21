"""Exploratory shelterbelt layer (damflood.shelterbelts) on a synthetic surface / ground model pair."""
import numpy as np
import pytest

from damflood import shelterbelts
from damflood.terrain import DEM


def _dem(arr, res=2.0):
    from rasterio.transform import from_origin
    d = DEM.__new__(DEM); d.arr = np.asarray(arr, float); d.res = res
    d.transform = from_origin(0, arr.shape[0] * res, res, res)
    return d


def test_canopy_mask_keeps_belts_and_drops_wires_and_low_vegetation():
    ground = np.full((100, 100), 200.0)
    surface = ground.copy()
    surface[40:45, 10:90] += 14.0      # a 10 m wide, 160 m long belt, 14 m tall
    surface[70, :] += 9.0              # a power line: one cell wide
    surface[10:30, 10:30] += 3.0       # a crop / pivot irrigator: too low
    surface[85:87, 85:87] += 12.0      # a single tree: 16 m2, below the patch limit
    m, chm = shelterbelts.canopy_mask(_dem(surface), _dem(ground), min_height=6.0)
    assert m[40:45, 10:90].all() and m.sum() == 5 * 80
    assert chm[42, 50] == pytest.approx(14.0) and chm[70, 50] == 0.0


def test_equivalent_manning_is_n_squared_weighted():
    assert shelterbelts.equivalent_manning(0.0, 0.045, 0.2) == pytest.approx(0.045)
    assert shelterbelts.equivalent_manning(1.0, 0.045, 0.2) == pytest.approx(0.2)
    assert shelterbelts.equivalent_manning(0.25, 0.045, 0.2) == pytest.approx(np.sqrt(0.25 * 0.04 + 0.75 * 0.045 ** 2))


def test_triangle_friction_raises_n_only_near_trees():
    mask = np.zeros((200, 200), bool); mask[98:103, :] = True          # belt along y = 200 m
    dem = _dem(np.zeros((200, 200)))
    c = np.array([[200.0, 200.0], [200.0, 380.0], [200.0, 200.0]]); areas = np.array([3000.0, 3000.0, 50.0])
    n = shelterbelts.triangle_friction(mask, dem, c, areas, 0.045, 0.2)
    assert n[1] == pytest.approx(0.045)
    assert 0.06 < n[0] < 0.1            # 10 m belt across a ~55 m triangle
    assert n[2] == pytest.approx(0.2, abs=0.01)   # small triangle inside the belt


def test_fraction_friction_matches_the_canopy_share_and_reports_stats():
    frac = _dem(np.zeros((100, 100)), res=10.0); frac.arr[:, 50:] = 0.5      # east half: half of every cell under trees
    c = np.array([[100.0, 500.0], [900.0, 500.0]]); areas = np.array([3000.0, 3000.0])
    n, stats = shelterbelts.fraction_friction(frac, c, areas, 0.045, 0.2)
    assert n[0] == pytest.approx(0.045)
    assert n[1] == pytest.approx(shelterbelts.equivalent_manning(0.5, 0.045, 0.2))
    assert stats["triangles_with_trees"] == 1 and stats["tree_n"] == 0.2
