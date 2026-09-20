"""Emergency dewatering before a breach: lowered initial pond levels for the level-pool routing.

Exploratory and self-contained – the main pipeline does not import this module.  It only reuses
`damflood.breach` (Reservoir, BreachGeometry, BreachEvent, route), so with zero hours of dewatering a
case is identical to what scripts/03_breach_hydrograph.py routes.

Screening model, not a certified assessment.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .breach import BreachEvent, BreachGeometry, Reservoir, hydrograph_summary, route


def reservoir(cfg: dict, key: str) -> Reservoir:
    p = cfg["ponds"][key]
    f = lambda k: float(p[k])  # YAML 1.1 reads '2.0e6' as a string
    return Reservoir(key, fsl=f("fsl_mRL"), invert=f("invert_mRL"), area_fsl=f("area_fsl_m2"),
                     volume_fsl=f("volume_m3"), crest=f("crest_mRL"))


def drawdown(res: Reservoir, q_m3s: float, hours: float) -> tuple[float, float]:
    """Pool level after releasing a constant net `q_m3s` for `hours` from FSL.
    Returns (level m RL, volume removed m3); the pond cannot go below its invert."""
    removed = min(max(q_m3s, 0.0) * max(hours, 0.0) * 3600.0, res.volume_fsl)
    return res.level(res.volume_fsl - removed), removed


def equalised_level(p1: Reservoir, p2: Reservoir, level1: float, level2: float, sill: float) -> float:
    """Static level both ponds settle at once connected above `sill` (the dividing-breach invert), i.e. with
    full tailwater control.  The routed cascade ignores tailwater (Pond 1 always drains to the sill), so it
    gives the upper bound on the Pond 2 level and this gives the lower bound."""
    if level1 <= sill:
        return level2
    total = float(p1.volume(level1) + p2.volume(level2))
    if float(p1.volume(sill) + p2.volume(sill)) >= total:   # Pond 2 never rises to the sill: Pond 1 drains to it
        return p2.level(float(p2.volume(level2) + p1.volume(level1) - p1.volume(sill)))
    lo, hi = sill, max(level1, level2)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if float(p1.volume(mid) + p2.volume(mid)) < total else (lo, mid)
    return 0.5 * (lo + hi)


def _event(res: Reservoir, geom: BreachGeometry, bd: dict, **kw) -> BreachEvent:
    return BreachEvent(res, geom, weir_coeff_rect=bd["weir_coeff_rect"], weir_coeff_tri=bd["weir_coeff_tri"], **kw)


def _inflow(r: dict):
    tt, qq = r["t"], r["Q_out"]
    return lambda s: float(np.interp(s, tt, qq, left=0.0, right=0.0))


def route_pond1(cfg: dict, level1: float, t_end: float, dt: float) -> dict:
    """Pond 1 piping through the dividing embankment from `level1` (breach sized for that pool)."""
    bd, p1 = cfg["breach_defaults"], reservoir(cfg, "pond1")
    invert = float(cfg["cascade"]["dividing_breach_invert_mRL"])
    if level1 <= invert:   # drawn down below the dividing-breach invert: nothing can pass into Pond 2
        n = int(np.ceil(t_end / dt)) + 1
        z = np.zeros(n)
        return {"t": np.arange(n) * dt, "Q_out": z, "Q_in": z, "level": z + level1, "t_init": None, "volume_released": 0.0}
    g = BreachGeometry.from_froehlich_2008(p1, invert=invert, mode=cfg["cascade"]["dividing_breach_mode"],
                                           pool_level=level1, progression=bd["progression"])
    return route(_event(p1, g, bd, initial_level=level1), t_end, dt)


def pond2_peak_level_unbreached(cfg: dict, r1: dict, level2: float, t_end: float, dt: float) -> float:
    """Highest Pond 2 level when it receives the Pond 1 outflow and does NOT breach.  The cascade
    initiates for any trigger level at or below this value, so one routing serves every trigger."""
    bd, p2 = cfg["breach_defaults"], reservoir(cfg, "pond2")
    g = BreachGeometry(mode="overtopping", invert=p2.crest, bottom_width=0.0, side_slope=0.0, formation_time=1.0)
    ev = _event(p2, g, bd, initial_level=level2, trigger_level=float("inf"))
    return float(route(ev, t_end, dt, inflow=_inflow(r1))["level"].max())


def route_pond2(cfg: dict, sc: dict, r1: dict, level2: float, invert: float, trigger: float,
                t_end: float, dt: float) -> dict:
    """Pond 2 external overtopping breach (same geometry rule as script 03: sized at the trigger pool)."""
    bd, p2 = cfg["breach_defaults"], reservoir(cfg, sc["pond"])
    g = BreachGeometry.from_froehlich_2008(p2, invert=invert, mode=sc["mode"], pool_level=trigger,
                                           progression=bd["progression"])
    return route(_event(p2, g, bd, initial_level=level2, trigger_level=trigger), t_end, dt, inflow=_inflow(r1))


def cascade_case(cfg: dict, sc: dict, invert: float, q1: float, q2: float, hours: float,
                 trigger: Optional[float] = None, t_end: Optional[float] = None, dt: Optional[float] = None,
                 full: bool = True, assume_breach_margin: Optional[float] = None) -> dict:
    """One dewatering case for a cascade scenario.  `full=False` skips the external-breach routing.

    assume_breach_margin: if given, Pond 2 is assumed to fail even when the drawn-down ponds no longer reach
    `trigger`: the breach then initiates `margin` metres below the peak level Pond 2 would reach unbreached
    (use the undrawn case's peak - trigger, so the breach starts at the same point of the filling curve)."""
    bd = cfg["breach_defaults"]
    dt = float(bd["routing_dt_s"]) if dt is None else dt
    t_end = float(bd["duration_h"]) * 3600 if t_end is None else t_end
    trigger = float(cfg["cascade"]["pond2_trigger_mRL"]) if trigger is None else trigger
    l1, v1 = drawdown(reservoir(cfg, "pond1"), q1, hours)
    l2, v2 = drawdown(reservoir(cfg, "pond2"), q2, hours)
    r1 = route_pond1(cfg, l1, t_end, dt)
    peak2 = pond2_peak_level_unbreached(cfg, r1, l2, t_end, dt)
    out = {"hours": hours, "q_pond1_m3s": q1, "q_pond2_m3s": q2, "pond1_level_mRL": l1, "pond2_level_mRL": l2,
           "volume_dewatered_m3": v1 + v2, "pond1_to_pond2_m3": r1["volume_released"],
           "pond2_peak_level_unbreached_mRL": peak2,
           "pond2_equalised_level_mRL": equalised_level(reservoir(cfg, "pond1"), reservoir(cfg, "pond2"), l1, l2,
                                                        float(cfg["cascade"]["dividing_breach_invert_mRL"])),
           "trigger_mRL": trigger, "cascade": bool(peak2 >= trigger)}
    if assume_breach_margin is not None:
        trigger = max(min(trigger, peak2 - assume_breach_margin), l2)
    out["effective_trigger_mRL"] = trigger
    if full:
        r2 = route_pond2(cfg, sc, r1, l2, invert, trigger, t_end, dt)
        s = hydrograph_summary(r2)
        out.update({"peak_Q_m3s": s["peak_Q_m3s"], "volume_released_m3": s["volume_released_m3"],
                    "t_init_h": None if r2["t_init"] is None else r2["t_init"] / 3600,
                    "time_to_peak_h": s["time_to_peak_s"] / 3600 if s["peak_Q_m3s"] > 0 else None})
        out["_r1"], out["_r2"] = r1, r2
    return out


def single_case(cfg: dict, sc: dict, invert: float, q: float, hours: float,
                t_end: Optional[float] = None, dt: Optional[float] = None) -> dict:
    """One dewatering case for a single-pond scenario (e.g. west, north): lower head and volume only."""
    bd = cfg["breach_defaults"]
    dt = float(bd["routing_dt_s"]) if dt is None else dt
    t_end = float(bd["duration_h"]) * 3600 if t_end is None else t_end
    res = reservoir(cfg, sc["pond"])
    lvl, removed = drawdown(res, q, hours)
    out = {"hours": hours, "q_m3s": q, "pond_level_mRL": lvl, "volume_dewatered_m3": removed}
    if lvl <= invert:
        out.update({"peak_Q_m3s": 0.0, "volume_released_m3": 0.0, "time_to_peak_h": None})
        return out
    g = BreachGeometry.from_froehlich_2008(res, invert=invert, mode=sc["mode"], pool_level=lvl,
                                           progression=bd["progression"])
    r = route(_event(res, g, bd, initial_level=lvl), t_end, dt)
    s = hydrograph_summary(r)
    out.update({"peak_Q_m3s": s["peak_Q_m3s"], "volume_released_m3": s["volume_released_m3"],
                "time_to_peak_h": s["time_to_peak_s"] / 3600, "_r": r})
    return out


def threshold_hours(hours: list[float], peak_levels: list[float], trigger: float) -> Optional[float]:
    """Shortest dewatering duration that keeps Pond 2 below `trigger` (linear interpolation between the
    tested durations).  0.0 if even the undrawn ponds stay below it, None if no tested duration is enough."""
    h, z = np.asarray(hours, float), np.asarray(peak_levels, float)
    if z[0] < trigger:
        return 0.0
    below = np.nonzero(z < trigger)[0]
    if not below.size:
        return None
    i = int(below[0])
    return float(h[i - 1] + (z[i - 1] - trigger) / (z[i - 1] - z[i]) * (h[i] - h[i - 1]))
