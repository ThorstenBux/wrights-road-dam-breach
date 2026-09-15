# Results – Wrights Road Storage Ponds dam-breach model (shakedown 15 Sep 2026; east run extended to Diversion Road 16 Sep 2026)

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

## 2b. East breach routed to Diversion Road (extended domain, 12 h, 20 m grid)

The east cascade breach re-run on the full 31.5 km × 16 km study domain (site to Diversion Road and the
Waimakariri River; the east edge sits 1 km beyond Diversion Road so the open boundary is on the river side of
the road). Same 20 m LiDAR grid, mesh densities, roughness and hydrograph as the shakedown; 272,000 triangles,
12 h simulated (12 h wall-clock on one loaded Apple-silicon core). Outputs: `outputs/east/*_extended.*`;
animation: [docs/east-extended](https://thorstenbux.github.io/wrights-road-dam-breach/east-extended/).

| Metric | East, extended (12 h) | East, shakedown (4 h) | Damwatch 2012 |
|---|---|---|---|
| Inundated area > 0.1 m (km²) | **68.9** | 39.5 (domain ended at Browns Rd) | flood zone 73 |
| Deepest water (m) | 2.9 | 2.9 | – |
| Fastest flow (m/s) | 5.8 | 5.5 | – |
| Buildings > 0.1 m / ≥ 0.5 m | 527 / 90 | 439 / 95 | households in zone 176 / at risk 40 |
| PAR screening (2.5 persons per at-risk building) | 225 | 238 | 107 |
| Wet area at 12 h (km²) | 15.8 (draining to the river) | – | – |

### Road arrival times – east breach vs Damwatch 2016 (WIL Evacuation Plan Table 1)

| Road | Damwatch arrival (h) | Model arrival (h) | Damwatch depth (m) | Model max depth (m) |
|---|---|---|---|---|
| Carleton Road | 1.50 | 0.83 | 0.68 | 1.06 |
| Wolffs Road | 2.08 | 1.33 | 0.33 | 0.99 |
| Poyntzs Road | 2.67 | 1.92 | 0.34 | 0.92 |
| Pesters Road | 3.00 | 2.27 | 0.57 | 0.53 |
| Downs Road | 4.17 | 3.33 | 0.3 | 1.12 |
| Browns Road | 5.25 | **4.34** | 0.58 | 0.64 |
| Two Chain Road | 7.33 | **5.42** | 0.46 | 0.63 |
| Diversion Road | 9.00 | **7.51** | <0.1 | 0.43 |
| South Eyre Road (east end, near Diversion Rd) | – | 7.90 | – | 0.23 |

Reading: the full-length wave stays in the Damwatch corridor (between South Eyre Road and the Waimakariri
terrace, along the WIL Main Race embankment) all the way to Diversion Road, and the inundated area (69 km²)
matches the Damwatch flood zone (73 km²) closely. Arrival is ~1 h earlier at Browns and Two Chain Roads and
~1.5 h earlier at Diversion Road, the same "faster and deeper" bias as the near-field roads (uniform n = 0.045,
20 m grid smoothing embankments and drains, 1.1 h breach formation). The largest difference is at Diversion
Road itself: 0.43 m here versus "<0.1 m" in 2016. At that point the model is at the far end of a 26 km
routing on a 20 m grid with no drains, culverts or stopbank detail, and the water then leaves through the
open east boundary; treat the Diversion Road depth as an upper-bound screening value and the arrival time as
±1 h. The near-field rows change by ≤ 0.06 h / ≤ 0.2 m compared with the shakedown domain, confirming the
smaller domain did not bias the earlier results. All 12 roads west of Diversion Road that Damwatch lists are
now reached; Thongcaster, Domain and Barrett Roads (south-west of the site) stay dry in the east scenario.

**Maximum depth**

![east extended max_depth](outputs/east/max_depth_extended.png)

**Arrival time**

![east extended arrival_h](outputs/east/arrival_h_extended.png)

**Hazard class**

![east extended hazard](outputs/east/hazard_extended.png)

**Maximum flow speed**

![east extended max_speed](outputs/east/max_speed_extended.png)

**Depth × velocity**

![east extended max_dv](outputs/east/max_dv_extended.png)

**Time of peak depth**

![east extended t_peak_h](outputs/east/t_peak_h_extended.png)

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

## 4. Key finding on the cascade

With the design report's volumes and areas, Pond 1 draining into Pond 2 statically equalises at ~223.8 m RL, 0.5 m below the Pond 2 crest (224.3 m). The overtopping cascade Damwatch describes therefore requires dynamic surge or a different stage–storage shape. The model initiates the Pond 2 breach at 223.6 m RL (`config/dam.yaml: cascade.pond2_trigger_mRL`); reconcile with Appendix H before any reportable use.

## 5. Interactive

* East: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* West: https://thorstenbux.github.io/wrights-road-dam-breach/west/
* Earthquake (all embankments): https://thorstenbux.github.io/wrights-road-dam-breach/quake/
* Storm (east breach + rain + Eyre River in flood): https://thorstenbux.github.io/wrights-road-dam-breach/storm/
