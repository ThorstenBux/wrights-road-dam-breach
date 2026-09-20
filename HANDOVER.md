# Handover – Wrights Road Storage Ponds dam-breach flood model

*Key numbers and every result map: [RESULTS.md](RESULTS.md).*

*Tripod Digital, 15 September 2026. Everything below was produced in one working session; treat all numbers as
screening-level (see SPEC.md §1.3). A Recognised Engineer must own anything that feeds the certified
Potential Impact Classification under the Building (Dam Safety) Regulations 2022.*

## Live animations (GitHub Pages)

* East embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* East breach routed to Diversion Road: https://thorstenbux.github.io/wrights-road-dam-breach/east-extended/
* North embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/north/
* North breach routed to Diversion Road: https://thorstenbux.github.io/wrights-road-dam-breach/north-extended/
* West embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/west/
* Earthquake, all embankments at once (postulated seismic failure): https://thorstenbux.github.io/wrights-road-dam-breach/quake/
* Storm, east breach during 10 mm/h rain with the Eyre River in flood (rainy-day combination): https://thorstenbux.github.io/wrights-road-dam-breach/storm/
* Index: https://thorstenbux.github.io/wrights-road-dam-breach/
* Exploratory race / dewatering / shelterbelt runs (six viewers under `docs/exploratory/`, linked from the index below Storm):
  see §8.

Controls: drag to orbit, scroll to zoom (down to 30 m), shift-drag to pan, space to play/pause; the description panel (key I) and the legend with the scale sliders (key L) can be minimised; buttons
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
| North (cascade) | 216.7 m | 820 m³/s | 4.7 Mm³ | 20.4 (4 h) / 49.4 (12 h, full domain) | 17 / 30 | ~43 / ~75 | 95 |
| West (Pond 1 piping only) | 221.9 m | 235 m³/s | 1.2 Mm³ | 6.0 km² | 2 | 5 | 4 |
| Earthquake (all embankments at once, postulated) | 210.8–221.9 m | 3,000 m³/s combined | 7.4 Mm³ | 43.4 km² | 87 | ~218 | – |
| Storm (east breach + 10 mm/h rain + Eyre River 150 m³/s) | 210.8 m | 2,100 m³/s | 7.2 Mm³ + rain/river | 56.6 total / 43.4 added by breach | 113 total / 75 added | ~283 | – |

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
7. Water races and dewatering (see §8): WIL to confirm which mapped race is MR4 / R2 / R3, whether MR4 and R3 are built
   as the EAP describes, as-built gate and race capacities, the culvert inventory (size, invert) and how Pond 2's
   dewatering flow is split between R2 and R3. Official information requests for the EAP Appendix F.6 dewatering
   inundation maps (ECan, WDC, Canterbury CDEM) were handed to a separate session – look for
   `docs/eap-appendix-f-information-requests.md` on its branch.

## 7. Known limitations of the shakedown

20 m grid, ≥ 1,500 m² triangles, uniform roughness, no culvert/bridge/race-structure assumptions, approximate
footprint and breach positions, buildings not in the terrain, depth at building centroid rather than surveyed
floor level, 4 h horizon on an 18 km domain (Browns Road onward not reached), south scenario not routed.
The east scenario has since been re-run on the full domain to Diversion Road (`--mode extended`, 12 h, still 20 m):
see RESULTS §2b; the north scenario has been routed both ways (4 h shakedown and 12 h extended, RESULTS §2c) and
reaches Diversion Road ~4 h later than the Damwatch 2016 table – the opposite bias to the east run, see §2c for the
likely reasons. The 20 m grid / uniform roughness limitations still apply. The east extended run took 12 h
wall-clock on a heavily loaded machine (expect ~4–6 h on an idle core); the north runs took minutes because the
wet area stays small; west/quake/storm remain shakedown-only.

## 8. Exploratory work – dewatering, water races, tree shelterbelts (19–20 Sep 2026)

**Status: exploratory and deliberately separate.** Thorsten asked to keep this apart from the pipeline until a benefit is
shown. Nothing in scripts 01–10, `config/dam.yaml`, `config/site.yaml`, `webgl/index.html`, `RESULTS.md` or the published
scenario viewers was changed; everything lives in new files. Screening model, not a certified assessment. Full write-ups:
[docs/dewatering-drawdown-sensitivity.md](docs/dewatering-drawdown-sensitivity.md) and
[docs/races-and-shelterbelts-2d.md](docs/races-and-shelterbelts-2d.md).

