"""Exploratory wet worst case (damflood.wet): inlet timing with a spin-up, river geometry, transect discharge."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pytest
from matplotlib.tri import Triangulation
from shapely.geometry import LineString

from damflood import wet


def test_delayed_inflow_waits_for_the_spin_up_and_keeps_the_cascade_lag():
    Q = wet.delayed(lambda t: t, pre_s=7200.0, t0_s=100.0)
    assert Q(0.0) == 0.0 and Q(7199.0) == 0.0
    assert Q(7200.0) == pytest.approx(100.0) and Q(7800.0) == pytest.approx(700.0)
    assert wet.delayed(lambda t: 5.0, 7200.0, 0.0, on=False)(9000.0) == 0.0     # the no-breach baseline
    assert wet.delayed(lambda t: t, 0.0, 50.0)(10.0) == pytest.approx(60.0)       # dry day: as scripts/04


def test_river_line_is_clipped_to_the_domain_and_strip_contains_it():
    ww = gpd.GeoDataFrame({"name": ["Eyre River", "Eyre River", "other"]},
                          geometry=[LineString([(-500, 0), (400, 0)]), LineString([(400, 0), (2000, 0)]), LineString([(0, 5), (9, 9)])])
    line = wet.river_line(ww, "Eyre River", [0, -1000, 1000, 1000], margin=100.0)
    assert line.length == pytest.approx(800.0) and line.coords[0][0] == pytest.approx(100.0)   # downstream order kept
    from shapely.geometry import Polygon
    assert Polygon(wet.river_strip(line, 50.0)).buffer(1).contains(line)
    left = wet.offset_line(line, 30.0); right = wet.offset_line(line, -30.0)
    assert left.coords[0][1] == pytest.approx(30.0) and right.coords[0][1] == pytest.approx(-30.0)
    assert left.coords[0][0] < left.coords[-1][0] and right.coords[0][0] < right.coords[-1][0]
    with pytest.raises(ValueError):
        wet.river_line(ww, "Waimakariri River", [0, -1000, 1000, 1000])


def test_transects_measure_discharge_with_the_documented_sign():
    xs, ys = np.meshgrid(np.linspace(0, 100, 11), np.linspace(0, 100, 11)); x, y = xs.ravel(), ys.ravel()
    tri = Triangulation(x, y); n = len(x); T = 3
    var = {"xmomentum": np.full((T, n), 2.0), "ymomentum": np.zeros((T, n))}      # 2 m2/s towards +x (east) everywhere
    sww = SimpleNamespace(tri=tri, x=x, y=y, volumes=tri.triangles, time=np.array([0.0, 100.0, 200.0]), ds=SimpleNamespace(variables=var))
    # flow east: left bank = north. Section from the left to the right bank; bank lines drawn downstream.
    tr = wet.Transects(sww, {"section": [(50, 90), (50, 10)], "left_bank": [(10, 80), (90, 80)]}, spacing=5.0)
    r = tr.integrate(t_from=0.0)
    assert r["Q"]["section"] == pytest.approx([160.0] * 3)          # 2 m2/s x 80 m, downstream = positive
    assert r["Q"]["left_bank"] == pytest.approx([0.0] * 3, abs=1e-9)
    assert r["net"]["section"].sum() == pytest.approx(160.0 * 200.0)
    var["ymomentum"][:] = 1.0                                           # now also 1 m2/s to the north = over the left bank
    assert wet.Transects(sww, {"left_bank": [(10, 80), (90, 80)]}, 5.0).integrate()["out"]["left_bank"].sum() == pytest.approx(80.0 * 200.0)


def test_run_tag_names_every_switch():
    spec = importlib.util.spec_from_file_location("s18", Path(__file__).resolve().parents[1] / "scripts" / "18_run_wet_worstcase.py")
    s18 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s18)
    assert s18.run_tag(True, 1.0, False, 0.2, False, False) == "_wet_trees020"
    assert s18.run_tag(True, 2.0, True, 0.045, True, True) == "_wet_q2_races_treesnone_nobreach"
    assert s18.run_tag(False, 2.0, True, 0.3, False, False) == "_dry_trees030"   # no river on a dry day
