# Results – Wrights Road Storage Ponds dam-breach model (shakedown, 15 Sep 2026)

Screening-level results. Method, assumptions and caveats: [SPEC.md](SPEC.md) §3 and §7.3; sources: [docs/source-notes.md](docs/source-notes.md). Time zero for all 2D results is the moment the external (downstream) breach opens; for cascade scenarios that is 2.2 h after the Pond 1 failure begins.

## 1. Breach outflow (all four scenarios)

| Scenario | Mechanism | Breach invert (LiDAR toe, m NZVD2016) | Peak outflow (m³/s) | Time to peak (h) | Volume released (Mm³) | Froehlich 1995 check (m³/s) |
|---|---|---|---|---|---|---|
| east | Pond 1 → Pond 2 cascade, overtopping | 210.8 | **2,098** | 1.1 | 7.18 | 1,484 |
| south | Pond 1 → Pond 2 cascade, overtopping | 215.4 | **1,066** | 1.5 | 5.34 | 777 |
| north | Pond 1 → Pond 2 cascade, overtopping | 216.7 | **817** | 1.7 | 4.68 | 600 |
| west | Pond 1 piping | 221.9 | **235** | 1.4 | 1.24 | 256 |

Damwatch (design report s3): "approximately 2,500 m³/s" for the type of breach analysed.

![east hydrograph](outputs/east/hydrograph.png)

![south hydrograph](outputs/south/hydrograph.png)

![north hydrograph](outputs/north/hydrograph.png)

![west hydrograph](outputs/west/hydrograph.png)

## 2. 2D flood routing (east and west, 4 h, 20 m grid)

| Metric | East | West | Damwatch 2012 (E / W) |
|---|---|---|---|
| Inundated area > 0.1 m (km²) | 39.47 | 5.99 | flood zone 73 / 15 |
| Deepest water (m) | 2.9 | 1.7 | – |
| Fastest flow (m/s) | 5.5 | 1.8 | – |
| Buildings > 0.1 m / ≥ 0.5 m | 439 / 95 | 45 / 2 | households in zone 176 / at risk 40 ; 50 / 1 |
| PAR screening (2.5 persons per at-risk building) | 238 | 5 | 107 / 4 |

### Road arrival times – east breach vs Damwatch 2016 (WIL Evacuation Plan Table 1)

| Road | Damwatch arrival (h) | Model arrival (h) | Damwatch depth (m) | Model max depth (m) |
|---|---|---|---|---|
| Carleton Road | 1.50 | 0.77 | 0.68 | 1.00 |
| Wolffs Road | 2.08 | 1.33 | 0.33 | 0.94 |
| Poyntzs Road | 2.67 | 1.90 | 0.34 | 0.75 |
| Pesters Road | 3.00 | 2.27 | 0.57 | 0.51 |
| Downs Road | 4.17 | 3.33 | 0.3 | 1.18 |
| Browns Road | 5.25 | not reached in 4 h | 0.58 | 0.00 |
| Two Chain Road | 7.33 | not reached in 4 h | 0.46 | 0.00 |
| Diversion Road | 9.00 | not reached in 4 h | <0.1 | not reached in 4 h |

The model reaches each road ~45 min earlier and generally deeper than the 2016 study – the expected direction for uniform roughness (n = 0.045), a 20 m grid that smooths road/race embankments, and a 1.1 h breach formation. These are the phase-1 calibration levers.

### Roads reached – west breach

| Road | First arrival (h) | Max depth (m) |
|---|---|---|
| Carleton Road | 1.93 | 0.37 |
| Wolffs Road | 2.86 | 0.30 |
| Wrights Road | 1.13 | 0.57 |
| Dixon Road | 0.64 | 0.71 |
| Domain Road | 1.10 | 0.50 |

## 3. Maps

### East breach

**Maximum depth**

![east max_depth](outputs/east/max_depth_shakedown.png)

**Maximum flow speed**

![east max_speed](outputs/east/max_speed_shakedown.png)

**Depth × velocity**

![east max_dv](outputs/east/max_dv_shakedown.png)

**Hazard class H1–H6**

![east hazard](outputs/east/hazard_shakedown.png)

**Arrival time**

