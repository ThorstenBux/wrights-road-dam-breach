# Notes for the Community Liaison Group – Wrights Road Storage Ponds breach model

Running notes of points worth raising with the CLG, BHSL/WIL or their engineers. Screening-level
model; nothing here is a certified assessment. Started 15 Sep 2026.

## Points to raise

### 1. Where does the water go if the ponds have to be emptied in an emergency?
The Damwatch Design Report (Issue 6, 26 Oct 2021, section 3.0 and Table 6, PDF p29) states that
emergency dewatering is done by opening the control gates that discharge outside the ponds – gates
G2, G3 and G6 – into the irrigation races (MR4, R2, R3), plus gate G5 between Pond 1 and the Tub.
The gates must be capable of opening after a Safety Evaluation Earthquake and its aftershocks (s9.3,
PDF p109). The Emergency Action Plan (Issue 6, Jun 2020, App. F.3) adds that the MR4 and R3 races
**both discharge to the Eyre River**, so emergency dewatering reaches the Eyre via the race network
(EAP Table F.1 example: Pond 1 via MR4 at 4–5 m³/s, Pond 2 via R2+R3 at 11–15 m³/s, i.e. 7.5–16.6 h per
metre of drawdown). The EAP warns that dewatering flows may exceed race capacity and that culverts are
the likely blockage points; the gate steps, race capacities and dewatering inundation maps are deferred
"prior to commissioning" and unpublished. Evidence: [dewatering-pathway-evidence.md](dewatering-pathway-evidence.md).
Questions for the CLG: what are the as-built gate and race capacities, how long does a full drawdown of
8.2 M m³ take against plausible failure-development times, are MR4/R3 built, what happens at the culverts
and the Eyre outfalls during dewatering (fine weather and coincident with a 1 % AEP Eyre flood), and will
the F.6 dewatering inundation maps be released?

*Screening runs (exploratory, Sep 2026 – [races-and-shelterbelts-2d.md](races-and-shelterbelts-2d.md),
[dewatering-drawdown-sensitivity.md](dewatering-drawdown-sensitivity.md)):* with the races taken from the LiDAR and every culvert
flowing freely, the race we take to be MR4 carries 5 m³/s and the south race (R2) carries 10 m³/s easily, but the Dixon Road
drain (our R3) cannot carry 5 m³/s – it spills along Dixon Road. With every culvert blocked the flat MR4 stalls 1.7 km from the
ponds. Six hours of dewatering removes only ~5 % of the stored water, so if the ponds still fail the breach flood is almost
unchanged (peak −6 %), and races already running full make no measurable difference to it. Extra questions for the CLG: which
mapped race is which, is R3 to be enlarged, and what is the intended split of Pond 2's flow between R2 and R3? Official
information requests for the F.6 maps (ECan, WDC, Canterbury CDEM) are being drafted separately.

### 2. Eyre River flooding and the north embankment
The same report (s3, PDF p32) cites preliminary Waimakariri District Council flood mapping showing that
a major Eyre River flood north of the ponds "would extend to the North embankment of the ponds". The
report concludes this would not endanger the ponds.

*Screening result (exploratory, 20 Sep 2026 – [eyre-flood-north-embankment.md](eyre-flood-north-embankment.md)):* we extended
the model north and west to where the Eyre leaves the foothills and could **not reproduce river water at the north
embankment**. The ponds sit on a ridge of the old Waimakariri fan and the ground falls from them towards the Eyre, 5.7–7 km
away; the upslope catchment of the north embankment is 0.7 km². In the 2D runs an Eyre flood of 150, 300 or 600 m³/s leaves
0.0 m of water at the embankment and comes no closer than 4.9 km. There is no public flood-frequency estimate for the Eyre on
the plains: the only recorder is a headwater site; NIWA's regional method gives ≈ 148 m³/s (±55 %) for the 1 % AEP flood,
ECan's largest gaugings are 292 and 266 m³/s near South Eyre Road. The councils' current flood model is rain-on-grid with no
Eyre scenario and shows 0–0.3 m of LOCAL rainfall ponding along the north embankment – probably what the "preliminary
mapping" showed too. Questions for the CLG / Damwatch: which map and event was meant, was the water river overflow or local
runoff, and what is the design basis for drainage and toe protection along Dixons Road? Requests to ECan and WDC are drafted
in [eyre-flood-information-requests.md](eyre-flood-information-requests.md). Embankment stability, seepage and stopbank
failure are outside what this model can say.

### 3. Could a breach or emergency dewatering put water on North Eyre Road?
Asked 16 Sep 2026. Screening answer from the model outputs and the LiDAR: **no credible pathway**.
North Eyre Road starts ~9 km east of the ponds and runs 1.7–2.9 km *north* of the Eyre River, on ground
4–12 m above the river bed at the same easting (e.g. road 126.8 m vs river 118.5 m at E 1548.9k). The plain
falls east-south-east at ~6 m/km, so everything released from the ponds moves away from the road:

* Breach wave: maximum depth along North Eyre Road is zero at every sample point in the extended east run
  and in the shakedown east, quake and storm runs; the northern edge of the wave stays 1.5–2 km south of
  South Eyre Road all the way to Downs Road (4–5 km south of North Eyre Road).
