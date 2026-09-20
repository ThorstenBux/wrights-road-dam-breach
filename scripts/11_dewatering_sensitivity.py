#!/usr/bin/env python
"""EXPLORATORY: how does emergency dewatering for some hours before the breach change the breach hydrograph?

Stand-alone sensitivity (level-pool routing only, runs in about a minute). Reads config/dewatering.yaml and
writes to outputs/dewatering/<scenario>/; it never touches the scenario outputs used by scripts 04-10.
The breach invert is taken from the scenario's existing breach_summary.json (script 03) so the zero-hour
case reproduces the published hydrograph.  Screening model, not a certified assessment.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, dewater  # noqa: E402

NOTE = "Screening-level sensitivity, not a certified assessment. Dewatering rates are EAP Table F.1 examples."


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = [k for k in rows[0] if not k.startswith("_")]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k in keys})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="east")
    ap.add_argument("--invert", type=float, default=None, help="breach invert (m RL); default: from script 03 output")
    ap.add_argument("--fixed-trigger", action="store_true",
                    help="cascades: keep the Pond 2 trigger fixed, so enough dewatering prevents the breach "
                         "(default: Pond 2 is assumed to fail anyway, at a correspondingly lower level)")
    ap.add_argument("--write-hydrograph", type=float, default=None, metavar="HOURS",
                    help="also write the breach hydrograph CSV for this many hours of dewatering (for the 2D race runs)")
    ap.add_argument("--rate-case", default="high", help="rate case for --write-hydrograph")
    ap.add_argument("--dt", type=float, default=None, help="routing step (s); default breach_defaults.routing_dt_s")
    a = ap.parse_args()

    cfg, sc, dw = config.dam(), config.scenario(a.scenario), config.load_yaml("dewatering.yaml")
    if sc.get("breaches"):
        raise SystemExit("multi-breach scenarios are not supported by this sensitivity")
    invert = a.invert
    if invert is None:
        summ = config.OUTPUTS / a.scenario / "breach_summary.json"
        if not summ.exists():
            raise SystemExit(f"{summ} not found – run scripts/03_breach_hydrograph.py first or pass --invert")
        invert = float(json.loads(summ.read_text())["breach_invert_mRL"])
    out_dir = config.OUTPUTS / "dewatering" / a.scenario
    out_dir.mkdir(parents=True, exist_ok=True)
    hours = [float(h) for h in dw["durations_h"]]
    default_trigger = float(cfg["cascade"]["pond2_trigger_mRL"])

    margin = None
    if sc["cascade"] and not a.fixed_trigger:
        base = dewater.cascade_case(cfg, sc, invert, 0.0, 0.0, 0.0, dt=a.dt, full=False)
        margin = max(base["pond2_peak_level_unbreached_mRL"] - default_trigger, 0.0)
        print(f"[dewater] Pond 2 assumed to fail anyway: breach initiates {margin:.2f} m below its unbreached peak level")
    suffix = "_fixed_trigger" if a.fixed_trigger else ""

    rows, thresholds = [], {}
    for case, rates in dw["rate_cases"].items():
        q1, q2 = float(rates["pond1_m3s"]), float(rates["pond2_m3s"])
        case_rows = []
        for h in hours:
            if sc["cascade"]:
                r = dewater.cascade_case(cfg, sc, invert, q1, q2, h, dt=a.dt, assume_breach_margin=margin)
            else:
                r = dewater.single_case(cfg, sc, invert, q1 if sc["pond"] == "pond1" else q2, h, dt=a.dt)
            r = {"rate_case": case, **r}
            case_rows.append(r)
            print(f"[dewater] {a.scenario} {case} {h:4.0f} h: " +
                  (f"P1 {r['pond1_level_mRL']:.2f} P2 {r['pond2_level_mRL']:.2f} -> P2 peak "
                   f"{r['pond2_peak_level_unbreached_mRL']:.2f} m RL, reaches {default_trigger}={r['cascade']}, "
                   f"breach at {r['effective_trigger_mRL']:.2f}, " if sc["cascade"] else
                   f"pond {r['pond_level_mRL']:.2f} m RL, ") + f"peak Q {r['peak_Q_m3s']:.0f} m3/s")
        rows += case_rows
        if sc["cascade"]:
            for key, col in (("routed_no_tailwater", "pond2_peak_level_unbreached_mRL"),
                             ("static_equalisation", "pond2_equalised_level_mRL")):
                peaks = [r[col] for r in case_rows]
                thresholds.setdefault(key, {})[case] = {f"{t:.1f}": dewater.threshold_hours(hours, peaks, float(t))
                                                        for t in dw["trigger_levels_mRL"]}

    if a.write_hydrograph is not None:
        from damflood.breach import write_hydrograph_csv
        rates = dw["rate_cases"][a.rate_case]; q1, q2 = float(rates["pond1_m3s"]), float(rates["pond2_m3s"])
        r = (dewater.cascade_case(cfg, sc, invert, q1, q2, a.write_hydrograph, dt=a.dt, assume_breach_margin=margin)
             if sc["cascade"] else
             dewater.single_case(cfg, sc, invert, q1 if sc["pond"] == "pond1" else q2, a.write_hydrograph, dt=a.dt))
        rr = r["_r2"] if sc["cascade"] else r["_r"]
        stem = f"hydrograph_dewater{a.write_hydrograph:g}h_{a.rate_case}{suffix}"
        write_hydrograph_csv(out_dir / f"{stem}.csv", rr, every=max(int(30 / (a.dt or float(cfg["breach_defaults"]["routing_dt_s"]))), 1))
        (out_dir / f"{stem}.json").write_text(json.dumps(
            {"t_init_s": rr["t_init"], "note": NOTE, **{k: v for k, v in r.items() if not k.startswith("_")}}, indent=2))
        print(f"[dewater] wrote {out_dir / (stem + '.csv')}")

    write_csv(out_dir / f"dewatering_sensitivity{suffix}.csv", rows)
    summary = {"scenario": a.scenario, "breach_invert_mRL": invert, "default_trigger_mRL": default_trigger,
               "rate_cases": dw["rate_cases"], "durations_h": hours, "pond2_assumed_to_fail_anyway": margin is not None, "breach_margin_below_peak_m": margin,
               "hours_of_dewatering_that_prevent_the_cascade_by_trigger_mRL": thresholds or None, "note": NOTE}
    (out_dir / f"dewatering_summary{suffix}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    plot(a.scenario, sc, rows, dw, default_trigger, out_dir, suffix)


def plot(name, sc, rows, dw, default_trigger, out_dir, suffix=""):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    cases = list(dw["rate_cases"])
    fig, ax = plt.subplots(1, 3 if sc["cascade"] else 2, figsize=(15 if sc["cascade"] else 10, 4.6))
    for c, col in zip(cases, ("tab:blue", "tab:red")):
        rr = [r for r in rows if r["rate_case"] == c]
        h = [r["hours"] for r in rr]
        ax[0].plot(h, [r["peak_Q_m3s"] for r in rr], "o-", color=col, label=f"{c} rates")
        ax[1].plot(h, [r["volume_released_m3"] / 1e6 for r in rr], "o-", color=col, label=f"{c} rates")
        if sc["cascade"]:
            ax[2].plot(h, [r["pond2_peak_level_unbreached_mRL"] for r in rr], "o-", color=col, label=f"{c} rates, routed (no tailwater)")
            ax[2].plot(h, [r["pond2_equalised_level_mRL"] for r in rr], "s:", color=col, ms=3, label=f"{c} rates, static equalisation")
    ax[0].set_ylabel("peak breach outflow (m3/s)"); ax[1].set_ylabel("volume released downstream (Mm3)")
    if sc["cascade"]:
        for t in dw["trigger_levels_mRL"]:
            ax[2].axhline(t, color="k", lw=1.6 if abs(t - default_trigger) < 1e-9 else 0.6, ls="--")
            ax[2].text(hrs_max(rows), t, f" {t:.1f}" + (" (default trigger)" if abs(t - default_trigger) < 1e-9 else ""),
                       va="bottom", ha="right", fontsize=7)
        ax[2].set_ylabel("Pond 2 peak level if it does not breach (m RL)")
    for x in ax:
        x.set_xlabel("hours of dewatering before the breach"); x.grid(alpha=.3); x.legend(fontsize=8)
    fig.suptitle(f"{name}: effect of emergency dewatering before the breach – exploratory screening, "
                 "not a certified assessment", fontsize=9)
    fig.tight_layout(); fig.savefig(out_dir / f"dewatering_sensitivity{suffix}.png", dpi=140)


def hrs_max(rows):
    return max(r["hours"] for r in rows)


if __name__ == "__main__":
    main()
