# wrights-road-dam-breach – agent notes

Read `HANDOVER.md` first (what/why/how), then `SPEC.md` (method, assumptions, open questions) and
`RESULTS.md` (numbers and maps). `docs/source-notes.md` has every sourced dam fact with page references;
`docs/clg-notes.md` holds points for the Community Liaison Group and the assumption register (keep it current).

* Env: `source /opt/miniconda3/etc/profile.d/conda.sh && conda activate damflood` (or `make env`).
* Tests: `make test`. Pipeline: `make dem vectors breach run post compare SCENARIO=east`.
* Config is the single source of dam parameters: `config/dam.yaml` (sourced, with page refs) and
  `config/site.yaml` (geometry, domain, mesh, run settings). Change parameters there, not in code.
* Site footprint and breach positions are APPROXIMATE (road-grid reconstruction); replace with drawing
  WIL1125/30/2 when available and say so in SPEC §2.
* The cascade trigger `cascade.pond2_trigger_mRL` (223.6) is the most consequential assumption – see SPEC §3.1.
* Viewer: edit `webgl/index.html`, then copy to every `docs/<scenario>/` (east, west, quake, storm; data.js stays) and push;
  Pages rebuilds from `docs/` on `main`. Regenerate data with `scripts/07_export_webgl.py --scenario <s> --cell 60`.
* Production runs: `01_fetch_dem.py --full`, then `--production` on scripts 04/05/06/07 (10 m, 14 h; hours per run).
* Scenarios with a `breaches:` list (the `quake` earthquake case) use `route_multi`/`cascade_multi` and one ANUGA
  inlet per external breach; `hydrograph.csv` is the sum, `hydrograph_<breach>.csv` the parts. Keep east/west untouched.
* Scenarios with a `hydrology:` block (the `storm` rainy-day case) add uniform rain and river inlets in script 04 and a
  `pre_breach_h` spin-up; all reported times are relative to the breach opening (post.maxima `t_breach`).
* Viewer debris (logs/fences/cars/trees/sheds) is purely illustrative: objects mobilise on depth/speed thresholds
  and drift down the water-surface gradient at the local speed; no debris data is exported or modelled in ANUGA.
* Everything is a screening model; keep the "not a certified assessment" wording in any new output.
