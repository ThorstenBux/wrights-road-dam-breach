"""Exploratory dewatering sensitivity (damflood.dewater) – kept apart from the main pipeline tests."""
import pytest

from damflood import config, dewater
from damflood.breach import BreachEvent, BreachGeometry, cascade

DT, T_END, INVERT = 5.0, 8 * 3600.0, 210.8


@pytest.fixture(scope="module")
def cfg():
    return config.dam()


def test_drawdown_matches_eap_table_f1(cfg):
    # EAP Table F.1: 4 m3/s from Pond 1 is ~9.3 h per metre, 15 m3/s from Pond 2 ~12.2 h per metre
    # (the EAP uses average areas, so only a loose match is expected near FSL)
    l1, v1 = dewater.drawdown(dewater.reservoir(cfg, "pond1"), 4.0, 9.3)
    l2, _ = dewater.drawdown(dewater.reservoir(cfg, "pond2"), 15.0, 12.2)
    assert v1 == pytest.approx(4.0 * 9.3 * 3600)
    assert 0.3 < 226.5 - l1 < 1.2
    assert 0.6 < 222.8 - l2 < 1.2


def test_drawdown_limits(cfg):
    p1 = dewater.reservoir(cfg, "pond1")
    assert dewater.drawdown(p1, 5.0, 0.0) == (pytest.approx(p1.fsl), 0.0)
    lvl, removed = dewater.drawdown(p1, 1e6, 100.0)
    assert lvl == pytest.approx(p1.invert) and removed == pytest.approx(p1.volume_fsl)


def test_zero_hours_reproduces_the_pipeline_cascade(cfg):
    """With no dewatering the case must be identical to what scripts/03 routes for east."""
    sc, bd = config.scenario("east"), cfg["breach_defaults"]
    trigger = float(cfg["cascade"]["pond2_trigger_mRL"])
    p1, p2 = dewater.reservoir(cfg, "pond1"), dewater.reservoir(cfg, "pond2")
    kw = {"weir_coeff_rect": bd["weir_coeff_rect"], "weir_coeff_tri": bd["weir_coeff_tri"]}
    g1 = BreachGeometry.from_froehlich_2008(p1, invert=cfg["cascade"]["dividing_breach_invert_mRL"],
                                            mode=cfg["cascade"]["dividing_breach_mode"], progression=bd["progression"])
    g2 = BreachGeometry.from_froehlich_2008(p2, invert=INVERT, mode=sc["mode"], pool_level=trigger,
                                            progression=bd["progression"])
    ref = cascade([BreachEvent(p1, g1, **kw), BreachEvent(p2, g2, trigger_level=trigger, **kw)], T_END, DT)[-1]
    r = dewater.cascade_case(cfg, sc, INVERT, 5.0, 15.0, 0.0, t_end=T_END, dt=DT)
    assert r["cascade"] and r["volume_dewatered_m3"] == 0.0
    assert r["peak_Q_m3s"] == pytest.approx(float(ref["Q_out"].max()), rel=1e-12)
    assert r["volume_released_m3"] == pytest.approx(ref["volume_released"], rel=1e-12)


def test_long_dewatering_prevents_the_cascade(cfg):
    sc = config.scenario("east")
    r = dewater.cascade_case(cfg, sc, INVERT, 5.0, 15.0, 12.0, t_end=T_END, dt=DT)
    assert not r["cascade"] and r["peak_Q_m3s"] == 0.0
    assert r["pond2_peak_level_unbreached_mRL"] < r["trigger_mRL"]


def test_equalised_level_conserves_volume_and_is_below_the_routed_peak(cfg):
    p1, p2 = dewater.reservoir(cfg, "pond1"), dewater.reservoir(cfg, "pond2")
    z = dewater.equalised_level(p1, p2, p1.fsl, p2.fsl, 222.8)
    assert float(p1.volume(z) + p2.volume(z)) == pytest.approx(p1.volume_fsl + p2.volume_fsl, rel=1e-9)
    assert z == pytest.approx(223.8, abs=0.05)          # the value noted in config/dam.yaml
    r = dewater.cascade_case(cfg, config.scenario("east"), INVERT, 0.0, 0.0, 0.0, t_end=T_END, dt=DT, full=False)
    assert z < r["pond2_peak_level_unbreached_mRL"]
    assert dewater.equalised_level(p1, p2, 222.0, 221.0, 222.8) == 221.0   # Pond 1 below the sill: no transfer


def test_single_pond_peak_falls_with_dewatering(cfg):
    sc = config.scenario("west")
    q = [dewater.single_case(cfg, sc, 222.0, 5.0, h, t_end=T_END, dt=DT)["peak_Q_m3s"] for h in (0, 6, 24)]
    assert q[0] > q[1] > q[2] > 0


def test_threshold_hours_interpolates():
    assert dewater.threshold_hours([0, 4, 8], [224.0, 223.7, 223.5], 223.6) == pytest.approx(6.0)
    assert dewater.threshold_hours([0, 4], [223.5, 223.4], 223.6) == 0.0
    assert dewater.threshold_hours([0, 4], [224.0, 223.9], 223.6) is None


def test_assumed_breach_still_fails_at_a_lower_level(cfg):
    """Pond 2 assumed to fail anyway: the breach initiates `margin` below the unbreached peak level."""
    sc = config.scenario("east")
    base = dewater.cascade_case(cfg, sc, INVERT, 5.0, 15.0, 0.0, t_end=T_END, dt=DT)
    margin = base["pond2_peak_level_unbreached_mRL"] - base["trigger_mRL"]
    same = dewater.cascade_case(cfg, sc, INVERT, 5.0, 15.0, 0.0, t_end=T_END, dt=DT, assume_breach_margin=margin)
    assert same["peak_Q_m3s"] == pytest.approx(base["peak_Q_m3s"], rel=1e-9)   # no dewatering: unchanged
    r = dewater.cascade_case(cfg, sc, INVERT, 5.0, 15.0, 12.0, t_end=T_END, dt=DT, assume_breach_margin=margin)
    assert not r["cascade"]                                   # the fixed trigger would not be reached ...
    assert r["effective_trigger_mRL"] == pytest.approx(r["pond2_peak_level_unbreached_mRL"] - margin)
    assert 0.7 * base["peak_Q_m3s"] < r["peak_Q_m3s"] < base["peak_Q_m3s"]   # ... but the pond still fails
    assert r["volume_released_m3"] < base["volume_released_m3"]
