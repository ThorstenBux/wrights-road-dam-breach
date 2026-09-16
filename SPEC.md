# Wrights Road Storage Ponds – dam-breach flood modelling: specification

*Tripod Digital – working draft, 15 September 2026. Screening-level model; see §1.3 on certification.*

## 1. What is being asked and what we will deliver

**Question.** For the proposed Wrights Road Storage Ponds (Burnt Hill Storage Ltd / Waimakariri
Irrigation Ltd, corner of Wrights Road and Dixon Road, ~9 km south of Oxford, ~6 km north of the
Waimakariri River): if an embankment breaches, what **flow rate** leaves the ponds and what **water
levels** result downstream, where and when?

**Deliverables (per breach scenario).**

| # | Deliverable | Form |
|---|---|---|
| D1 | Breach outflow hydrograph: discharge vs time, peak discharge, time to peak, volume released, breach dimensions vs time, pond level vs time | CSV + PNG + JSON summary |
| D2 | Inundation rasters: maximum depth, maximum velocity, depth x velocity, flood hazard class (H1–H6), arrival time (depth > 0.1 m), time of peak | GeoTIFF (EPSG:2193, 10 m) |
| D3 | Water level / depth time series at points of interest (road crossings, dwellings, WIL races) | CSV + plots |
| D4 | Road table: first arrival time, max depth and location per named road (comparable to the WIL Evacuation Plan Table 1) | CSV |
| D5 | Buildings table and Population-at-Risk screening (depth ≥ 0.5 m criterion as used by Damwatch 2012; hazard > H2 criterion per NZSOLD 2024) | CSV + JSON |
| D6 | Sensitivity runs: breach width, formation time, breach invert (foundation scour), Manning's n | tables |
| D7 | Method statement, assumptions register and comparison with the Damwatch 2012/2016 results | this document + report |

### 1.1 The dam (from Damwatch Design Report Issue 6, Oct 2021 – details and page refs in `docs/source-notes.md`)

* Two adjoining lined ponds on a ~1 km x 1 km footprint (120 ha property), split by a middle embankment.
  **Pond 1** (upper, west): FSL RL 226.5 m, ~30 ha, ~2.0 Mm³, 8 m deep. **Pond 2** (lower, east): FSL RL 222.8 m,
  ~72 ha, ~6.2 Mm³, 12 m deep. Total **8.2 Mm³**. Freeboard 1.5 m → crests ≈ RL 228.0 / 224.3.
* Gravel-fill embankments with an exposed geomembrane liner; fill won from the pond inverts, so the ponds
  are partly excavated: natural ground falls from ~RL 224 (NW) to ~RL 213 (SE) across the site (LiDAR), so the
  embankment stands 0–12 m above ground depending on the side. Internal slopes 1V:3H; external 1V:2H (Medium
  PIC sections) / 1V:2.5H (High PIC sections).
* Off-river storage: no natural catchment inflow; the only external inflow is the WIL main race into the Buffer
  Pond (protected by an emergency spillway and a 20 m fuse plug, ~60 m³/s). Groundwater ~20 m deep.
* Potential Impact Classification (Damwatch, 2012 basis): **High** for the north, east and south embankments,
  **Medium** for the west embankment and the embankment north of the Tub.
* Previous dam-break work: Damwatch PIC report E1125 (Sep 2012), 2D hydraulic model, four breach locations
  (E/S/N/W), 270-household doorstep survey; "Dam Break Flood Hazard Update" (Sep 2016). Peak breach outflow
  "approximately 2,500 m³/s". PAR 107 / 54 / 95 / 4 (E/S/N/W). Arrival times at roads in the WIL Evacuation Plan
  (Carleton Rd 50 min … Diversion Rd 5 h 35 min for a north breach). **Appendix H (the breach analysis) is
  bound separately and not public.**
* Status (Sep 2026): consented (Environment Court Aug 2020), not yet built, target operation 2029/30.

### 1.2 Regulatory frame

* **Building (Dam Safety) Regulations 2022** (in force 13 May 2024): each pond is a classifiable dam (≥ 4 m and
  ≥ 20,000 m³). The owner must have a PIC certified by a **Recognised Engineer** and, for Medium/High PIC, a Dam
  Safety Assurance Programme (DSAP) audited and certified, plus emergency planning.
