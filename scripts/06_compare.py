#!/usr/bin/env python
"""Compare modelled road arrival times / depths with the Damwatch 2016 values quoted in the
WIL Emergency Evacuation Plan (config/dam.yaml: previous_results.arrival_times)."""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config  # noqa: E402


def hm_to_h(s: str) -> float:
    h, m = s.split(":")
    return int(h) + int(m) / 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="east")
    config.add_mode_arg(ap)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    mode = config.mode_from_args(a)
    out_dir = config.scenario_dir(a.scenario)
    rt = pd.read_csv(out_dir / f"roads_{mode}{a.tag}.csv")
    prev = config.dam()["previous_results"]["arrival_times"]
    idx = {"north": 0, "south": 1, "east": 2}.get(a.scenario)
    rows = []
    for road, rec in prev.items():
        m = rt[rt["road"] == road]
        model_t = float(m["first_arrival_h"].iloc[0]) if not m.empty and pd.notna(m["first_arrival_h"].iloc[0]) else None
        model_d = float(m["max_depth_m"].iloc[0]) if not m.empty else None
        dw_t = hm_to_h(rec[a.scenario]) if idx is not None and a.scenario in rec else None
        dw_d = rec["depth_m"][idx] if idx is not None else None
        rows.append({"road": road,
                     "Damwatch 2016 arrival (h)": round(dw_t, 2) if dw_t is not None else None,
                     "model arrival (h)": round(model_t, 2) if model_t is not None else None,
                     "Damwatch depth (m)": dw_d, "model max depth (m)": round(model_d, 2) if model_d is not None else None})
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / f"compare_damwatch_{mode}{a.tag}.csv", index=False)
    print(df.to_markdown(index=False) if hasattr(df, "to_markdown") else df.to_string(index=False))


if __name__ == "__main__":
    main()
