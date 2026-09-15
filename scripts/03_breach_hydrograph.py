#!/usr/bin/env python
"""Breach parameters + level-pool routing -> outflow hydrograph for a scenario."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config  # noqa: E402
from damflood.breach import (BreachEvent, BreachGeometry, MultiBreachEvent, Reservoir, cascade,  # noqa: E402
                             cascade_multi, froehlich_1995_peak, hydrograph_summary, route, write_hydrograph_csv)


def reservoir(cfg: dict, key: str) -> Reservoir:
    p = cfg["ponds"][key]
    f = lambda k: float(p[k])  # YAML 1.1 reads '2.0e6' as a string
    return Reservoir(key, fsl=f("fsl_mRL"), invert=f("invert_mRL"), area_fsl=f("area_fsl_m2"),
                     volume_fsl=f("volume_m3"), crest=f("crest_mRL"))


def toe_level(dem_path, loc, outward, dist=(40, 60, 80, 100)):
    """Natural ground just outside the embankment toe (lowest of a few samples)."""
    from damflood.terrain import DEM
    dem = DEM(dem_path)
    xs = [loc[0] + outward[0] * d for d in dist]; ys = [loc[1] + outward[1] * d for d in dist]
    z = dem.sample(xs, ys)
    return float(np.min(z)), [round(float(v), 2) for v in z]


def latest_dem():
    cands = sorted(config.DATA_DERIVED.glob("dem_*m.tif"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--dem", type=Path, default=None)
    ap.add_argument("--invert", type=float, default=None, help="override breach invert (m RL)")
    ap.add_argument("--width-factor", type=float, default=1.0)
    ap.add_argument("--time-factor", type=float, default=1.0)
    ap.add_argument("--scour", type=float, default=None, help="extra scour below natural ground (m)")
    ap.add_argument("--trigger", type=float, default=None, help="Pond 2 breach initiation level (m RL) for cascades")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    cfg = config.dam(); sc = config.scenario(a.scenario); bd = cfg["breach_defaults"]
    out_dir = config.scenario_dir(a.scenario)
    dt = float(bd["routing_dt_s"]); t_end = float(bd["duration_h"]) * 3600

    # breach invert = natural ground at toe (from LiDAR) unless overridden
    dem_path = a.dem or latest_dem()
    if a.invert is not None:
        invert, samples, src = a.invert, [], "user"
    elif dem_path is not None:
        invert, samples = toe_level(dem_path, sc["breach_location_nztm"], sc["outward_dir"])
        src = f"LiDAR toe ({dem_path.name})"
    else:
        raise SystemExit("No DEM found – run scripts/01_fetch_dem.py first or pass --invert")
    scour = bd["breach_invert_scour_m"] if a.scour is None else a.scour
    invert -= scour

    pond = reservoir(cfg, sc["pond"])
    events, notes = [], []
    if sc.get("breaches"):
        main_r, results, events, notes, extra = multi_breach(cfg, sc, bd, a, dem_path, dt, t_end)
        write_hydrograph_csv(out_dir / f"hydrograph{a.tag}.csv", main_r, every=int(30 / dt))
        summ = hydrograph_summary(main_r)
        summ.update({"scenario": a.scenario, "description": sc["description"], "title": sc.get("title"),
                     "breach_invert_mRL": extra["primary_invert"], "breach_invert_source": extra["invert_source"],
                     "scour_m": scour, "pond2_trigger_mRL": None, "pond2_max_level_mRL": float(results[-1]["level"].max()),
                     "damwatch_2012_2016_peak_m3s": cfg["previous_results"]["peak_breach_outflow_m3s"],
                     "breach_notes": notes, "width_factor": a.width_factor, "time_factor": extra["time_factor"],
                     "breaches": extra["breaches"], "seismic": True,
                     "method": "Froehlich (2008) parameters per embankment, formation time x%.2f (seismic); simultaneous "
                               "level-pool routing of all breaches; broad-crested weir; no tailwater submergence" % extra["time_factor"]})
        (out_dir / f"breach_summary{a.tag}.json").write_text(json.dumps(summ, indent=2))
        print(json.dumps({k: v for k, v in summ.items() if k not in ("breach_notes",)}, indent=2))
        for n in notes:
            print("  -", n)
        plot_multi(a, sc, out_dir, results, events)
        return
    if sc["cascade"]:
        p1 = reservoir(cfg, "pond1")
        g1 = BreachGeometry.from_froehlich_2008(p1, invert=cfg["cascade"]["dividing_breach_invert_mRL"],
                                                mode=cfg["cascade"]["dividing_breach_mode"], progression=bd["progression"])
        g1.bottom_width *= a.width_factor; g1.formation_time *= a.time_factor
        events.append(BreachEvent(p1, g1, weir_coeff_rect=bd["weir_coeff_rect"], weir_coeff_tri=bd["weir_coeff_tri"]))
        notes.append(f"Pond 1 -> Pond 2 dividing breach ({g1.mode}): {g1.notes}; B_bot={g1.bottom_width:.1f} m, z={g1.side_slope}, t_f={g1.formation_time/3600:.2f} h")
        trigger = a.trigger if a.trigger is not None else float(cfg["cascade"]["pond2_trigger_mRL"])
        g2 = BreachGeometry.from_froehlich_2008(pond, invert=invert, mode=sc["mode"], pool_level=trigger, progression=bd["progression"])
        g2.bottom_width *= a.width_factor; g2.formation_time *= a.time_factor
        events.append(BreachEvent(pond, g2, trigger_level=trigger, weir_coeff_rect=bd["weir_coeff_rect"], weir_coeff_tri=bd["weir_coeff_tri"]))
        notes.append(f"{sc['pond']} external breach ({g2.mode}, initiates when Pond 2 reaches {trigger} m RL; crest {pond.crest} m): {g2.notes}; B_bot={g2.bottom_width:.1f} m, z={g2.side_slope}, t_f={g2.formation_time/3600:.2f} h")
        results = cascade(events, t_end, dt)
        main_r = results[-1]
        for i, r in enumerate(results):
            write_hydrograph_csv(out_dir / f"hydrograph_stage{i+1}{a.tag}.csv", r, every=int(30 / dt))
    else:
        g = BreachGeometry.from_froehlich_2008(pond, invert=invert, mode=sc["mode"], progression=bd["progression"])
        g.bottom_width *= a.width_factor; g.formation_time *= a.time_factor
        events.append(BreachEvent(pond, g, weir_coeff_rect=bd["weir_coeff_rect"], weir_coeff_tri=bd["weir_coeff_tri"]))
        notes.append(f"{sc['pond']} external breach ({g.mode}): {g.notes}; B_bot={g.bottom_width:.1f} m, z={g.side_slope}, t_f={g.formation_time/3600:.2f} h")
        main_r = route(events[0], t_end, dt); results = [main_r]

    write_hydrograph_csv(out_dir / f"hydrograph{a.tag}.csv", main_r, every=int(30 / dt))
    summ = hydrograph_summary(main_r)
    pool0 = (trigger if sc["cascade"] else pond.fsl)
    h_w = pool0 - invert
    summ.update({
        "scenario": a.scenario, "description": sc["description"], "breach_invert_mRL": invert,
        "breach_invert_source": src, "toe_samples_m": samples, "scour_m": scour,
        "froehlich_1995_peak_check_m3s": froehlich_1995_peak(pond.volume_above(invert, pool0), h_w),
        "pond2_trigger_mRL": (trigger if sc["cascade"] else None),
        "pond2_max_level_mRL": float(main_r["level"].max()),
        "damwatch_2012_2016_peak_m3s": cfg["previous_results"]["peak_breach_outflow_m3s"],
        "breach_notes": notes, "width_factor": a.width_factor, "time_factor": a.time_factor,
        "method": "Froehlich (2008) parameters; level-pool routing; broad-crested weir; no tailwater submergence",
    })
    (out_dir / f"breach_summary{a.tag}.json").write_text(json.dumps(summ, indent=2))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("breach_notes",)}, indent=2))
    for n in notes:
        print("  -", n)

    # plot
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for i, r in enumerate(results):
        ax[0].plot(r["t"] / 3600, r["Q_out"], label=f"stage {i+1}: {events[i].reservoir.name} outflow")
        ax[1].plot(r["t"] / 3600, r["level"], label=f"{events[i].reservoir.name} level")
        ax[1].plot(r["t"] / 3600, r["breach_bottom"], "--", lw=0.8, label=f"{events[i].reservoir.name} breach bottom")
    ax[0].set_ylabel("Q (m3/s)"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[0].set_title(f"{a.scenario}: {sc['description'][:90]}", fontsize=9)
    ax[1].set_ylabel("level (m RL)"); ax[1].set_xlabel("hours after initiation"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(out_dir / f"hydrograph{a.tag}.png", dpi=140)


def multi_breach(cfg, sc, bd, a, dem_path, dt, t_end):
    """Simultaneous breaches of several embankments (seismic scenario). Pond 1 breaches (incl. the dividing
    embankment feeding Pond 2) are routed first, then Pond 2 with the dividing inflow. Returns the total
    downstream hydrograph (sum of all external breaches) plus per-breach CSVs."""
    tf = float(sc.get("formation_time_factor", 1.0)) * a.time_factor
    scour = bd["breach_invert_scour_m"] if a.scour is None else a.scour
    per_pond: dict[str, dict] = {}
    notes, breaches_meta, invert_src, primary_invert = [], [], "", None
    for b in sc["breaches"]:
        res = reservoir(cfg, b["pond"])
        if "invert_mRL" in b:
            invert, samples, src = float(b["invert_mRL"]), [], "config"
        elif a.invert is not None:
            invert, samples, src = a.invert, [], "user"
        else:
            invert, samples = toe_level(dem_path, b["location_nztm"], b["outward_dir"]); src = f"LiDAR toe ({dem_path.name})"
            invert -= scour
        g = BreachGeometry.from_froehlich_2008(res, invert=invert, mode=b["mode"], progression=bd["progression"])
        g.bottom_width *= a.width_factor; g.formation_time *= tf
        per_pond.setdefault(b["pond"], {})[b["name"]] = g
        if b["name"] == "east" or primary_invert is None and "location_nztm" in b:
            primary_invert, invert_src = invert, src
        notes.append(f"{b['name']} ({b['pond']}, {g.mode}{', feeds ' + b['feeds'] if b.get('feeds') else ''}): invert {invert:.1f} m ({src}); "
                     f"{g.notes}; B_bot={g.bottom_width:.1f} m, z={g.side_slope}, t_f={g.formation_time/3600:.2f} h (x{tf:g})")
        breaches_meta.append({"name": b["name"], "pond": b["pond"], "mode": b["mode"], "feeds": b.get("feeds"),
                              "location_nztm": b.get("location_nztm"), "outward_dir": b.get("outward_dir"),
                              "invert_mRL": invert, "toe_samples_m": samples, "B_bot_m": g.bottom_width,
                              "z": g.side_slope, "t_f_h": g.formation_time / 3600})
    feeds = {b["pond"]: b["name"] for b in sc["breaches"] if b.get("feeds")}
    order = ["pond1", "pond2"] if "pond1" in per_pond else list(per_pond)
    events = [MultiBreachEvent(reservoir(cfg, pk), per_pond[pk], feeds=feeds.get(pk),
                               weir_coeff_rect=bd["weir_coeff_rect"], weir_coeff_tri=bd["weir_coeff_tri"]) for pk in order]
    results = cascade_multi(events, t_end, dt)
    out_dir = config.scenario_dir(a.scenario)
    # downstream hydrograph = every breach that does not feed another pond
    t = results[0]["t"]; Q = np.zeros_like(t)
    for ev, r in zip(events, results):
        for name, q in r["Q_by_breach"].items():
            if name != ev.feeds:
                Q += q
            rr = dict(r); rr["Q_out"] = q; rr["Q_in"] = r["Q_in"] if name == ev.feeds else np.zeros_like(q)
            write_hydrograph_csv(out_dir / f"hydrograph_{name}{a.tag}.csv", rr, every=int(30 / dt))
    for bm in breaches_meta:
        r = results[order.index(bm["pond"])]; q = r["Q_by_breach"][bm["name"]]
        i = int(np.argmax(q)); bm["peak_Q_m3s"] = float(q[i]); bm["time_to_peak_h"] = float(t[i] / 3600)
        bm["volume_m3"] = float(np.trapezoid(q, t))
    main_r = {"t": t, "Q_out": Q, "Q_in": np.zeros_like(t), "level": results[-1]["level"], "breach_bottom": results[-1]["breach_bottom"],
              "breach_bottom_width": results[-1]["breach_bottom_width"], "breach_top_width": results[-1]["breach_top_width"],
              "t_init": 0.0, "volume_released": float(np.trapezoid(Q, t))}
    extra = {"primary_invert": primary_invert, "invert_source": invert_src, "time_factor": tf, "breaches": breaches_meta}
    return main_r, results, events, notes, extra


def plot_multi(a, sc, out_dir, results, events):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for ev, r in zip(events, results):
        for name, q in r["Q_by_breach"].items():
            ax[0].plot(r["t"] / 3600, q, label=f"{ev.reservoir.name} -> {name}" + (" (into Pond 2)" if name == ev.feeds else ""),
                       ls="--" if name == ev.feeds else "-")
        ax[1].plot(r["t"] / 3600, r["level"], label=f"{ev.reservoir.name} level")
    tot = sum(q for ev, r in zip(events, results) for n, q in r["Q_by_breach"].items() if n != ev.feeds)
    ax[0].plot(results[0]["t"] / 3600, tot, "k", lw=2, label="total downstream outflow")
    ax[0].set_ylabel("Q (m3/s)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
    ax[0].set_title(f"{a.scenario}: {sc.get('title') or sc['description'][:90]}", fontsize=9)
    ax[1].set_ylabel("level (m RL)"); ax[1].set_xlabel("hours after the earthquake"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(out_dir / f"hydrograph{a.tag}.png", dpi=140)


if __name__ == "__main__":
    main()