* **NZSOLD Dam Safety Guidelines 2024, Module 2** (consequence assessment and PIC) recognises three levels of
  dam-break assessment – *initial*, *intermediate*, *comprehensive*. A High-PIC dam that needs inundation maps
  for emergency planning requires an intermediate or comprehensive assessment: breach parameters from
  historical data (Wahl 1998; Froehlich 2016a/b), 2D flood routing, outputs of extent, arrival time, time to
  peak, depth, velocity and duration at key locations, hazard thresholds H1–H6, PAR with no credit for warning
  or evacuation, both "sunny day" and "rainy day" scenarios where credible.

### 1.3 What this project is – and is not

This pipeline is an **independent, reproducible, open-source screening model at the NZSOLD "intermediate"
level**. It is suitable for: an independent check of the Damwatch numbers; visualising inundation for the
Community Liaison Group, WDC Civil Defence and the Evacuation Plan; sensitivity testing; and preparing inputs
for a certified assessment. It is **not** a certified PIC or DSAP deliverable: that must be produced or
reviewed and certified by a Recognised Engineer (Regulations 2022, Part 2), who may prefer HEC-RAS / TUFLOW
and who will need the design drawings and Appendix H. All life-safety conclusions drawn from this model must
carry that caveat.

## 2. What we need (inputs) – status

| Input | Why | Status | Source / action |
|---|---|---|---|
| Crest alignment, crest levels, crest width, batter slopes, dividing-embankment position | breach geometry, terrain burn-in, breach locations | **Approximate** (report text + road grid); **need drawings** WIL1125/30/2, 21–23, 101–119 | request from BHSL / WIL / Damwatch |
| Stage–storage tables for Pond 1 and Pond 2 | volume released vs level (V_w for Froehlich; routing) | **Assumed** truncated-pyramid from the report's volumes/areas/depths | drawings or design model |
| Vertical datum of design RLs | LiDAR is NZVD2016; design RLs may be Lyttelton 1937 (offset ~0.3–0.5 m in Canterbury) | **Unconfirmed** | ask Damwatch; check against surveyed Buffer Pond / MR4 levels in LiDAR |
| Damwatch Appendix H + 2016 Flood Hazard Update | breach parameters, software, inundation maps to compare/calibrate | **Not public** | request from BHSL (Community Liaison Group context) |
| Pre-construction LiDAR DEM | terrain for 2D routing | **Have** – LINZ Canterbury 1 m DEM 2020–2025 (NZVD2016, CC BY 4.0), no API key; also Waimakariri Jun–Jul 2023 tiles at the site | `scripts/01_fetch_dem.py` |
| Roads, buildings, water races, ponds | arrival tables, PAR, hydraulic features | **Have (OSM)**; **recommended** LINZ NZ Building Outlines + NZ Roads via LDS API key; Damwatch 2012 doorstep survey (270 households) | `scripts/02_fetch_vectors.py`; LINZ key |
| Land cover → Manning's n | flood wave speed and depth | **Default** n = 0.045 (pasture/crop); **recommended** LCDB v5 (LRIS, free) or OSM landuse map | phase 1 |
| Hydraulic structures: road embankments, culverts, bridges, WIL race embankments (MR4, R2, R3), Eyre River / Cust drains | blockage or conveyance of the flood wave | Embankments resolved by 1 m LiDAR; **culverts/bridges not** – need WDC/ECan asset data or blocked/open assumptions per NZSOLD s2.3.6 | phase 1 |
| Occupancy data (dwellings, farm workers, schools, roads) | PAR per NZSOLD Table 2.7 | **Not held** – screening uses 2.5 persons/dwelling | WDC / Census / survey |
| "Rainy day" hydrology | NZSOLD requires it where credible | Off-river storage with no tributary inflow – Damwatch treats sunny-day as governing; document rationale; PMP into the Buffer Pond handled by fuse plug | note in report |
| Receiving water (Waimakariri River) | tailwater | negligible per Damwatch (peak ≪ 2 × MAF) | no action |
| Compute | 2D runs of 200–450 km² at 10–20 m for 8–14 h simulated | Apple Silicon Mac ok for shakedown (~100 k triangles); production (~0.5–1 M triangles) needs hours per run or a Linux box with MPI | phase 1 |

