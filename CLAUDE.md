# wrights-road-dam-breach – agent notes

Read `HANDOVER.md` first (what/why/how), then `SPEC.md` (method, assumptions, open questions) and
`RESULTS.md` (numbers and maps). `docs/source-notes.md` has every sourced dam fact with page references;
`docs/clg-notes.md` holds points for the Community Liaison Group and the assumption register (keep it current).
`docs/dewatering-pathway-evidence.md` is the evidence note on emergency dewatering via the races to the Eyre River.

* Env: `source /opt/miniconda3/etc/profile.d/conda.sh && conda activate damflood` (or `make env`).
* Tests: `make test`. Pipeline: `make dem vectors breach run post compare SCENARIO=east`.
* Config is the single source of dam parameters: `config/dam.yaml` (sourced, with page refs) and
  `config/site.yaml` (geometry, domain, mesh, run settings). Change parameters there, not in code.
* Site footprint and breach positions are APPROXIMATE (road-grid reconstruction); replace with drawing
  WIL1125/30/2 when available and say so in SPEC §2.
* The cascade trigger `cascade.pond2_trigger_mRL` (223.6) is the most consequential assumption – see SPEC §3.1.
* Viewer: edit `webgl/index.html`, then copy to every `docs/<scenario>/` (east, east-extended, west, quake, storm; data.js stays) and push;
  Pages rebuilds from `docs/` on `main`. Regenerate data with `scripts/07_export_webgl.py --scenario <s> --cell 60`.
* Model tiers: `--mode shakedown|extended|production` on scripts 01/04–08 (`config.mode_settings`). `extended` = the full
  domain to Diversion Road at 20 m with the shakedown mesh (~270k triangles, 12 h); outputs carry the `_extended` suffix.
  `--production`/`--full` are aliases for the 10 m tier (14 h; hours per run).
* Scenarios with a `breaches:` list (the `quake` earthquake case) use `route_multi`/`cascade_multi` and one ANUGA
  inlet per external breach; `hydrograph.csv` is the sum, `hydrograph_<breach>.csv` the parts. Keep east/west untouched.
* Scenarios with a `hydrology:` block (the `storm` rainy-day case) add uniform rain and river inlets in script 04 and a
  `pre_breach_h` spin-up; all reported times are relative to the breach opening (post.maxima `t_breach`).
* Everything is a screening model; keep the "not a certified assessment" wording in any new output.