* Dewatering through gates G2/G3/G6: the receiving races MR4/R2/R3 and the mapped drains near the site fall
  from ~221 m to ~195 m over 3.5 km heading east-south-east, into the same corridor as the breach wave. No
  mapped race or drain crosses the Eyre; a race-bank failure would spill down the same gradient.
* Eastern end (Swannanoa/Diversion Road): the wave arrives at 0.2–0.4 m; ground rises ~9 m over the 4.8 km
  from Diversion Road to the east end of North Eyre Road, and the Old Eyre Bed (38–41 m) sits above the wet
  cells. Where breach water touches the diverted Eyre channel it is downstream of the old-bed offtake.

The only chain that is not physically impossible is a river-flood story: a major Eyre flood reaches the north
embankment (WDC mapping, report s3), the north embankment fails into the flooded foreground (contrary to the
report's conclusion), the released water (north hydrograph peak 817 m³/s, 4.7 Mm³, not 2D-routed, heavily
attenuated over 6 km of near-flat plain) joins the Eyre flood, and the combined flow overtops the low north
bank between Eyrewell and Swannanoa (road ~49–52 m vs river ~50 m at E 1559–1560k), where the Eyre flooded
historically before the 1929 diversion (ECan R05/15; an earlier version of this note said 1860s). That overtopping would happen with or without the dam; the dam's
increment is marginal. **Message for the CLG:** North Eyre Road is outside any credible breach or dewatering
footprint; its flood risk is an Eyre River question that this model does not cover (domain stops short of
the river at the site). Follow-ups: WDC Eyre flood mapping (point 2), dewatering rate and race outfalls
(point 1).

*Update 20 Sep 2026 – the chain has now been modelled ([eyre-flood-north-embankment.md](eyre-flood-north-embankment.md)):*
its first link fails, because an Eyre flood of up to 600 m³/s does not reach the north embankment at all. A north breach
during a 300 m³/s Eyre flood (both the 817 m³/s and the full-depth 2,100 m³/s variant, A16), the east cascade and the
earthquake case all run east-south-east south of South Eyre Road and meet the river only at river km 53, by South Eyre Road /
the Diversion, 28 km of river below the ponds. There they add 50–170 m³/s and raise the river flood by 0.22–0.33 m over
1–4 km, putting +0.6 to +1.6 Mm³ over the north-east bank line where 2.2 Mm³ already leaves in the river flood alone; no
reach spills only because of a breach, and the **breach-added depth on North Eyre Road is 0.0 m in every case**. North Eyre
Road does get wet from the RIVER alone in the model (0.08 / 0.16 / 0.29 m at 150 / 300 / 600 m³/s), in line with the May 2021
evacuation between Wolffs Road and North Eyre Road – an Eyre River matter with or without the dam.

## Assumptions in the model that real data would improve