## 3. Method

### 3.1 Breach outflow (D1) – `damflood/breach.py`

1. **Stage–storage** per pond: area varies linearly with level between invert and FSL (V = H(A₀+A₁)/2), calibrated
   to the report's volume, area and depth. Replace with drawing-based tables when available.
2. **Breach parameters** – Froehlich (2008): average width B = 0.27 k₀ V_w^0.32 h_b^0.04 (k₀ = 1.3 overtopping,
   1.0 piping), side slopes 1.0 / 0.7 (H:V), formation time t_f = 63.2 √(V_w /(g h_b²)); V_w = volume above the final
   breach invert; h_b = pool level – breach invert. Peak-flow check with Froehlich (1995). NZSOLD 2024 cites
   Froehlich (2016a/b); the coefficients are to be confirmed by the reviewing engineer and can be entered as
   user parameters. Sensitivity: width x0.5/x2, t_f x0.5/x2.
3. **Breach invert** = natural ground at the embankment toe from LiDAR (no foundation scour), with a scour
   sensitivity (+1 m). Because the ponds are partly below ground, this – not the 8–12 m "embankment height" –
   controls the releasable volume and head, and it differs strongly between the up-slope (west, north) and
   down-slope (east, south) sides.
4. **Level-pool routing**: the pool drains through a trapezoidal breach that grows linearly (or sinusoidally)
   to its final size over t_f; broad-crested weir flow Q = 1.7 b H^1.5 + 1.4 z H^2.5 (SI); 1 s time step; no
   tailwater submergence (conservative for outflow).
5. **Cascade** (E/S/N scenarios, following Damwatch): Pond 1 pipes through the dividing embankment into Pond 2
   (breach invert = Pond 2 FSL); Pond 2 then fails by overtopping when it reaches a configurable initiation
   level, and the Pond 2 hydrograph is routed downstream. **Finding (this study):** with the report's volumes
   and areas, a static level-pool equalisation of the two ponds reaches only ~RL 223.8, 0.5 m *below* the
   Pond 2 crest (224.3), so overtopping requires dynamic surge/wave effects or a different stage–storage
   shape. The default initiation level is set to RL 223.6 (FSL + 0.8 m) and must be reconciled with
   Appendix H. This is the single most consequential assumption in the cascade scenarios.
6. West scenario: direct piping failure of Pond 1 only (Medium PIC), no cascade.
7. **Earthquake scenario (`quake`)** – simultaneous breaches (`MultiBreachEvent`, `route_multi`, `cascade_multi`):
   every external embankment (E, S, N of Pond 2; W of Pond 1) and the dividing embankment start to fail at t = 0,
   each with Froehlich (2008) final dimensions as if it failed alone and a formation time halved for erosion through
   cracked, slumped fill. Pond 1 drains through the west and dividing breaches (the latter into Pond 2); Pond 2 drains
   through the sum of its three breaches, and the pool is volume-limited across all of them. The downstream
   hydrograph is the sum of the four external breaches, each injected at its own inlet in the 2D model. This is a
   postulated bounding case (the design intent is that the ponds survive the Safety Evaluation Earthquake with
   233–388 mm crest settlement against 1.5 m freeboard), triggered for example by an Alpine Fault rupture (Mw ~8) or
   a Darfield-type Mw 7 Canterbury Plains event; it assumes no warning time and no liquefaction of the gravel
   foundation (groundwater ~20 m deep). See `config/dam.yaml: scenarios.quake` for the full assumption list.
