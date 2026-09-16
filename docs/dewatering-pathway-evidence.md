# Emergency dewatering pathway — Wrights Road Storage Ponds → Eyre River

Evidence note, 16 Sep 2026. Question: in a major event, would the ponds be dewatered into the Eyre River via the races and culverts by opening gates?

**Short answer:** yes, in principle. The operator's own Emergency Action Plan states it. But the operational detail (gate capacities, race alignments, dewatering inundation maps) is deferred "prior to commissioning" and has not been published.

## Source

*Wrights Road Storage Ponds – Emergency Action Plan (Pre-construction Issue)*, Issue 6, 8 June 2020, prepared for Waimakariri Irrigation Ltd (Damwatch ref. E1154). Published by BHSL:
https://www.bhsl.co.nz/wp-content/uploads/Waimakariri_Emergency-Action-Plan-Issue-6-2020_06_08.pdf

Retrieved 16 Sep 2026. The document predates the 28 Jan 2026 consent transfer to BHSL and still names WIL as dam owner.

## What it says

| EAP ref | Content (paraphrased) |
|---|---|
| §1.5 Principles | The primary defence against a developing failure is to lower the pond level by opening the outflow gates. The rate is balanced against the risk of downstream damage from high flow. |
| App. D.1 | Close inflows and discharge the pond into the irrigation network. Rate is limited by outlet works capacity (discharge from the Tub and from Pond 2) and by the network's capacity to pass and store water. |
| App. F.1 | Framework only: which gates to open and close, backup power, and manual gate operation are all to be detailed before commissioning. |
| App. F.2 | Example drawdown times per 1 m of storage (see table below). |
| App. F.3 | Races being developed by WIL, **both discharging to the Eyre River**: **MR4** (Main Race), about 6.3 km, about 8 culverts, 4 major offtakes; **R3**, about 11.8 km, about 20 culverts, 6 offtakes. Maximum dewatering flows may exceed race capacity, causing local flooding and minor damage to the network. |
| App. F.4–F.5 | Culverts are identified as the most likely blockage points, which could overtop the race side embankments. Clearance before dewatering and surveillance during it are to be specified. |
| App. F.6 | Promised maps of land inundated between the ponds and the Eyre, showing rate, extent and depth, for two cases: (1) maximum dewatering in fine weather with normal Eyre flow; (2) maximum dewatering combined with the peak of a 1-in-100 AEP Eyre flood. |

### Example drawdown times (EAP Table F.1)

| Pond | Average area (m²) | Outlet | Net outflow (m³/s) | Hours per 1 m drawdown |
|---|---|---|---|---|
| 1 | 134,400 | MR4 | 4 | 9.3 |
| 1 | 134,400 | MR4 | 5 | 7.5 |
| 2 | 658,500 | R2+R3 | 11 | 16.6 |
| 2 | 658,500 | R2+R3 | 14 | 13.0 |
| 2 | 658,500 | R2+R3 | 15 | 12.2 |

Table F.1 is labelled an example. Note that it names an **R2** race alongside R3, but F.3 describes only MR4 and R3.

## Gaps and open questions

- Appendices A (drawings), B (dam-break inundation maps), E (contacts) and F (dewatering detail) are all placeholders "to be included prior to commissioning".
- Gate activation steps are listed as "to be confirmed".
- It is not known whether MR4 and R3 are built, or what their as-built capacities are.
- No dewatering inundation maps have been published (F.6).
- Full drawdown time for 8.2 M m³ is not stated. Check it against plausible failure-development times.
- Not yet read: DSMP Issue 5 (14 Jun 2017) §6.2 "dewater guidelines", and Design Report Issue 6 / Appendix E drawings (outlet works and gate capacities). Both are on the BHSL document library.
- Consent link: CRC263186 cl. 86(d)(ii) requires immediate dewatering if insurance non-performance affects dam-breach cover, so the feasibility of this pathway is directly relevant.

## Modelling implications

The EAP frames these for HEC-RAS; this project routes in ANUGA (see SPEC §3.2), which can take the same inlets. Related: [source-notes.md](source-notes.md) (EAP section), [clg-notes.md](clg-notes.md) point 1.

Candidate scenarios beyond the dam breach itself:

1. **Controlled dewatering, fine weather.** Pond outflow at 4–5 m³/s (MR4) plus 11–15 m³/s (R2/R3), routed down the races to the Eyre. Test race overtopping at the culverts.
2. **Controlled dewatering plus a 1% AEP Eyre flood.** Same outflows combined with the Eyre flood peak.
3. **Culvert-blockage sensitivity.** Blocked culverts on MR4 and R3, with overland flow paths toward the Eyre.

Data needed: race alignments and cross-sections, culvert inventory (size, invert levels), outlet and gate rating curves, and Eyre River design flows.