![east arrival_h](outputs/east/arrival_h_shakedown.png)

**Time of peak depth**

![east t_peak_h](outputs/east/t_peak_h_shakedown.png)

### West breach

**Maximum depth**

![west max_depth](outputs/west/max_depth_shakedown.png)

**Maximum flow speed**

![west max_speed](outputs/west/max_speed_shakedown.png)

**Depth × velocity**

![west max_dv](outputs/west/max_dv_shakedown.png)

**Hazard class H1–H6**

![west hazard](outputs/west/hazard_shakedown.png)

**Arrival time**

![west arrival_h](outputs/west/arrival_h_shakedown.png)

**Time of peak depth**

![west t_peak_h](outputs/west/t_peak_h_shakedown.png)

## 3b. Earthquake scenario – all embankments fail at once (`quake`)

Postulated seismic failure at full supply (e.g. Alpine Fault Mw ~8 or a Darfield-type Mw 7 event): the east,
south, north and west embankments and the dividing embankment all start to breach at t = 0, with Froehlich
formation times halved for erosion through cracked, slumped fill, and no warning time. Assumption list in
`config/dam.yaml: scenarios.quake`; method in SPEC §3.1 item 7. Time zero is the earthquake.

| Metric | Earthquake (all breaches) | East cascade (reference) |
|---|---|---|
| Combined peak outflow (m³/s) | **3,001** at 0.6 h (east breach alone 2,567; west 274; south 207; north 49) | 2,098 at 1.1 h |
| Volume released (Mm³) | 7.43 (east 6.04, west 0.97, south 0.38, north 0.05) | 7.18 |
| Lag from initiating event to external breach (h) | 0 | 2.2 (Pond 1 → Pond 2 filling) |
| Inundated area > 0.1 m after 4 h (km²) | 43.4 | 39.5 |
| Deepest water (m) | 3.1 | 2.9 |
| Fastest flow (m/s) | 5.9 | 5.5 |
| Buildings > 0.1 m / ≥ 0.5 m | 474 / 87 | 439 / 95 |
| PAR screening (2.5 persons per at-risk building) | 218 | 238 |

Road arrival (h after the initiating event, water > 0.1 m) and maximum depth:

| Road | Earthquake arrival | East cascade arrival (after Pond 2 breach) | East cascade arrival (after Pond 1 failure) | Quake depth (m) | East depth (m) |
|---|---|---|---|---|---|
| Carleton Road | 0.60 | 0.77 | 2.94 | 1.04 | 1.00 |
| Wolffs Road | 1.07 | 1.33 | 3.50 | 0.90 | 0.94 |
| Poyntzs Road | 1.60 | 1.90 | 4.07 | 0.72 | 0.75 |
| Pesters Road | 1.98 | 2.27 | 4.44 | 0.48 | 0.51 |
| Downs Road | 3.10 | 3.33 | 5.50 | 1.11 | 1.18 |
| Dixon Road (north) | 0.29 | – | – | 0.76 | – |
| Domain Road (north) | 0.49 | – | – | 0.51 | – |

Reading: the east breach still carries 80 % of the water because its invert is 5–6 m lower than the others,
so the downstream picture along Carleton–Downs Road resembles the east cascade, arriving 10–20 min sooner
and, measured from the initiating event, about 2.3 h sooner because there is no Pond 1 → Pond 2 stage. The
extra 4 km² of inundation and the additional buildings reached are on the Dixon Road (north), MR4 (west) and
R2 race (south) sides, which the single-breach scenarios do not touch. The number of buildings ≥ 0.5 m is
slightly lower than the east case because the same volume is spread over more directions.

![quake hydrograph](outputs/quake/hydrograph.png)

### Earthquake maps

![quake max_depth](outputs/quake/max_depth_shakedown.png)

![quake max_speed](outputs/quake/max_speed_shakedown.png)

![quake max_dv](outputs/quake/max_dv_shakedown.png)

![quake hazard](outputs/quake/hazard_shakedown.png)

![quake arrival_h](outputs/quake/arrival_h_shakedown.png)

![quake t_peak_h](outputs/quake/t_peak_h_shakedown.png)

## 3c. Storm scenario – breach during heavy rain with the Eyre River in flood (`storm`)

