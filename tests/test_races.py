"""Exploratory race conditioning (damflood.races) on a synthetic LiDAR tile."""
import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString

from damflood import races
from damflood.terrain import DEM


@pytest.fixture
def dem(tmp_path):
    """600 x 200 m plain falling 1 % to the east at 2 m cells, with a 6 m wide, 1.5 m deep race along
    y = 100 and a 12 m wide road fill (no channel) across it at x = 300."""
    res, nx, ny = 2.0, 300, 100
    x = (np.arange(nx) + 0.5) * res; y = 200 - (np.arange(ny) + 0.5) * res
    X, Y = np.meshgrid(x, y)
    z = 100.0 - 0.01 * X
    z = np.where((np.abs(Y - 100) <= 3) & (np.abs(X - 300) > 6), z - 1.5, z)
    path = tmp_path / "dem.tif"
    with rasterio.open(path, "w", driver="GTiff", height=ny, width=nx, count=1, dtype="float32", crs="EPSG:2193",
                       transform=from_origin(0, 200, res, res), nodata=-9999.0) as ds:
        ds.write(z.astype("float32"), 1)
    return DEM(path)


def test_follow_chain_joins_ways_downstream():
    ww = gpd.GeoDataFrame({"osm_id": ["1", "2", "3", "9"]}, geometry=[
        LineString([(0, 0), (10, 0)]), LineString([(10, 0), (20, 5)]), LineString([(20, 5), (30, 5)]),
        LineString([(50, 50), (60, 60)])], crs=2193)
    line = races.follow_chain(ww, "1")
    assert line.length == pytest.approx(10 + np.hypot(10, 5) + 10)
    assert races.follow_chain(ww, "3").length == pytest.approx(10)
    with pytest.raises(KeyError):
        races.follow_chain(ww, "404")


def test_clip_keeps_the_piece_from_the_start():
    part = races.clip_to_bbox(LineString([(50, 50), (500, 50)]), [0, 0, 200, 100], margin=30)
    assert part.bounds == pytest.approx((50, 50, 170, 50))


def test_snap_finds_the_channel_and_the_road_crossing(dem):
    osm = LineString([(20, 108), (580, 108)])            # mapped 8 m off the real channel
    th = races.snap_thalweg(dem, osm, "T", station=5.0, search=14.0, hump=0.4)
    assert np.abs(th.xy[5:-5, 1] - 100).max() <= 3.5     # snapped into the 6 m wide bed
    assert np.median(th.ground - th.z_raw) == pytest.approx(1.5, abs=0.15)
    assert len(th.crossings) == 1
    c = th.crossings[0]
    assert c["x"] == pytest.approx(300, abs=8) and c["hump_m"] == pytest.approx(1.5, abs=0.2)
    assert np.all(np.diff(th.z_open) <= 1e-9)            # the opened bed only falls downstream
    assert np.all(np.diff(th.s) == pytest.approx(5.0, abs=0.3))


def test_burn_bed_opens_or_keeps_the_crossing(dem):
    th = races.snap_thalweg(dem, LineString([(20, 100), (580, 100)]), "T")
    row, col = 50, 150                                   # the cell on the race line under the road fill
    assert dem.arr[row, col] == pytest.approx(97.0, abs=0.05)
    opened = races.burn_bed(dem, dem.arr, th, bed_width=4.0, crossings_open=True)
    kept = races.burn_bed(dem, dem.arr, th, bed_width=4.0, crossings_open=False)
    assert opened[row, col] == pytest.approx(95.5, abs=0.1)     # cut down to the bed
    assert kept[row, col] == pytest.approx(97.0, abs=0.1)       # culvert blocked: the fill stays
    assert np.all(opened <= dem.arr + 1e-9) and np.all(kept <= dem.arr + 1e-9)   # never raises the ground
    assert opened[10, 150] == dem.arr[10, 150]                  # away from the race nothing changes


def test_bankfull_capacity_order_of_magnitude(dem):
    th = races.snap_thalweg(dem, LineString([(20, 100), (580, 100)]), "T")
    cap = races.bankfull_capacity(th, bed_width=6.0, n=0.03)
    assert cap["mean_slope"] == pytest.approx(0.01, rel=0.2)
    assert 20 < cap["bankfull_Q_m3s"] < 80
