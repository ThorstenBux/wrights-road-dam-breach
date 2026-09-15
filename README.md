# Wrights Road Storage Ponds – dam-breach flood model

Screening-level dam-breach flood model (breach outflow hydrograph + 2D flood routing) for the
proposed 8.2 Mm³ Wrights Road Storage Ponds near Burnt Hill / West Eyreton, Waimakariri District.
Open tools only: LINZ LiDAR (no API key), OpenStreetMap, ANUGA 2D shallow-water solver.

**Read [SPEC.md](SPEC.md) first**, then [RESULTS.md](RESULTS.md) (key numbers and all maps) and [HANDOVER.md](HANDOVER.md) – what is needed, what has been assumed, and what a certified
assessment under the Building (Dam Safety) Regulations 2022 additionally requires.
Source facts with page references are in [docs/source-notes.md](docs/source-notes.md); points to raise with the Community Liaison Group and the assumption register are in [docs/clg-notes.md](docs/clg-notes.md).

## Live animations (GitHub Pages)

* East embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/east/
* West embankment breach: https://thorstenbux.github.io/wrights-road-dam-breach/west/
* Earthquake (all embankments at once): https://thorstenbux.github.io/wrights-road-dam-breach/quake/
* Storm (east breach + 10 mm/h rain + Eyre River in flood): https://thorstenbux.github.io/wrights-road-dam-breach/storm/
* Index: https://thorstenbux.github.io/wrights-road-dam-breach/

Controls: drag to orbit, scroll to zoom (down to 30 m), shift-drag to pan, space to play/pause; buttons
Re-centre / Breach / Street level; sliders for terrain and flood vertical scale; checkbox to colour the water by
flow speed (m/s) instead of depth. Building colour: amber > 0.1 m, red ≥ 0.5 m at the footprint.

## Quick start

```bash
conda env create -f environment.yml      # or: conda env update -f environment.yml
conda activate damflood
make test                                # breach-routing unit tests
make dem                                 # LiDAR DEM, shakedown domain (20 m)
make vectors                             # OSM roads / buildings / water for the study domain
make breach SCENARIO=east                # breach parameters + outflow hydrograph
make run SCENARIO=east                   # ANUGA 2D routing (shakedown: ~4 h simulated)
make post SCENARIO=east                  # hazard rasters, road arrival table, buildings/PAR
```

Model tiers (`--mode` on scripts 01/04–08, or `MODE=` with make): `shakedown` (18 × 11.5 km to Browns Road, 20 m, 4 h),
`extended` (full 31.5 × 16 km domain to Diversion Road and the Waimakariri River, still 20 m and the shakedown mesh, 12 h),
`production` (full domain, 10 m, fine mesh, 14 h). `--production` / `--full` remain as aliases.

Extras: `scripts/06_compare.py` (model vs Damwatch road arrival times) and `scripts/07_export_webgl.py`
(data for the Three.js viewer in `webgl/index.html`: LiDAR terrain, animated water, roads with names, OSM
buildings extruded to footprint and coloured when flooded, 1.8 m figures; views: Re-centre / Breach /
Street level at true vertical scale). Depth maps from script 05 carry road names.

## Layout

```
config/site.yaml     site geometry, model domain, data sources, mesh/run settings
config/dam.yaml      dam parameters (sourced), scenarios, breach defaults, friction, consequence rules
damflood/            breach.py terrain.py vectors.py model.py post.py
scripts/01..05       pipeline steps (see Makefile)
outputs/<scenario>/  hydrograph.csv/.png, breach_summary.json, *.sww, max_depth/max_speed/max_dv/
                     arrival_h/hazard GeoTIFFs, roads.csv, buildings.csv, post_summary.json, map PNG
```

## Status
Scaffold + first shakedown run. Pond footprint and breach locations are **approximate** (derived
from the EAP coordinate and the road grid); replace with drawing WIL1125/30/2 geometry.