### 8.1 Questions and answers

| Question | Answer (screening level) |
|---|---|
| Does dewatering for some hours before the breach reduce the flood? | Hardly, if the ponds still fail: at the EAP example rates (5 + 15 m³/s) 6 h removes 0.43 Mm³ of 8.2 Mm³; east peak 2,098 → 1,973 m³/s (−6 %), 12 h −12 %, 24 h −24 %; timing unchanged. With a FIXED 223.6 m cascade trigger instead, 3–8 h of dewatering would stop Pond 2 failing at all – that alternative rides entirely on the trigger assumption (A4) and is kept behind `--fixed-trigger`. Working assumption agreed with Thorsten: the ponds still fail, at a correspondingly lower level. |
| Do the races carry the dewatering flow? (the unpublished EAP App. F.6 case) | Culverts open: MR4 (5 m³/s) yes, reaches the domain edge towards the Eyre in 3.4 h; R2 (10 m³/s) yes, easily (bank-full ~48 m³/s); R3 = the Dixon Road drain (5 m³/s) NO – bank-full ~4–6 m³/s, spills along Dixon Road, front stalls ~5.9 km down. Every culvert blocked: MR4 stalls 1.7 km from the ponds (only 4 m fall in 5.6 km); R2 overtops its crossings and still gets through; ~0.2 km² wet outside the races, ≤ 0.7 m. |
| Does it matter for the breach flood that the races are already full? | No. 20 m³/s is 1 % of the breach peak: flooded area 26.3 vs 26.0 km², depths +0–2 cm, arrivals within one 5-min output step. |
| What do the > 10 m shelterbelts do? | Nothing for the first ~8 km (few belts near the ponds – pivot irrigation), then a growing delay: on the full domain 15 / 28 / 39 min later at Diversion Road for n = 0.12 / 0.20 / 0.30 under trees (7.58 → 7.83 / 8.04 / 8.23 h; Damwatch 9.0 h), +0.1–0.4 m behind dense belts (Downs Road 1.17 → 1.34–1.59 m), flooded area unchanged. Closes 20–45 % of the far-field gap to Damwatch, none of the near-field gap (Carleton–Poyntzs Roads). |

Recommendation given to Thorsten: bring the **shelterbelts** into the main model as an optional friction layer; keep
**dewatering down the races** as its own small scenario (it answers EAP F.6); leave the races out of the breach scenarios.
Not yet decided by him.

### 8.2 What was built (all new files)

| File | Purpose |
|---|---|
| `config/dewatering.yaml`, `damflood/dewater.py`, `scripts/11_dewatering_sensitivity.py` | Level-pool sensitivity: drawdown for 0–24 h, then the scenario's breach routed exactly as script 03 (0 h reproduces the published east hydrograph – tested). `--write-hydrograph 6` exports the breach hydrograph used by the 2D race runs. Outputs `outputs/dewatering/<scenario>/`. |
| `config/races.yaml`, `damflood/races.py`, `scripts/12_run_races.py` | Near-field 2D domain (14 × 9.5 km, 2 m DEM) with MR4 / R2 / R3 in the mesh. Cases `dewater`, `dewater_breach`, `breach_dry`; `--crossings open|blocked`; `--shelterbelts`. Outputs `outputs/races/`. 25–55 min per run. |
| `scripts/13_races_compare.py` | Long sections and spill map for dewatering-only; pairwise difference maps / road tables (full vs dry races, trees vs none). |
| `damflood/shelterbelts.py`, `scripts/15_canopy_fraction.py`, `scripts/16_run_shelterbelts.py`, `scripts/17_shelterbelts_compare.py` | Trees = LINZ 1 m DSM − DEM ≥ 6 m (buildings, wires, single trees removed); equivalent n per triangle (n² area-weighted). Script 16 repeats a standard scenario run with trees, tagged `_treesnone|_trees012|_trees020|_trees030`, so scripts 05/06 work with `--tag`. Summary in `outputs/east/shelterbelts_extended.{csv,png,json}`. |
| `scripts/14_export_races_webgl.py` | Animated 3D views: a patched COPY of `webgl/index.html` (race lines, tree blocks) + data.js. `--docs` writes `docs/exploratory/<run>/`; without it `outputs/races/viewer/<run>/` (preview: `races-viewer` in `.claude/launch.json`). |
| `tests/test_dewater.py`, `tests/test_races.py`, `tests/test_shelterbelts.py` | 22 tests in total with the existing ones; `make test`. |

