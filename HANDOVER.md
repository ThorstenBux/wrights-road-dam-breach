# Handover – Wrights Road Storage Ponds dam-breach flood model

*Key numbers and every result map: [RESULTS.md](RESULTS.md).*

*Tripod Digital, 15 September 2026. Everything below was produced in one working session; treat all numbers as
screening-level (see SPEC.md §1.3). A Recognised Engineer must own anything that feeds the certified
Potential Impact Classification under the Building (Dam Safety) Regulations 2022.*

## Live animations (GitHub Pages)

* East embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* West embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/west/
* Index: https://thorstenbux.github.io/wrights-road-dam-breach/

Controls: drag to orbit, scroll to zoom (down to 30 m), shift-drag to pan, space to play/pause; buttons
Re-centre / Breach / Street level; sliders for terrain and flood vertical scale; checkbox to colour the water by
flow speed (m/s) instead of depth. Building colour: amber > 0.1 m, red ≥ 0.5 m at the footprint.

## 1. What was asked

"For the Wrights Road Dam in West Eyreton we need flood modelling with flow rate and water level in case of a
breach." Deliverables: breach outflow hydrographs, inundation depth/velocity/arrival maps, road and building
impacts, a reproducible pipeline, and an interactive 3D animation.

## 2. What was done

1. **Sources reviewed** (all public, links in `docs/source-notes.md`): Damwatch Design Report Issue 6 (Oct 2021),
   WIL Emergency Action Plan Issue 6 (Jun 2020), WIL Emergency Evacuation Plan draft v7.2 (Jun 2020), NZSOLD Dam
   Safety Guidelines 2024 Module 2, Building (Dam Safety) Regulations 2022, BHSL/WIL project pages.
2. **Site located**: EAP gives NZTM 1,534,683 E / 5,196,928 N; the road grid (Wrights Rd bearing ~196°, Dixon Rd
   ~287°, corner at 1,535,375 / 5,197,371) gives a 1.075 km rotated square whose centroid is within 65 m of the
   EAP point. Footprint is approximate until drawing WIL1125/30/2 is obtained.
3. **Data acquired without any API key**: LINZ Canterbury 1 m LiDAR DEM 2020–2025 (open AWS bucket
   `nz-elevation`, NZVD2016), Waimakariri 2023 tiles; OpenStreetMap roads/buildings/water for a 27 × 16 km domain.
4. **Breach model** (`damflood/breach.py`): Froehlich (2008) width/side-slope/formation time, Froehlich (1995)
   peak check, level-pool routing through a growing trapezoidal weir, Pond 1 → Pond 2 cascade. Unit-tested.
5. **2D routing** (`damflood/model.py`): ANUGA 4.0 on a 165k-triangle mesh over the 18 × 11.5 km shakedown
   domain at 20 m; hydrograph injected at the embankment toe; ponds burned into the DEM as a block at crest level.
6. **Post-processing** (`damflood/post.py`): max depth / speed / depth×speed / hazard class (ARR H1–H6) /
   arrival-time GeoTIFFs; road arrival table; building and PAR screening; maps with road names; comparison
   with the Damwatch 2016 arrival table.