| # | Assumption | Used in | What would replace it |
|---|---|---|---|
| A1 | Pond footprint ≈ 1,075 m square rotated with the road grid; breach points mid-embankment | all scenarios | crest line and breach locations from drawing WIL1125/30/2 |
| A2 | Stage–storage: wetted area varies linearly between invert and FSL | all | surveyed stage–storage tables from the drawings |
| A3 | Design levels ("RL") are on the same datum as the LiDAR (NZVD2016) | all | datum statement from Damwatch |
| A4 | Pond 2 overtopping cascade starts at RL 223.6 (static equalisation only reaches ~223.8, 0.5 m below crest) | east/south/north/storm | Appendix H (breach analysis) of the design report |
| A5 | Froehlich (2008) breach parameters; NZSOLD cites Froehlich 2016 | all | engineer-confirmed coefficients |
| A6 | Uniform roughness n = 0.045; culverts, bridges and race crossings not represented. Exploratory runs (A17, A19) show shelterbelts delay the far field by 15–40 min at Diversion Road and that full races do not change the breach flood | 2D routing | LCDB land cover; LiDAR canopy layer (built, optional); WDC/ECan asset data for culverts and bridges |
| A7 | Earthquake: every embankment and the dividing embankment fail at once, formation time halved, no liquefaction | quake | GNS site-specific hazard, Damwatch seismic stability results (s7.3.3), engineer's view on credible seismic failure modes |
| A8 | Earthquake: no warning time (sirens, TDR crest cable assumed lost) | quake | EAP resilience of the warning system |
| A9 | Storm: 10 mm/h steady rain with zero infiltration on the whole plain | storm | NIWA HIRDS rainfall for the site; soil infiltration (S-map) |
| A10 | Storm: Eyre River flood flow 150 m³/s entering the domain (10 mm/h on ~150 km² upstream catchment, runoff coefficient ~0.4) | storm | No Eyre recorder exists at Downs Road or Eyrewell – the only one is the headwater site at Trig Road Ford (166405). 150 m³/s happens to match NIWA's regional 1 % AEP estimate (148 m³/s ± 55 %, see A22); an ECan flood-frequency analysis is still needed |
| A11 | Storm: 2 h of rain and river before the breach | storm | choose the timing from a design storm hyetograph |
| A12 | Storm: the Waimakariri River is not in flood (domain edge is transmissive) | storm | Waimakariri flood level at the confluence for the same storm |
| A13 | 2.5 persons per dwelling; OSM footprints classify "dwellings" | consequences | 2012 doorstep survey (Damwatch), LINZ building outlines, census |
| A14 | Shakedown grid 20 m, 4 h (east and north also on the full domain, 12 h); no production (10 m, 14 h) runs yet | all | production runs once A1–A4 are settled |
| A15 | The north (Dixon Road) breach releases Pond 2 only; Pond 1 is assumed to sit on the west 30 % of the footprint. A direct Pond 1 breach on the north side (`north_p1`) was checked and is smaller (473 m³/s), so this is not what sets the 2016 north times | north | drawing WIL1125/30/2 (which pond the north embankment retains) |
| A16 | Breach invert = natural ground at the toe (no headcut into the ~6 m of pond that lies below ground). On the north side this gives 817 m³/s and arrivals 0.6–4 h *later* than Damwatch 2016; a breach cut down to the Pond 2 floor (210.8 m) gives the east-size 2,100 m³/s outflow and reproduces the 2016 north times and severity (RESULTS §2c). The two are carried as a bounding pair; the full-depth case governs the north-side PIC | north (also south/west in principle) | Appendix H breach parameters; engineer's judgement on headcut erosion through the in-situ gravels; floor levels and cut/fill from WIL1125/30/2 |
| A17 | Exploratory race runs: MR4 / R2 / R3 matched to unnamed OSM waterways; beds = LiDAR water surface; culverts either open cuts or fully blocked; Pond 2 dewatering split 10 / 5 m³/s between R2 / R3; constant EAP Table F.1 example rates | exploratory dewatering / race runs (not in RESULTS) | WIL race GIS, cross-sections, gate ratings and culvert inventory; EAP App. F detail |
| A18 | Exploratory dewatering-then-breach: the ponds are assumed to fail anyway, the Pond 2 breach initiating 0.56 m below the level it would reach unbreached (where 223.6 sits for full ponds) | exploratory dewatering sensitivity | engineer's view on failure development under a falling pool; Appendix H |
| A19 | Exploratory shelterbelts: trees = LiDAR canopy ≥ 6 m, Manning n 0.12–0.30 under canopy as an area-weighted equivalent per triangle; no trunk / fence / debris blockage | exploratory shelterbelt runs (not in RESULTS) | field check of belt density and fencing; literature values for flow through shelterbelts; LCDB for other land cover |
| A20 | Exploratory wet worst case: the `storm` rain and Eyre inflow (A9–A12) for 2 h before and 12 h after the breach, combined with the east cascade or the earthquake breaches and with shelterbelt roughness; breach effects measured against the same storm without the breach on the same mesh and roughness; Eyre flood doubled as a sensitivity only; 10 m³/s of race dewatering flow reaching the Eyre (MR4 5, R3 5, R2 none) | exploratory wet runs (not in RESULTS) – [docs/wet-worstcase-trees-races.md](wet-worstcase-trees-races.md) | ECan Eyre flow record and flood frequency, HIRDS design storm, S-map infiltration; WIL race outfall locations and rates |
| A21 | Exploratory Eyre capacity: bank-full Manning capacity (n 0.035) of 2 m LiDAR sections ±400 m about the OSM centreline; 2D river banks on 1,000 m² triangles; no bank erosion or stopbank failure | exploratory Eyre analysis (not in RESULTS) | ECan / WDC river survey, stopbank crest levels and condition, flood mapping for the Eyre |
| A22 | Exploratory Eyre flood on the north-extended domain: the whole flood enters where the Eyre leaves the foothills as one gamma-shaped hydrograph (base 5 m³/s, peak after 5 h); peaks 150 m³/s (≈ NIWA regional 1 % AEP estimate, ±55 %), 300 m³/s (≈ largest ECan gauging) and 600 m³/s (bounding) – the last two have no return period; no tributary inflow below Oxford; losses to groundwater ignored; breach opens 8 h in, when the peak passes the ponds' reach | exploratory north / Eyre runs (not in RESULTS) – [eyre-flood-north-embankment.md](eyre-flood-north-embankment.md) | ECan flood frequency and design hydrograph for the Eyre, rating and high-flow gaugings (request drafted) |
| A23 | The "preliminary WDC flood mapping" of design report s3 is read as local rain-on-grid ponding, because neither the LiDAR terrain nor the 2D model lets river water reach the north embankment and the councils' current model has no Eyre scenario | CLG point 2 | the map itself and its event description from WDC / Damwatch (request drafted) |
| A24 | North-extended domain: 20 m LiDAR of 2020–25 on 1,000–6,000 m² triangles, stopbanks and road embankments smoothed, no bridges / culverts / races; fixed bed (no avulsion, stopbank erosion or failure); ponds as a solid block; embankment stability, seepage and toe erosion under external water not modelled | exploratory north / Eyre runs | ECan stopbank crest survey and river cross-sections; Damwatch drainage and toe-protection design along Dixons Road |