8. **Storm scenario (`storm`)** – the NZSOLD "rainy day" combination: the east cascade breach (identical hydrograph)
   opens during a regional storm. The 2D model gets steady 10 mm/h rain on the whole domain with no infiltration
   (`Rate_operator`), the Eyre River already in flood where it enters the domain (constant 150 m³/s inlet – an
   assumption derived from 10 mm/h on the ~150 km² foothill catchment with a runoff coefficient of ~0.4; replace with
   ECan flow records), and 2 h of spin-up before the breach so the channel is flowing across the domain and the plain
   is wet. Arrival times are measured as the first time the depth exceeds the pre-breach depth by 0.1 m, so rain and
   the river do not count as the breach wave; maximum depths are absolute. The design report (s3) cites WDC mapping
   showing a major Eyre flood reaching the north embankment, but the river is ~7 km north of the ponds, outside both
   model domains, so that interaction is not represented. Emergency dewatering of the ponds is via control gates
   G2/G3/G6 into the irrigation races (report s3.0, Table 6); per the EAP (App. F.3) the MR4 and R3 races discharge
   to the Eyre River, so a controlled dewatering ultimately reaches the Eyre (not modelled here; see
   `docs/dewatering-pathway-evidence.md`).

### 3.2 2D flood routing (D2–D4) – `damflood/model.py`

* **Engine**: ANUGA 4.0 (Geoscience Australia / ANU) – open-source finite-volume shallow-water solver on an
  unstructured triangular mesh, well-validated for dam-break and inundation; runs on macOS/Linux, Python API,
  MPI-parallel on Linux. Alternatives: HEC-RAS 2D (free, Windows, built-in breach module – the usual choice of
  NZ dam engineers), TUFLOW / MIKE21 (commercial). The ANUGA pipeline is fully scripted and re-runnable, which
  is what an independent check and repeated sensitivity runs need.
* **Domain**: shakedown 18 km x 11.5 km (site to Browns/Two Chain Road) at 20 m DEM; full domain 31.5 km x 16 km
  (site to Diversion Road and the Waimakariri River, covering the Damwatch 59–73 km² flood zones; the east edge is
  1 km beyond Diversion Road, which runs at 1560.6–1561.3 km E, so the open boundary is not on the road). The full
  domain is run either as the **extended** tier (20 m, shakedown mesh, 12 h – used for the east run in RESULTS §2b)
  or as **production** (10 m, fine mesh, 14 h).
* **Mesh**: coarse triangles ~4,000 m² (shakedown) / ~1,200 m² (production); refined to 900 / 200 m² within
  2.5 km of the site and 2,000 / 600 m² in the flow corridor. Flow algorithm DE0 (shakedown) / DE1 (production).
* **Terrain**: LiDAR pre-construction ground; the full ponds burned in as a solid block at crest level (the
  reservoir is not resolved; the breach hydrograph is injected on an 80 m x 30 m patch just outside the toe).
  Option retained to model the ponds explicitly with an eroding breach for a comprehensive assessment.
* **Friction**: Manning's n = 0.045 uniform (sensitivity 0.035–0.06); phase 1: land-cover-based raster.
* **Boundaries**: transmissive on all edges (water leaves the domain at the Waimakariri River side).
* **Duration**: 4 h (shakedown) / 12 h (extended) / 14 h (production, to cover Diversion Road arrival ~10 h 40 min).

### 3.3 Hazard products and consequences (D2, D4, D5) – `damflood/post.py`

* Per mesh vertex over all timesteps: max depth, max speed, max D·V, arrival time (depth > 0.10 m), time of peak;
  gridded to 10 m GeoTIFFs.
* Flood hazard classes H1–H6 with the ARR 2019 / Smith et al. (2014) thresholds referenced by NZSOLD Table 2.5.
* Roads: sample every 25 m along each named road → first arrival, max depth, location.
* Buildings: max depth/speed/D·V at each footprint → "at risk" by the Damwatch criterion (≥ 0.5 m) and by the
  NZSOLD criterion (> H2); PAR = at-risk dwellings x 2.5 persons (screening). NZSOLD PAR proper needs
  occupancy per Table 2.7 and no evacuation credit.
* Validation targets: Damwatch peak ~2,500 m³/s; Evacuation Plan Table 1 arrival times and depths.

## 4. Scenario matrix