7. **3D viewer** (`webgl/index.html` + `scripts/07_export_webgl.py`): Three.js; LiDAR terrain; animated water
   surface (depth or flow-speed colouring); road names; OSM buildings extruded to footprint (5 m houses, 6.5 m
   large sheds, 4 m small sheds) coloured amber > 0.1 m and red ≥ 0.5 m; 1.8 m figures; hydrograph scrubber;
   Re-centre / Breach / Street-level views (street level = true vertical scale, jumps to the wave's arrival).

## 3. What was found

| Scenario | Breach invert (LiDAR toe) | Peak outflow | Volume released | Wet area (4 h) | Buildings ≥ 0.5 m | PAR screening | Damwatch 2012 PAR |
|---|---|---|---|---|---|---|---|
| East (Pond 1 → Pond 2 cascade, overtopping) | 210.8 m | **2,100 m³/s** | 7.2 Mm³ | 39.5 km² | 95 | ~235 | 107 |
| South (cascade) | 215.4 m | 1,070 m³/s | 5.3 Mm³ | not run in 2D | | | 54 |
| North (cascade) | 216.7 m | 820 m³/s | 4.7 Mm³ | not run in 2D | | | 95 |
| West (Pond 1 piping only) | 221.9 m | 235 m³/s | 1.2 Mm³ | 6.0 km² | 2 | 5 | 4 |

* The east peak is within 20 % of Damwatch's "approximately 2,500 m³/s". The ordering E > S > N > W follows the
  ground level at the toe (211 m on the Wrights Road side vs 222 m on the MR4 side), now quantified from LiDAR.
* Modelled arrival at each road is ~45 min earlier and generally deeper than the Damwatch 2016 table
  (Carleton 0.77 h vs 1.5 h … Downs 3.33 h vs 4.17 h). Expected direction for uniform roughness (n = 0.045),
  a 20 m grid that smooths road and race embankments, and a 1.1 h breach formation. These are the calibration
  levers for phase 1.
* **Cascade caveat**: with the report's volumes/areas, Pond 1 draining into Pond 2 statically equalises ~0.5 m
  *below* the Pond 2 crest. The overtopping cascade Damwatch describes therefore depends on dynamic surge or a
  different stage–storage shape; the model initiates the Pond 2 breach at 223.6 m RL (config
  `cascade.pond2_trigger_mRL`). Reconcile with Appendix H.
* The flood is channelled along the WIL Main Race embankment east of Carleton Road – a feature worth
  representing explicitly (culverts, breaches of the race) in production runs.

## 4. How to run

```bash
conda env create -f environment.yml && conda activate damflood
make test                      # breach routing unit tests
make dem                       # LiDAR DEM, shakedown domain (20 m)   [python scripts/01_fetch_dem.py --full for 10 m]
make vectors                   # OSM roads / buildings / water
make breach SCENARIO=east      # hydrograph -> outputs/east/hydrograph.csv|png, breach_summary.json
make run SCENARIO=east         # ANUGA 2D (shakedown ~85 min on one core; add --production for 10 m / 14 h)
make post SCENARIO=east        # rasters, roads.csv, buildings.csv, map PNG
make compare SCENARIO=east     # vs Damwatch 2016 arrival table
python scripts/07_export_webgl.py --scenario east --cell 60     # viewer data -> outputs/east/webgl/data.js
```
Serve the viewer locally with `python -m http.server 8765 --directory outputs/east/webgl` (a plain `file://`
open will not load `data.js`). Sensitivities: `03_breach_hydrograph.py --width-factor 2 --time-factor 0.5
--scour 1 --trigger 224.0 --tag _wide`; `04_run_model.py --manning 0.06 --tag _n06`.

## 5. Repository layout

```
SPEC.md                 specification, method, scenarios, results, open questions
HANDOVER.md             this file
docs/source-notes.md    sourced facts with page references
config/site.yaml        site geometry, domain, data sources, mesh/run settings
config/dam.yaml         dam parameters (sourced), scenarios, breach defaults, friction, consequence rules
damflood/               breach.py terrain.py vectors.py model.py post.py config.py
scripts/01..07          pipeline steps
tests/test_breach.py    unit tests
webgl/index.html        3D viewer (needs data.js beside it)
docs/east, docs/west    GitHub Pages deployment of the viewer (data.js committed, ~10–20 MB each)
outputs/<scenario>/     small results are committed (csv, json, png); .sww and GeoTIFFs are not (regenerate)
data/                   not committed (downloaded by scripts 01/02)
```

## 6. Open items (client)

1. Drawings WIL1125/30/2, 21–23, 101–119; stage–storage curves; crest width; dividing-embankment position.
2. Datum of the design RLs vs NZVD2016 (LiDAR).
3. Damwatch Appendix H (breach parameters, software, maps) and the 2016 Flood Hazard Update.
4. LINZ Data Service API key (building outlines, road centrelines, parcels) and LRIS account (LCDB roughness).
5. Purpose: independent check / community visualisation / input to the certified PIC and DSAP.
6. Compute for production: Mac (hours per run) or Linux with MPI.

## 7. Known limitations of the shakedown

20 m grid, ≥ 1,500 m² triangles, uniform roughness, no culvert/bridge/race-structure assumptions, approximate
footprint and breach positions, buildings not in the terrain, depth at building centroid rather than surveyed
floor level, 4 h horizon on an 18 km domain (Browns Road onward not reached), south/north scenarios not routed.