NZSOLD "rainy day" combination: the east cascade breach (identical hydrograph, peak 2,098 m³/s) opens after 2 h of
steady 10 mm/h rain on saturated ground (no infiltration) with the Eyre River already carrying an assumed 150 m³/s
where it enters the domain. Breach-added figures are differenced against an identical storm run without the breach,
so rain and river water are not credited to the dam. Assumptions in `config/dam.yaml: scenarios.storm` and
[docs/clg-notes.md](docs/clg-notes.md) (A9–A12); method SPEC §3.1 item 8. Time zero is the breach opening.

| Metric | Storm: everything | Storm: added by the breach | East cascade, dry (reference) |
|---|---|---|---|
| Inundated area > 0.1 m after 4 h (km²) | 56.6 | 43.4 | 39.5 |
| Deepest water (m) | 2.6 | – | 2.9 |
| Buildings > 0.1 m / ≥ 0.5 m | 608 / 113 | 477 / 75 | 439 / 95 |
| Buildings > H2 hazard | 112 | 84 | 94 |
| PAR screening (2.5 persons per at-risk building) | 283 | – | 238 |

Road arrival (h after the breach opens, first time the breach raises the depth by > 0.1 m above the storm-only run)
and maximum total depth:

| Road | Storm arrival | East arrival | Storm depth (m) | East depth (m) |
|---|---|---|---|---|
| Carleton Road | 0.77 | 0.77 | 0.99 | 1.00 |
| Wolffs Road | 1.32 | 1.33 | 1.01 | 0.94 |
| Poyntzs Road | 1.83 | 1.90 | 1.08 | 0.75 |
| Pesters Road | 2.20 | 2.27 | 0.70 | 0.51 |
| Downs Road | 3.13 | 3.33 | 1.22 | 1.18 |
| Dixon Road | 1.03 | 0.96 | 0.73 | 0.70 |

Reading: the breach wave itself is barely faster on a wet plain (0–12 min earlier at Poyntzs–Downs Road), but it
spreads over 10 % more ground and is 0.05–0.35 m deeper where it meets the Eyre River and the ponded runoff east of
Poyntzs Road, because the river channel and the drains are already full. What changes most is the total picture
people would experience: 608 buildings with water against 439, and 113 rather than 95 with 0.5 m or more, since
the storm alone already wets 40 km² of the plain in this (very heavy, saturated-ground) rainfall assumption. The
storm-only baseline run is `outputs/storm/storm_shakedown_nobreach.sww`.

Mesh note: the storm runs use a repaired mesh (95,140 triangles, no sliver triangles – see SPEC §7.3). Re-running
the east scenario on the repaired mesh changes its inundated area from 39.5 to 39.2 km², road arrivals by ≤ 2 min
and buildings ≥ 0.5 m from 95 to 92, so the published east results were left as they are.

![storm hydrograph](outputs/storm/hydrograph.png)

### Storm maps (total depth, including rain and river)

![storm max_depth](outputs/storm/max_depth_shakedown.png)

![storm max_speed](outputs/storm/max_speed_shakedown.png)

![storm max_dv](outputs/storm/max_dv_shakedown.png)

![storm hazard](outputs/storm/hazard_shakedown.png)

![storm arrival_h](outputs/storm/arrival_h_shakedown.png)

![storm t_peak_h](outputs/storm/t_peak_h_shakedown.png)

## 4. Key finding on the cascade

With the design report's volumes and areas, Pond 1 draining into Pond 2 statically equalises at ~223.8 m RL, 0.5 m below the Pond 2 crest (224.3 m). The overtopping cascade Damwatch describes therefore requires dynamic surge or a different stage–storage shape. The model initiates the Pond 2 breach at 223.6 m RL (`config/dam.yaml: cascade.pond2_trigger_mRL`); reconcile with Appendix H before any reportable use.

## 5. Interactive

* East: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* West: https://thorstenbux.github.io/wrights-road-dam-breach/west/
* Earthquake (all embankments): https://thorstenbux.github.io/wrights-road-dam-breach/quake/
* Storm (east breach + rain + Eyre River in flood): https://thorstenbux.github.io/wrights-road-dam-breach/storm/