| Scenario | Mechanism | Breach side | Volume involved | Damwatch PIC (Regs 2008) | Damwatch PAR |
|---|---|---|---|---|---|
| east | Pond 1 → Pond 2 cascade, Pond 2 overtopping | Wrights Rd (E) | 8.2 Mm³ | High | 107 |
| south | cascade, overtopping | R2 race (S) | 8.2 Mm³ | High | 54 |
| north | cascade, overtopping | Dixon Rd (N) | 8.2 Mm³ | High | 95 |
| west | Pond 1 piping only | MR4 race (W) | 2.0 Mm³ | Medium | 4 |
| quake | earthquake: all embankments + dividing embankment breach at once, t_f x0.5, no warning | E + S + N + W | 8.2 Mm³ | – (postulated) | – |
| storm | rainy day: east cascade breach + 10 mm/h rain (no infiltration) + Eyre River in flood (150 m³/s assumed), 2 h spin-up | Wrights Rd (E) | 8.2 Mm³ + rain + river | – (combination) | – |
| sensitivities | width x0.5/x2; t_f x0.5/x2; invert –1 m scour; n 0.035/0.06; cascade initiation level | east (governing) | | | |

## 5. Work plan

| Phase | Scope | Output |
|---|---|---|
| **0 – today** | Sources reviewed, parameters extracted, pipeline scaffolded, unit tests, shakedown run of the east scenario on real LiDAR | this spec, repo, first hydrograph and depth map |
| 1 – geometry & data | Obtain drawings, stage–storage, datum, Appendix H, 2016 update; LINZ buildings/roads (API key); LCDB roughness; culvert/bridge assumptions; production DEM | validated inputs, assumptions register |
| 2 – production runs | Four scenarios at 10 m / 14 h; sensitivity set; comparison with Damwatch | D1–D6 |
| 3 – reporting | Method statement, maps, tables, web map for the Community Liaison Group; hand-over package for the Recognised Engineer | D7 |

## 6. Decisions needed from the client

1. Purpose: independent check / community visualisation / input to the certified PIC & DSAP (drives the level of assessment and who signs it off).
2. Can BHSL/WIL release drawings WIL1125/30/xx, the stage–storage curves, Appendix H and the 2016 update?
3. Datum of design levels; confirmation of Pond 1 (west) / Pond 2 (east) layout and dividing-embankment position.
4. Whether a LINZ Data Service API key and an LRIS (LCDB) account can be created for the project.
5. Compute: run production on a Mac (hours per run) or on a Linux box/cloud with MPI.

## 7. First results (Phase 0 shakedown, 15 Sep 2026)

### 7.1 Breach outflow hydrographs (D1) – `outputs/<scenario>/hydrograph.csv|png`, `breach_summary.json`

| Scenario | Breach invert (LiDAR toe, m NZVD2016) | Peak outflow (m³/s) | Time to peak after external breach starts (h) | Lag: Pond 1 failure → Pond 2 breach (h) | Volume released (Mm³) | Froehlich (1995) peak check (m³/s) |
|---|---|---|---|---|---|---|
| east | 210.8 | **2,098** | 1.1 | 2.2 | 7.18 | 1,484 |
| south | 215.4 | **1,066** | 1.5 | 2.2 | 5.34 | 777 |
| north | 216.7 | **817** | 1.7 | 2.2 | 4.68 | 600 |
| west | 221.9 | **235** | 1.4 | 0.0 | 1.24 | 256 |
| quake (sum of E+S+N+W) | 210.8 / 215.4 / 216.7 / 221.9 | **3,001** (east alone 2,567; west 274; south 207; north 49) | 0.6 | 0.0 (all at t = 0) | 7.43 | – |

Breach geometry (Froehlich 2008, final size; B_bot = bottom width, z = side slope H:V, t_f = formation time):

