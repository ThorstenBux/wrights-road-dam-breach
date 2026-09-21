"""Exploratory Eyre flood at the north embankment (damflood.north): hydrograph, terrain routing helpers, run tags."""
import numpy as np
import pytest
from shapely.geometry import LineString

from damflood import north


def test_gamma_hydrograph_peaks_where_and_as_high_as_asked():
    Q = north.gamma_hydrograph(peak=300.0, base=5.0, t_peak_s=5 * 3600.0, shape=3.0)
    t = np.arange(0.0, 30 * 3600.0, 60.0); q = np.array([Q(v) for v in t])
    assert Q(0.0) == 5.0 and Q(-10.0) == 5.0
    assert q.max() == pytest.approx(300.0) and t[q.argmax()] == pytest.approx(5 * 3600.0)
    assert np.all(np.diff(q[: q.argmax()]) >= 0) and np.all(np.diff(q[q.argmax():]) <= 0)      # one rise, one recession
    assert q[-1] < 6.0                                                                          # back to base flow
    assert north.hydrograph_volume(lambda _: 10.0, 3600.0) == pytest.approx(36000.0)
    with pytest.raises(ValueError):
        north.gamma_hydrograph(peak=1.0, base=5.0, t_peak_s=3600.0)


def test_embankment_samples_lie_outside_on_the_left_of_the_drawn_line():
    pts = north.embankment_samples([0, 0], [100, 0], spacing=20.0, offset=40.0)
    assert len(pts) == 5 and np.allclose(pts[:, 1], 40.0) and np.allclose(pts[:, 0], [10, 30, 50, 70, 90])


def _tilted_plane_with_pit(n=30):
    y, x = np.mgrid[0:n, 0:n]
    z = 100.0 - 1.0 * x + 0.0 * y          # falls towards +x (east)
    z[10:13, 10:13] -= 5.0                 # a closed pit
    return z.astype(float)


def test_fill_depressions_removes_pits_and_every_trace_reaches_the_edge():
    z = _tilted_plane_with_pit(); f = north.fill_depressions(z)
    assert np.all(f >= z) and f[11, 11] > z[11, 11]                       # the pit is filled ...
    assert f[11, 11] <= z[11, 13] + 0.01                                  # ... to its spill level, not higher
    assert np.allclose(f[20:, :], z[20:, :])                              # ground that already drains is untouched
    p = north.trace_downhill(f, 11, 3)
    assert p[-1][1] == z.shape[1] - 1 and np.all(np.diff(f[p[:, 0], p[:, 1]]) < 0)


def test_upslope_mask_d8_is_the_strip_upslope_and_anypath_is_wider():
    z = _tilted_plane_with_pit(); f = north.fill_depressions(z)
    target = np.zeros(z.shape, bool); target[20, 25] = True
    d8 = north.upslope_mask(f, target); any_ = north.upslope_mask(f, target, multiple=True)
    assert d8[20, 5] and not d8[5, 5] and not d8[20, 27]                  # same row upslope only; nothing downslope
    assert any_[15, 5] and any_.sum() > d8.sum() and np.all(any_[d8])    # diagonal routes count for "any path"
    assert not any_[20, 27]


def test_spread_downhill_conserves_the_overflow_and_spreads_it():
    z = np.tile(100.0 - np.arange(30.0), (30, 1)); src = np.zeros(z.shape); src[15, 2] = 1.0
    acc = north.spread_downhill(z, src)
    assert acc[:, 20].sum() == pytest.approx(1.0, abs=1e-4) and (acc[:, 20] > 0).sum() > 5
    assert acc[15, 20] == acc[:, 20].max()


def test_run_tag_and_baseline_naming():
    assert north.run_tag("north", 300, 0.0, "_full") == "_north_q300_full"
    assert north.run_tag("north", 300, 10.0, "_full", no_breach=True) == "_north_q300_rain10_nobreach"
    assert north.run_tag("north", 0) == "_north_q0"


def test_river_inlet_points_downstream():
    loc, d = north.river_inlet(LineString([(0, 0), (1000, 0), (1000, -1000)]), 500.0)
    assert np.allclose(loc, [500, 0]) and np.allclose(d, [1, 0])


def test_gap_report_lists_large_gaps_only():
    from rasterio.transform import from_origin
    g = np.zeros((50, 50), bool); g[5:15, 10:20] = True; g[40, 40] = True
    rep = north.gap_report(g, 20.0, from_origin(1000.0, 3000.0, 20.0, 20.0))
    assert len(rep) == 1 and rep[0]["area_km2"] == pytest.approx(0.04)
    assert rep[0]["bbox_nztm"] == [1200.0, 2700.0, 1400.0, 2900.0]
