#!/usr/bin/env python
"""EXPLORATORY: what tree shelterbelts, a wet plain and an Eyre River in flood change – summary of the scripts/18 runs.

Expects scripts/05_postprocess.py to have been run on every scripts/18 run with --tag (wet runs with
--baseline-sww = the same storm without the breach; the baselines themselves too). Four questions:
  1. delay    do shelterbelts slow the breach flood less, or more, on a wet plain than on a dry one? (arrival / depth)
  2. redirect do they steer it somewhere else? (direction of the breach-added flow at its peak; volume through
              north-south screen lines per km of northing)
  3. eyre     what does the breach add to a river already in flood – discharge along the river, water leaving
              over each bank per km with and without the breach, rise of the flood level in the river
  4. inflows  the same with the Eyre flood doubled / with the dewatering flow of the races added (if those runs exist)
Writes outputs/wet/wet_compare_<mode>.{json,png} + csv tables. Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, post, vectors, wet  # noqa: E402

SCREEN_E = [1538000, 1542000, 1546000, 1550000, 1554000, 1558000]


def read_tif(p):
    with rasterio.open(p) as ds:
        a = ds.read(1).astype(float); a[(a == ds.nodata) | ~np.isfinite(a)] = np.nan
        return a, [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top], ds.res[0] ** 2


class Run:
    def __init__(self, scenario, mode, tag):
        self.scenario, self.mode, self.tag = scenario, mode, tag
        self.dir = config.scenario_dir(scenario); self.sww_path = self.dir / f"{scenario}_{mode}{tag}.sww"

    def ok(self):
        return self.sww_path.exists() and (self.dir / f"arrival_h_{self.mode}{self.tag}.tif").exists()

    def tif(self, key):
        return read_tif(self.dir / f"{key}_{self.mode}{self.tag}.tif")

    def meta(self):
        return json.loads((self.dir / f"run_meta_{self.mode}{self.tag}.json").read_text())

    def summary(self):
        return json.loads((self.dir / f"post_summary_{self.mode}{self.tag}.json").read_text())

    def roads(self):
        return pd.read_csv(self.dir / f"roads_{self.mode}{self.tag}.csv").set_index("road")


def peak_added_flow(run: post.SWW, base, t_from):
    """Per vertex: the breach-added unit discharge vector (run minus baseline) at the time its size peaks."""
    v = run.ds.variables; b = base.ds.variables if base is not None else None
    n = len(run.x); best = np.zeros(n); qx = np.zeros(n); qy = np.zeros(n)
    for k, t in enumerate(run.time):
        if t < t_from:
            continue
        dx = np.asarray(v["xmomentum"][k, :], float); dy = np.asarray(v["ymomentum"][k, :], float)
        if b is not None:
            dx = dx - np.asarray(b["xmomentum"][k, :], float); dy = dy - np.asarray(b["ymomentum"][k, :], float)
        m = np.hypot(dx, dy); up = m > best
        best[up] = m[up]; qx[up] = dx[up]; qy[up] = dy[up]
    return qx, qy, best


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    config.add_mode_arg(ap)
    ap.add_argument("--scenarios", nargs="+", default=["east", "quake"])
    ap.add_argument("--trees", nargs="+", default=["020", "030"])
    ap.add_argument("--baseline-scenario", default="east", help="where the no-breach runs live (they do not depend on the breach)")
    ap.add_argument("--q-min", type=float, default=0.05, help="m2/s: smaller breach-added flows are ignored in the direction statistics")
    a = ap.parse_args()
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    mode = config.mode_from_args(a) if (a.mode or a.production) else "extended"
    site, wcfg = config.site(), config.load_yaml("wet.yaml")["eyre"]
    thr = site["run"]["depth_threshold_m"]; bbox = config.mode_settings(mode)["bbox"]
    out = config.OUTPUTS / "wet"; out.mkdir(parents=True, exist_ok=True)
    res = {"note": "exploratory screening – not a certified assessment", "mode": mode, "delay": {}, "redirect": {}, "eyre": {}, "inflows": {}}
    base = lambda tr, extra="": Run(a.baseline_scenario, mode, f"_wet{extra}_trees{tr}_nobreach")

    # ---- 1. delay: trees vs none, dry vs wet -------------------------------------------------------------------
    rows = []; fig, axs = plt.subplots(len(a.scenarios), 2, figsize=(20, 5.4 * len(a.scenarios)), squeeze=False)
    for i, sc in enumerate(a.scenarios):
        for j, cond in enumerate(("dry", "wet")):
            r0 = Run(sc, mode, f"_{cond}_treesnone")
            if not r0.ok():
                print(f"[wet] missing {r0.sww_path.name} (or its post-processing) – skipped"); continue
            A0, ext, cell = r0.tif("arrival_h"); D0 = r0.tif("max_excess" if cond == "wet" else "max_depth")[0]
            s0 = r0.summary(); rd0 = r0.roads()
            rows.append({"scenario": sc, "condition": cond, "trees": "none", **{f"{k} arrival (h)": v for k, v in rd0["first_arrival_h"].items()}})
            for tr in a.trees:
                r = Run(sc, mode, f"_{cond}_trees{tr}")
                if not r.ok():
                    continue
                A = r.tif("arrival_h")[0]; D = r.tif("max_excess" if cond == "wet" else "max_depth")[0]
                both = np.isfinite(A) & np.isfinite(A0); dA = np.where(both, A - A0, np.nan) * 60
                wetc = (np.nan_to_num(D) > thr) | (np.nan_to_num(D0) > thr); dD = np.where(wetc, np.nan_to_num(D) - np.nan_to_num(D0), np.nan)
                far = A0 > np.nanpercentile(A0, 75)
                key = "breach_added_area_km2_gt_%.2fm" % thr if cond == "wet" else "inundated_area_km2_gt_%.2fm" % thr
                res["delay"][f"{sc}_{cond}_trees{tr}"] = {
                    "shelterbelts": r.meta().get("shelterbelts"),
                    "breach_flood_area_km2": r.summary().get(key), "breach_flood_area_none_km2": s0.get(key),
                    "arrival_delay_min_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dA, [5, 50, 95])],
                    "arrival_delay_min_mean": float(np.nanmean(dA)),
                    "arrival_delay_min_median_in_far_field": float(np.nanmedian(dA[far & both])),
                    "depth_change_m_percentiles_5_50_95": [float(v) for v in np.nanpercentile(dD, [5, 50, 95])],
                    "area_deeper_by_0.1m_km2": float((dD > 0.1).sum() * cell / 1e6), "area_shallower_by_0.1m_km2": float((dD < -0.1).sum() * cell / 1e6)}
                rows.append({"scenario": sc, "condition": cond, "trees": f"n=0.{tr[1:]}", **{f"{k} arrival (h)": v for k, v in r.roads()["first_arrival_h"].items()}})
                if tr == a.trees[0]:
                    im = axs[i][j].imshow(dA, extent=ext, cmap="RdBu_r", vmin=-45, vmax=45); plt.colorbar(im, ax=axs[i][j], shrink=0.7)
                    axs[i][j].add_patch(plt.Polygon(site["site"]["footprint_nztm"], fc="0.7", ec="k")); axs[i][j].tick_params(labelsize=6)
                    axs[i][j].set_title(f"{sc}, {cond} plain: arrival delay with shelterbelts n=0.{tr[1:]} minus none (min)", fontsize=9)
    fig.suptitle("Breach flood arrival: what tree shelterbelts change on a dry and on a wet plain (same mesh) – exploratory screening, not a certified assessment", fontsize=10)
    fig.tight_layout(); fig.savefig(out / f"wet_delay_{mode}.png", dpi=110); plt.close(fig)
    pd.DataFrame(rows).round(2).to_csv(out / f"wet_roads_{mode}.csv", index=False)

    # ---- geometry for 2 and 3 ----------------------------------------------------------------------------------
    W, S, E, N = bbox
    screens = {f"E{int(x / 1000)}": [(x, N - 300), (x, S + 300)] for x in SCREEN_E if W < x < E}     # drawn north -> south: eastward = positive
    eyre = wet.river_line(vectors.load(config.DATA_RAW / "osm_domain.gpkg", "waterways"), wcfg["name"], bbox, margin=wcfg["refine_half_width_m"] + 100)
    sm = eyre.simplify(60.0); hw = wcfg["refine_half_width_m"]; sections = {}
    for d in np.arange(1000, eyre.length, 2000):
        p0, p1 = sm.interpolate(max(sm.project(eyre.interpolate(d)) - 60, 0)), sm.interpolate(min(sm.project(eyre.interpolate(d)) + 60, sm.length))
        tx, ty = p1.x - p0.x, p1.y - p0.y; L = np.hypot(tx, ty); lx, ly = -ty / L, tx / L; c = eyre.interpolate(d)
        sections[f"x{d / 1000:04.1f}"] = [(c.x + hw * lx, c.y + hw * ly), (c.x - hw * lx, c.y - hw * ly)]          # left bank -> right bank
    left = wet.offset_line(eyre, wcfg["bank_offset_m"]); right = wet.offset_line(eyre, -wcfg["bank_offset_m"])
    lines = {**screens, **sections, "bank_left": left, "bank_right": list(right.coords)[::-1]}                 # right bank drawn upstream: leaving = positive
    bank_km = lambda name, s: (np.asarray(s) if name == "bank_left" else right.length - np.asarray(s)) / 1000

    def fluxes(run: Run, baseline: Run | None):
        s = post.SWW(run.sww_path); pre = float(run.meta().get("pre_breach_s", 0.0))
        r = wet.Transects(s, lines, spacing=20.0).integrate(t_from=pre)
        b = wet.Transects(post.SWW(baseline.sww_path), lines, spacing=20.0).integrate(t_from=pre) if baseline is not None else None
        return s, r, b, pre

    # ---- 2. redirect -------------------------------------------------------------------------------------------
    figS, axS = plt.subplots(len(a.scenarios), len(screens), figsize=(3.2 * len(screens), 4.6 * len(a.scenarios)), squeeze=False, sharey=True)
    keep = {}
    for i, sc in enumerate(a.scenarios):
        for cond in ("dry", "wet"):
            ref = None
            for tr in ["none"] + a.trees:
                run = Run(sc, mode, f"_{cond}_trees{tr}")
                if not run.sww_path.exists():
                    continue
                bl = base(tr) if cond == "wet" else None
                s, r, b, pre = fluxes(run, bl); keep[(sc, cond, tr)] = (r, b, pre, np.asarray(s.time, float))
                prof = {}
                for nm in screens:
                    v = r["net"][nm] - (b["net"][nm] if b else 0.0); y = N - 300 - r["s"][nm]
                    bins = np.floor((y - S) / 1000).astype(int); prof[nm] = np.bincount(bins, weights=v, minlength=int((N - S) / 1000) + 1) / 1e6
                qx, qy, qm = peak_added_flow(s, post.SWW(bl.sww_path) if bl else None, pre)
                if tr == "none":
                    ref = (prof, qx, qy, qm, s)
                    for jx, nm in enumerate(screens):
                        axS[i][jx].plot(prof[nm], S / 1000 + np.arange(len(prof[nm])) + 0.5, color="k" if cond == "dry" else "#2b6cb0", lw=1.4, label=f"{cond}, no trees")
                    continue
                p0, qx0, qy0, qm0, s0 = ref
                ok = (qm > a.q_min) & (qm0 > a.q_min)
                ang = np.degrees(np.abs(np.arctan2(qx * qy0 - qy * qx0, qx * qx0 + qy * qy0)))
                shift = {nm: {"volume_Mm3_none": float(p0[nm].sum()), "volume_Mm3_trees": float(prof[nm].sum()),
                              "moved_between_km_bands_Mm3": float(np.abs(prof[nm] - p0[nm]).sum() / 2),
                              "centroid_shift_north_m": float(1000 * (np.average(np.arange(len(prof[nm])), weights=np.maximum(prof[nm], 1e-9))
                                                                       - np.average(np.arange(len(p0[nm])), weights=np.maximum(p0[nm], 1e-9))))} for nm in screens}
                res["redirect"][f"{sc}_{cond}_trees{tr}"] = {
                    "direction_change_deg_percentiles_50_90_99": [float(v) for v in np.percentile(ang[ok], [50, 90, 99])],
                    "share_of_flow_points_turned_more_than_20deg": float((ang[ok] > 20).mean()), "share_turned_more_than_45deg": float((ang[ok] > 45).mean()),
                    "peak_unit_flow_ratio_percentiles_5_50_95": [float(v) for v in np.percentile(qm[ok] / qm0[ok], [5, 50, 95])], "screen_lines": shift}
                if tr == a.trees[0]:
                    for jx, nm in enumerate(screens):
                        axS[i][jx].plot(prof[nm], S / 1000 + np.arange(len(prof[nm])) + 0.5, color="k" if cond == "dry" else "#2b6cb0", lw=1, ls="--", label=f"{cond}, trees n=0.{tr[1:]}")
                    if cond == "wet":
                        figD, axD = plt.subplots(figsize=(15, 7)); m = np.where(ok, ang, np.nan)
                        g, trf = s.grid(m, bbox, 40.0); im = axD.imshow(g, extent=[W, E, S, N], cmap="magma_r", vmin=0, vmax=60); plt.colorbar(im, ax=axD, shrink=0.7, label="degrees")
                        axD.plot(*eyre.xy, color="#2b6cb0", lw=0.8); axD.add_patch(plt.Polygon(site["site"]["footprint_nztm"], fc="0.7", ec="k"))
                        axD.set_title(f"{sc}, wet plain: change in direction of the breach-added flow at its peak, shelterbelts n=0.{tr[1:]} vs none – exploratory screening, not a certified assessment", fontsize=9)
                        figD.tight_layout(); figD.savefig(out / f"wet_direction_{sc}_{mode}.png", dpi=110); plt.close(figD)
        for jx, nm in enumerate(screens):
            axS[i][jx].set_title(f"{sc}: through E {nm[1:]} km", fontsize=8); axS[i][jx].tick_params(labelsize=6); axS[i][jx].set_xlabel("Mm³ per km of northing", fontsize=7)
        axS[i][0].set_ylabel("northing (km)", fontsize=8); axS[i][0].legend(fontsize=6)
    figS.suptitle("Where the breach water goes: breach-added volume flowing east through north-south screen lines – exploratory screening, not a certified assessment", fontsize=9)
    figS.tight_layout(); figS.savefig(out / f"wet_screenlines_{mode}.png", dpi=110); plt.close(figS)

    # ---- 3. the Eyre River: what the breach adds -------------------------------------------------------------------
    def eyre_stats(r, b, pre, t, run: Run, baseline: Run):
        km = np.array([float(k[1:]) for k in sections]); tb = t >= pre
        Qr = np.array([r["Q"][k][tb].max() for k in sections]); Qb = np.array([b["Q"][k][tb].max() for k in sections])
        dQ = np.array([(r["Q"][k][tb] - b["Q"][k][tb]).max() for k in sections])
        dV = np.array([getattr(np, "trapezoid", getattr(np, "trapz", None))((r["Q"][k] - b["Q"][k])[tb], t[tb]) for k in sections]) / 1e6
        o = {"section_km": km.tolist(), "peak_Q_no_breach_m3s": Qb.round(1).tolist(), "peak_Q_with_breach_m3s": Qr.round(1).tolist(),
             "max_breach_added_Q_m3s": dQ.round(1).tolist(), "breach_added_volume_Mm3": dV.round(3).tolist()}
        for nm in ("bank_left", "bank_right"):
            k_ = bank_km(nm, r["s"][nm]); bins = np.floor(k_).astype(int); nb = int(np.ceil(eyre.length / 1000)) + 1
            vr = np.bincount(bins, weights=r["out"][nm], minlength=nb) / 1e6; vb = np.bincount(bins, weights=b["out"][nm], minlength=nb) / 1e6
            o[nm] = {"leaving_no_breach_Mm3_per_km": vb.round(3).tolist(), "leaving_with_breach_Mm3_per_km": vr.round(3).tolist(),
                     "total_no_breach_Mm3": float(vb.sum()), "total_with_breach_Mm3": float(vr.sum()),
                     "km_where_breach_adds_more_than_0.05_Mm3": [int(x) for x in np.where(vr - vb > 0.05)[0]],
                     "km_spilling_only_with_breach": [int(x) for x in np.where((vr > 0.05) & (vb < 0.01))[0]]}
        Dr, ext, _ = run.tif("max_depth"); Db = baseline.tif("max_depth")[0]; Wd, Ed, Sd, Nd = ext; resd = (Ed - Wd) / Dr.shape[1]
        ch = np.arange(0, eyre.length, 100.0); rise = []
        for d in ch:
            p = eyre.interpolate(d); ii, jj = int((Nd - p.y) / resd), int((p.x - Wd) / resd); w = int(150 / resd)
            sl = (slice(max(ii - w, 0), ii + w + 1), slice(max(jj - w, 0), jj + w + 1))
            rise.append(float(np.nanmax(np.nan_to_num(Dr[sl]) - np.nan_to_num(Db[sl]))))
        rise = np.array(rise); hit = np.where(rise > thr)[0]
        o["flood_level_rise_in_river_m"] = {"chainage_km": (ch / 1000).round(1).tolist(), "rise_m": rise.round(2).tolist(), "max_m": float(rise.max()),
                                            "first_km_reached_by_breach_water": float(ch[hit[0]] / 1000) if len(hit) else None,
                                            "km_of_river_raised_more_than_0.1m": float(len(hit) * 0.1)}
        return o

    figE, axE = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    for sc, col in zip(a.scenarios, ("#c05621", "#6b46c1")):
        for extra, label in (("", ""), ("_q2", " (Eyre flood doubled)"), ("_races", " (+ race dewatering flow)")):
            tr = "none" if (sc, "wet", "none") in keep and not extra else a.trees[0]
            run = Run(sc, mode, f"_wet{extra}_trees{tr}"); bl = base(tr, extra)
            if not (run.ok() and bl.ok()):
                continue
            if extra or (sc, "wet", tr) not in keep:
                s, r, b, pre = fluxes(run, bl); t = np.asarray(s.time, float)
            else:
                r, b, pre, t = keep[(sc, "wet", tr)]
            st = eyre_stats(r, b, pre, t, run, bl); st["trees"] = tr
            if extra and (sc, "wet", tr) in keep:   # the changed inflow itself: storm-only river, this inflow vs the plain one (same trees)
                b0 = keep[(sc, "wet", tr)][1]; tb = t >= 0
                st["storm_only_vs_plain_inflow"] = {
                    "peak_Q_plain_m3s": [round(float(b0["Q"][k].max()), 1) for k in sections], "peak_Q_this_m3s": [round(float(b["Q"][k].max()), 1) for k in sections],
                    "final_Q_plain_m3s": [round(float(b0["Q"][k][-1]), 1) for k in sections], "final_Q_this_m3s": [round(float(b["Q"][k][-1]), 1) for k in sections],
                    **{f"{nm}_leaving_Mm3_plain_vs_this": [round(float(b0["out"][nm].sum() / 1e6), 2), round(float(b["out"][nm].sum() / 1e6), 2)] for nm in ("bank_left", "bank_right")}}
                Db0 = base(tr).tif("max_depth")[0]; Db1 = bl.tif("max_depth")[0]; dd = np.nan_to_num(Db1) - np.nan_to_num(Db0)
                st["storm_only_vs_plain_inflow"]["area_deeper_by_0.1m_km2"] = float((dd > 0.1).sum() * 100 / 1e6)
                st["storm_only_vs_plain_inflow"]["area_newly_wet_km2"] = float(((np.nan_to_num(Db1) > thr) & ~(np.nan_to_num(Db0) > thr)).sum() * 100 / 1e6)
                st["storm_only_vs_plain_inflow"]["max_rise_m"] = float(np.nanmax(dd))
            (res["inflows"] if extra else res["eyre"])[f"{sc}{extra}"] = st
            if not extra:
                axE[0].plot(st["section_km"], st["peak_Q_with_breach_m3s"], "o-", color=col, label=f"{sc}: with breach")
                axE[0].plot(st["section_km"], st["peak_Q_no_breach_m3s"], "o:", color="0.4", label="storm only" if sc == a.scenarios[0] else None)
                x = np.arange(len(st["bank_left"]["leaving_with_breach_Mm3_per_km"])) + 0.5
                axE[1].step(x, np.array(st["bank_left"]["leaving_with_breach_Mm3_per_km"]) - np.array(st["bank_left"]["leaving_no_breach_Mm3_per_km"]), where="mid", color=col, label=f"{sc}: left (north-east) bank")
                axE[1].step(x, -(np.array(st["bank_right"]["leaving_with_breach_Mm3_per_km"]) - np.array(st["bank_right"]["leaving_no_breach_Mm3_per_km"])), where="mid", color=col, ls="--", label=f"{sc}: right (south-west) bank, plotted downwards")
                axE[2].plot(st["flood_level_rise_in_river_m"]["chainage_km"], st["flood_level_rise_in_river_m"]["rise_m"], color=col, label=sc)
    axE[0].set_ylabel("peak discharge in the river corridor (m³/s)"); axE[0].legend(fontsize=7)
    axE[1].set_ylabel("breach-added water leaving over the bank\n(Mm³ per km; negative = less leaves)"); axE[1].axhline(0, color="k", lw=0.5); axE[1].legend(fontsize=7)
    axE[2].set_ylabel("rise of the peak flood level\nwithin 150 m of the centreline (m)"); axE[2].set_xlabel("distance along the Eyre from the north edge of the domain (km)"); axE[2].legend(fontsize=7)
    figE.suptitle("Eyre River already in flood: what the breach adds – exploratory screening, not a certified assessment", fontsize=10)
    figE.tight_layout(); figE.savefig(out / f"wet_eyre_{mode}.png", dpi=120); plt.close(figE)

    (out / f"wet_compare_{mode}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k in ("delay",)}, indent=1))
    print(f"[wet] wrote {out}/wet_compare_{mode}.json and figures")


if __name__ == "__main__":
    main()