* **east** – pond2 external breach (overtopping, initiates when Pond 2 reaches 223.6 m RL; crest 224.3 m): V_w=6.786e+06 m3, h_b=12.80 m, B_avg=59.7 m; B_bot=46.9 m, z=1.0, t_f=1.14 h
* **south** – pond2 external breach (overtopping, initiates when Pond 2 reaches 223.6 m RL; crest 224.3 m): V_w=4.977e+06 m3, h_b=8.18 m, B_avg=53.1 m; B_bot=44.9 m, z=1.0, t_f=1.53 h
* **north** – pond2 external breach (overtopping, initiates when Pond 2 reaches 223.6 m RL; crest 224.3 m): V_w=4.329e+06 m3, h_b=6.86 m, B_avg=50.4 m; B_bot=43.5 m, z=1.0, t_f=1.70 h
* **west** – pond1 external breach (piping): V_w=1.255e+06 m3, h_b=4.63 m, B_avg=25.7 m; B_bot=22.4 m, z=0.7, t_f=1.36 h
* **quake** – all five breaches open at t = 0 with formation times halved (east 0.58 h, south 0.80 h, north 0.89 h, west 0.68 h, dividing 0.77 h). The east breach, whose invert is 4.6–6 m lower than the others, takes 6.0 of the 7.4 Mm³ released: Pond 2 is empty below the south and north inverts before those breaches are fully formed, so they pass only 0.38 and 0.05 Mm³. Pond 1 loses 0.97 Mm³ west and 0.28 Mm³ into Pond 2. The combined peak (3,000 m³/s at 0.6 h) is 43 % above the cascade east peak and arrives ~2.7 h earlier relative to the initiating event, because there is no Pond 1 → Pond 2 filling stage.
* Pond 1 → Pond 2 dividing breach (all cascade scenarios): piping, invert at Pond 2 FSL 222.8 m, V_w = 1.02 Mm³, B_avg = 23.8 m, t_f = 1.53 h; Pond 2 reaches the 223.6 m initiation level 2.2 h after Pond 1 starts to fail (peak level 223.67–223.73 m, i.e. 0.6 m below the crest – see §3.1 item 5).

**Comparison with Damwatch:** the east-breach peak of ~2,100 m³/s is within 20 % of the "approximately
2,500 m³/s" quoted in the design report; the empirical Froehlich (1995) check gives ~1,500 m³/s. The
ordering east > south > north > west follows directly from the ground level at the toe (211 m on the
Wrights Road side vs 217 m on the Dixon Road side and 222 m on the MR4 side), which the LiDAR now
quantifies. Sensitivity to the cascade initiation level, breach width and formation time is the next step.

### 7.2 2D routing shakedown (D2–D5)

Shakedown settings: 18 km × 11.5 km domain, 20 m LiDAR grid, 165,000-triangle mesh (1,500 m² near the site,
3,000 m² in the corridor), Manning n = 0.045, 4 h simulated, ANUGA DE0. Wall-clock on one Apple-silicon core:
30 min for the west run, 85 min for the east run (the timestep shrinks as the wet area grows).

**West breach (Pond 1 piping, 1.24 Mm³ released) – complete.**

| Metric | Model (4 h) | Damwatch 2012 |
|---|---|---|
| Inundated area > 0.1 m | 5.99 km² | flood zone 15 km² |
| Deepest water | 1.7 m | – |
| Buildings touched > 0.1 m / ≥ 0.5 m | 45 / 2 | households in zone 50 / at risk 1 |
| PAR screening (2.5 persons per at-risk dwelling) | 5 | PAR 4 |
| Roads reached | Wrights Rd (1.1 h, 0.57 m), Dixon Rd (0.6 h, 0.71 m), Domain Rd (1.1 h, 0.50 m) | – |

The west outflow spills over the MR4 race and drifts north-east toward Dixon Road at shallow depth, which is
consistent with the Medium/Low PIC assigned to that embankment. Outputs: `outputs/west/` (GeoTIFFs
`max_depth`, `max_speed`, `max_dv`, `arrival_h`, `hazard`; `roads_shakedown.csv`; `buildings_shakedown.csv`;
`max_depth_shakedown.png`).

**East breach (cascade, 7.2 Mm³ released, peak 2,100 m³/s) – complete (4 h after the Pond 2 breach opens;
Pond 2 breach opens 2.2 h after the Pond 1 failure begins).**

| Metric | Model (4 h) | Damwatch 2012 |
|---|---|---|
| Inundated area > 0.1 m | 39.47 km² (domain ends at Browns Road) | flood zone 73 km² (full duration) |
| Deepest water | 2.9 m (at the breach) | – |
| Buildings touched > 0.1 m / ≥ 0.5 m | 439 / 95 | households in zone 176 / at risk 40 |
| PAR screening (2.5 persons per at-risk building) | 238 | PAR 107 |