Reproduce: `python scripts/11_dewatering_sensitivity.py --scenario east --write-hydrograph 6`; `python scripts/12_run_races.py
--case dewater|dewater_breach|breach_dry [--crossings blocked] [--shelterbelts]`; `python scripts/13_races_compare.py
[--crossings blocked]`; `python scripts/15_canopy_fraction.py --mode extended`; `python scripts/16_run_shelterbelts.py --mode
extended --no-trees | --tree-n 0.20`; then `05`/`06 --mode extended --tag _trees020` and `python scripts/17_shelterbelts_compare.py
--mode extended`. Needs `data/raw/osm_domain.gpkg` and (for script 16) `data/derived/dem_full_20m.tif`; the 2 m DEM / DSM are
fetched on demand.

### 8.3 Things the next person should know (learned the hard way)

* **Races in OSM are unnamed** `stream` / `drain` ways. Our match to the EAP names is an ASSUMPTION: MR4 = the race heading north
  from the NW corner (way 809026039 onward; 8 crossings at mapped roads, the EAP says "about 8 culverts"), R2 = the race
  along the south side from Wrights Road (885343375), R3 = the Dixon Road drain (903988636). The supply race arrives from the SW.
* **The ponds are not in the LiDAR** (it pre-dates them) and the approximate footprint's south edge lies on the R2 race, so the
  race chains start just outside the footprint corners.
* **LiDAR race beds are water surfaces** (no penetration): capacities are under-estimated, R2 has visible drop structures.
* **Mesh representation**: a single centre-line breakline chokes a small race (every channel triangle gets a bank vertex, the
  centroid bed rises by 1/3–2/3 of the bank height; MR4 moved 0.6 km in 6 h). Use the two bed-edge lines
  (`Thalweg.bed_edges`). ANUGA takes breaklines in ABSOLUTE coordinates (it adds them without the geo-reference), and interior
  refinement regions crossed by breaklines leave pockets with no area limit – the race domain uses a uniform 3,000 m² instead.
* **Culverts** are either open cuts through the fill or fully blocked (LiDAR surface); no capacity-limited culverts yet
  (`anuga.Boyd_box_operator` would be the next step once sizes are known). Blocked mode must not let the bed burn reach into
  the fill (fixed; covered by a test).
* **R2's OSM chain ends inside the domain** – the spill at its end is a mapping artefact, not a finding.
* **Arrival times resolve to the 5-min output step**; stripes in the arrival-difference maps are that, not physics.
* **Extended mesh count**: `--mode extended` builds ~201,000 triangles today, the published east-extended run had ~272,000
  (config changed since). Script 16 therefore has `--no-trees` for a baseline on the identical mesh; it gives 7.58 h to
  Diversion Road vs 7.5 h published. These extended runs took ~15 min each on an idle machine, not hours.
* **Tree roughness is the mild end**: n = 0.20 under canopy, area-weighted per triangle; trunks + fences + debris acting as a
  porous wall are not modelled. Canopy: 15.7 km² = 3.1 % of the full domain, median height 12.5 m (near field: 13.8 m).
* **Pipeline inconsistency noticed, not changed**: routed without tailwater, Pond 2 would reach 224.16 m RL unbreached, not the
  ~223.8 m static-equalisation level quoted in `config/dam.yaml` – relevant to how robust the 223.6 m trigger (A4) looks.
* Viewer data for the six exploratory runs is 127 MB under `docs/exploratory/` (same order as the existing viewers).

### 8.4 State and next steps

* Merged to `main` on 20 Sep 2026 (PR #8, branch `claude/tree-shelters-water-races-a8b3c5`); the exploratory section on the index
  page and the six viewers under https://thorstenbux.github.io/wrights-road-dam-breach/exploratory/ are live.
* Next, in order of value: (1) decide whether shelterbelts go into the main model – if so add the canopy friction as an option of
  script 04 / `model.build_domain`, re-run the scenarios, update RESULTS / SPEC §3.2 / A6; (2) tree-block animation for the
  full-domain runs (generalise script 14 to standard scenario runs); (3) a debris-blockage upper bound for belts across the flow
  (low sill or n ≈ 0.3+ on refined strips); (4) the dewatering scenario with WIL's race / culvert data and the R2/R3 split, plus
  the 1 % AEP Eyre coincidence case of EAP F.6; (5) follow up the official information requests.

