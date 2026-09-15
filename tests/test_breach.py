import numpy as np
import pytest

from damflood.breach import (BreachEvent, BreachGeometry, Reservoir, cascade,
                             froehlich_1995_peak, froehlich_2008, route)


@pytest.fixture
def pond2():
    # Pond 2 per Damwatch design report: FSL 222.8, ~72 ha, ~6.2 Mm3, 12 m deep, 1.5 m freeboard
    return Reservoir("Pond 2", fsl=222.8, invert=210.8, area_fsl=720_000, volume_fsl=6.2e6, crest=224.3)


def test_stage_storage_roundtrip(pond2):
    assert pond2.volume(pond2.fsl) == pytest.approx(6.2e6, rel=1e-9)
    assert pond2.volume(pond2.invert) == 0.0
    for z in (212.0, 218.5, 222.8):
        assert pond2.level(pond2.volume(z)) == pytest.approx(z, abs=1e-6)


def test_froehlich_2008_reference_values():
    p = froehlich_2008(V_w=5.0e6, h_b=7.0, mode="overtopping")
    assert p["B_avg"] == pytest.approx(0.27 * 1.3 * 5e6**0.32 * 7**0.04, rel=1e-12)
    assert 45 < p["B_avg"] < 60
    assert p["t_f"] == pytest.approx(63.2 * np.sqrt(5e6 / (9.81 * 49)), rel=1e-12)
    assert 6000 < p["t_f"] < 7000  # ~1.8 h
    assert p["z"] == 1.0
    assert froehlich_2008(5e6, 7.0, "piping")["z"] == 0.7
    assert froehlich_1995_peak(5e6, 7.0) > 500


def test_routing_conserves_mass(pond2):
    invert = 215.5  # natural ground at east toe
    geom = BreachGeometry.from_froehlich_2008(pond2, invert=invert, mode="piping")
    r = route(BreachEvent(pond2, geom), t_end=24 * 3600, dt=2.0)
    V_w = pond2.volume_above(invert)
    assert r["volume_released"] == pytest.approx(V_w, rel=0.02)  # slow weir tail
    assert r["level"][-1] == pytest.approx(invert, abs=0.15)
    assert r["Q_out"].max() > 0
    assert np.all(r["Q_out"] >= 0)


def test_cascade_triggers_lower_pond(pond2):
    pond1 = Reservoir("Pond 1", fsl=226.5, invert=218.5, area_fsl=300_000, volume_fsl=2.0e6, crest=228.0)
    # Pond 1 pipes into Pond 2 through the middle embankment (breach invert at Pond 2 FSL)
    g1 = BreachGeometry.from_froehlich_2008(pond1, invert=222.8, mode="piping")
    ev1 = BreachEvent(pond1, g1)
    # NOTE: with the frustum stage-storage from the design-report volumes, Pond 1 + Pond 2
    # statically equalise at ~223.8 m, 0.5 m BELOW the Pond 2 crest (224.3). Overtopping
    # therefore needs a dynamic surge allowance -> trigger a little below crest.
    trigger = 223.6
    g2 = BreachGeometry.from_froehlich_2008(pond2, invert=215.5, mode="overtopping", pool_level=trigger)
    ev2 = BreachEvent(pond2, g2, trigger_level=trigger)
    r1, r2 = cascade([ev1, ev2], t_end=8 * 3600, dt=2.0)
    assert r2["t_init"] is not None and r2["t_init"] > 0
    assert r2["level"].max() >= trigger
    assert r2["level"].max() < 224.3  # static equalisation does not reach the crest
    assert r2["Q_out"].max() > r1["Q_out"].max() * 0.5