Road arrival times, model vs the Damwatch 2016 values in the WIL Evacuation Plan (both measured from the start
of the external breach; Damwatch describe theirs as "worst case … from time of breach"):

| Road | Damwatch 2016 arrival (h) | Model arrival (h) | Damwatch depth (m) | Model max depth (m) |
|---|---|---|---|---|
| Carleton Road | 1.50 | 0.77 | 0.68 | 1.00 |
| Wolffs Road | 2.08 | 1.33 | 0.33 | 0.94 |
| Poyntzs Road | 2.67 | 1.90 | 0.34 | 0.75 |
| Pesters Road | 3.00 | 2.27 | 0.57 | 0.51 |
| Downs Road | 4.17 | 3.33 | 0.3 | 1.18 |
| Browns Road | 5.25 | not reached in 4 h | 0.58 | 0.00 |
| Two Chain Road | 7.33 | not reached in 4 h | 0.46 | 0.00 |
| Diversion Road | 9.00 | not reached in 4 h | <0.1 | not reached in 4 h |

Reading: the modelled wave runs east-south-east in the same corridor Damwatch mapped (between South Eyre Road
and the Waimakariri terrace, channelled along the WIL Main Race embankment), and reaches each road **about
45 minutes earlier** and generally **deeper** than the 2016 study. Both differences point the same way and are
expected from the shakedown assumptions: uniform Manning n = 0.045 with no shelterbelts, fences or crops; a
20 m grid that smooths the road and race embankments that would pond and delay the flow; and a breach that
opens fully in 1.1 h. The building count at ≥ 0.5 m (95) exceeds Damwatch's 40 households because OSM
footprints include sheds and outbuildings and the count is at footprint centroid rather than surveyed
doorstep level. These are the calibration levers for phase 1, not evidence that either study is wrong.

Outputs: `outputs/east/` (GeoTIFFs, `roads_shakedown.csv`, `buildings_shakedown.csv`,
`compare_damwatch_shakedown.csv`, `max_depth_shakedown.png`, `east_shakedown.sww`).

**3D animation.** `scripts/07_export_webgl.py` + `webgl/index.html` produce a Three.js viewer: LiDAR terrain,
animated water surface at terrain + modelled depth, all named roads labelled, OSM buildings extruded to their
footprints (coloured amber above 0.1 m and red at 0.5 m or more), 1.8 m figures beside dwellings, hydrograph
scrubber, and three views: **Re-centre** (frames the full flood extent, also on load), **Breach** close-up, and
**Street level** (switches to true vertical scale ×1 at a dwelling that floods, and jumps to the moment the wave
arrives, so buildings and people are seen going under water at their real proportions). Published as a private
artifact: https://claude.ai/artifact/KjgsKm5Q7NGFzwZ3G1v1v6

### 7.3 Caveats specific to the shakedown

* **Mesh repair (16 Sep 2026).** The original refinement handling left a 1 m gap between the site circle and the
  corridor polygon, which the mesher filled with a ring of 61,503 sliver triangles (< 5 m) – 37 % of the 165,047
  triangles – pinning the CFL time step at ~0.15 s. `_prepare_refinements` now separates regions by 150 m; the
  shakedown mesh has 95,140 triangles, none under 22 m, and runs 4–10× faster. The east, west and quake results
  above were produced on the old mesh; the storm scenario on the repaired one. A re-run of east on the repaired mesh
  (`outputs/east/*_mesh2.*`) changes inundated area 39.5 → 39.2 km², road arrivals by ≤ 2 min, buildings ≥ 0.5 m
  95 → 92 – i.e. the mesh defect cost time, not accuracy. Production runs should use the repaired mesh.

* 20 m grid and ≥ 1,500 m² triangles smooth out road embankments, races and drains; production runs use 10 m / 200–600 m².
* Pond footprint, dividing embankment and breach positions are approximate (§2).
* Uniform roughness; no culvert/bridge blockage assumptions; buildings not represented in the terrain.
* Depth "at a building" is the model depth at the footprint centroid, not a floor level; Damwatch surveyed doorsteps.
