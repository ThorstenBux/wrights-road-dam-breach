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

### 2. Eyre River flooding and the north embankment
The same report (s3, PDF p32) cites preliminary Waimakariri District Council flood mapping showing that
a major Eyre River flood north of the ponds "would extend to the North embankment of the ponds". The
report concludes this would not endanger the ponds. Our model domains do not reach the Eyre River at
the ponds (it runs ~7 km north), so this interaction is not represented; the storm scenario only
includes the Eyre where it crosses the breach flood corridor ~10 km east. Worth asking for the WDC
mapping and the design basis for the north embankment under external flooding.

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
historically before the 1860s diversion. That overtopping would happen with or without the dam; the dam's
increment is marginal. **Message for the CLG:** North Eyre Road is outside any credible breach or dewatering
footprint; its flood risk is an Eyre River question that this model does not cover (domain stops short of
the river at the site). Follow-ups: WDC Eyre flood mapping (point 2), dewatering rate and race outfalls
(point 1), and optionally a 2D run of the north breach on the extended domain to quantify how much reaches
the Eyre.

## Assumptions in the model that real data would improve

| # | Assumption | Used in | What would replace it |
|---|---|---|---|
| A1 | Pond footprint ≈ 1,075 m square rotated with the road grid; breach points mid-embankment | all scenarios | crest line and breach locations from drawing WIL1125/30/2 |
| A2 | Stage–storage: wetted area varies linearly between invert and FSL | all | surveyed stage–storage tables from the drawings |
| A3 | Design levels ("RL") are on the same datum as the LiDAR (NZVD2016) | all | datum statement from Damwatch |
| A4 | Pond 2 overtopping cascade starts at RL 223.6 (static equalisation only reaches ~223.8, 0.5 m below crest) | east/south/north/storm | Appendix H (breach analysis) of the design report |
| A5 | Froehlich (2008) breach parameters; NZSOLD cites Froehlich 2016 | all | engineer-confirmed coefficients |
| A6 | Uniform roughness n = 0.045; culverts, bridges and race crossings not represented | 2D routing | LCDB land cover; WDC/ECan asset data for culverts and bridges |
| A7 | Earthquake: every embankment and the dividing embankment fail at once, formation time halved, no liquefaction | quake | GNS site-specific hazard, Damwatch seismic stability results (s7.3.3), engineer's view on credible seismic failure modes |
| A8 | Earthquake: no warning time (sirens, TDR crest cable assumed lost) | quake | EAP resilience of the warning system |
| A9 | Storm: 10 mm/h steady rain with zero infiltration on the whole plain | storm | NIWA HIRDS rainfall for the site; soil infiltration (S-map) |
| A10 | Storm: Eyre River flood flow 150 m³/s entering the domain (10 mm/h on ~150 km² upstream catchment, runoff coefficient ~0.4) | storm | ECan flow record for the Eyre River (Downs Road / Eyrewell recorder), flood frequency |
| A11 | Storm: 2 h of rain and river before the breach | storm | choose the timing from a design storm hyetograph |
| A12 | Storm: the Waimakariri River is not in flood (domain edge is transmissive) | storm | Waimakariri flood level at the confluence for the same storm |
| A13 | 2.5 persons per dwelling; OSM footprints classify "dwellings" | consequences | 2012 doorstep survey (Damwatch), LINZ building outlines, census |
| A14 | Shakedown grid 20 m, 4 h (east and north also on the full domain, 12 h); no production (10 m, 14 h) runs yet | all | production runs once A1–A4 are settled |
| A15 | The north (Dixon Road) breach releases Pond 2 only, with its invert at the LiDAR toe (216.7 m); Pond 1 is assumed to sit on the west 30 % of the footprint. Gives a 817 m³/s peak and road arrivals 0.6–4 h *later* than the Damwatch 2016 north times | north | drawing WIL1125/30/2 (which pond the north embankment retains) and the 2016 north-breach parameters in Appendix H |
