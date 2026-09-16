# Notes for the Community Liaison Group – Wrights Road Storage Ponds breach model

Running notes of points worth raising with the CLG, BHSL/WIL or their engineers. Screening-level
model; nothing here is a certified assessment. Started 15 Sep 2026.

## Points to raise

### 1. Where does the water go if the ponds have to be emptied in an emergency?
The Damwatch Design Report (Issue 6, 26 Oct 2021, section 3.0 and Table 6, PDF p29) states that
emergency dewatering is done by opening the control gates that discharge outside the ponds – gates
G2, G3 and G6 – into the irrigation races (MR4, R2, R3), plus gate G5 between Pond 1 and the Tub.
The gates must be capable of opening after a Safety Evaluation Earthquake and its aftershocks (s9.3,
PDF p109). **Emergency dewatering is therefore into the race network, not into the Eyre River.**
Questions for the CLG: what is the dewatering rate through the gates, how long does it take to draw
the ponds down to a safe level, and what happens in the races and at their outfalls during that time?

### 2. Eyre River flooding and the north embankment
The same report (s3, PDF p32) cites preliminary Waimakariri District Council flood mapping showing that
a major Eyre River flood north of the ponds "would extend to the North embankment of the ponds". The
report concludes this would not endanger the ponds. Our model domains do not reach the Eyre River at
the ponds (it runs ~7 km north), so this interaction is not represented; the storm scenario only
includes the Eyre where it crosses the breach flood corridor ~10 km east. Worth asking for the WDC
mapping and the design basis for the north embankment under external flooding.

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
