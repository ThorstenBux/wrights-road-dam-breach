#!/usr/bin/env python
"""EXPLORATORY: summarise the shelterbelt runs of scripts/16_run_shelterbelts.py against the same-mesh baseline.

Expects scripts/05_postprocess.py and scripts/06_compare.py to have been run with --tag _treesnone / _trees012 / ...
Writes outputs/<scenario>/shelterbelts_<mode>.{csv,png,json}. Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", default="east"); config.add_mode_arg(ap)
    ap.add_argument("--tags", nargs="+", default=["_trees012", "_trees020", "_trees030"])
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    mode = config.mode_from_args(a); out = config.scenario_dir(a.scenario); site = config.site()
    thr = site["run"]["depth_threshold_m"]
    rd = lambda key, tag: rasterio.open(out / f"{key}_{mode}{tag}.tif")
    with rd("arrival_h", "_treesnone") as ds:
        A0 = ds.read(1).astype(float); ext = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]; nod = ds.nodata; cell = ds.res[0] ** 2
    with rd("max_depth", "_treesnone") as ds:
        D0 = ds.read(1).astype(float)
    clean = lambda A: np.where((A == nod) | ~np.isfinite(A), np.nan, A)
    A0, D0 = clean(A0), clean(D0)
    dw = pd.read_csv(out / f"compare_damwatch_{mode}_treesnone.csv").set_index("road")
    table = dw[["Damwatch 2016 arrival (h)", "Damwatch depth (m)"]].copy()
    table["arrival none (h)"] = dw["model arrival (h)"]; table["depth none (m)"] = dw["model max depth (m)"]
    summary = {"note": "exploratory screening – not a certified assessment", "runs": {}}
    fig, axs = plt.subplots(len(a.tags), 2, figsize=(20, 5.2 * len(a.tags)), squeeze=False)
    for row, tag in zip(axs, a.tags):
        with rd("arrival_h", tag) as ds:
            A = clean(ds.read(1).astype(float))
        with rd("max_depth", tag) as ds:
            D = clean(ds.read(1).astype(float))
        both = np.isfinite(A) & np.isfinite(A0); dA = np.where(both, A - A0, np.nan) * 60
        wet = (np.nan_to_num(D) > thr) | (np.nan_to_num(D0) > thr); dD = np.where(wet, np.nan_to_num(D) - np.nan_to_num(D0), np.nan)
        c = pd.read_csv(out / f"compare_damwatch_{mode}{tag}.csv").set_index("road")
        label = f"n={int(tag[-3:]) / 100:.2f}"
        table[f"arrival {label} (h)"] = c["model arrival (h)"]; table[f"depth {label} (m)"] = c["model max depth (m)"]
        meta = json.loads((out / f"run_meta_{mode}{tag}.json").read_text())
        far = A0 > np.nanpercentile(A0, 75)      # the last quarter of the flooded area to be reached
        summary["runs"][tag] = {
            "shelterbelts": meta.get("shelterbelts"),
            "flooded_area_km2": float(np.isfinite(A).sum() * cell / 1e6), "flooded_area_none_km2": float(np.isfinite(A0).sum() * cell / 1e6),
            "arrival_delay_min_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dA, [5, 50, 95])],
            "arrival_delay_min_median_in_far_field": float(np.nanmedian(dA[far & both])),
            "depth_change_m_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dD, [5, 50, 95])]}
        lim = max(15.0, float(np.nanpercentile(np.abs(dA), 98)))
        for ax, arr, lab, l in ((row[0], dA, f"arrival delay, trees {label} minus none (min)", lim), (row[1], dD, f"peak depth change, trees {label} minus none (m)", 0.3)):
            im = ax.imshow(arr, extent=ext, cmap="RdBu_r", vmin=-l, vmax=l); plt.colorbar(im, ax=ax, shrink=0.7)
            ax.add_patch(plt.Polygon(site["site"]["footprint_nztm"], fc="0.7", ec="k")); ax.set_title(lab, fontsize=9); ax.tick_params(labelsize=6)
    fig.suptitle(f"{a.scenario} {mode}: tree shelterbelts as roughness vs none (same mesh) – exploratory screening, not a certified assessment", fontsize=10)
    fig.tight_layout(); fig.savefig(out / f"shelterbelts_{mode}.png", dpi=120)
    table.round(2).to_csv(out / f"shelterbelts_{mode}.csv")
    (out / f"shelterbelts_{mode}.json").write_text(json.dumps(summary, indent=2))
    print(table.round(2).to_string()); print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
