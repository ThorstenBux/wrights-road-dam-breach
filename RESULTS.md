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

## 4. Key finding on the cascade

With the design report's volumes and areas, Pond 1 draining into Pond 2 statically equalises at ~223.8 m RL, 0.5 m below the Pond 2 crest (224.3 m). The overtopping cascade Damwatch describes therefore requires dynamic surge or a different stage–storage shape. The model initiates the Pond 2 breach at 223.6 m RL (`config/dam.yaml: cascade.pond2_trigger_mRL`); reconcile with Appendix H before any reportable use.

## 5. Interactive

* East: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* West: https://thorstenbux.github.io/wrights-road-dam-breach/west/
