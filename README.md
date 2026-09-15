# Wrights Road Storage Ponds – dam-breach flood model

Screening-level dam-breach flood model (breach outflow hydrograph + 2D flood routing) for the
proposed 8.2 Mm³ Wrights Road Storage Ponds near Burnt Hill / West Eyreton, Waimakariri District.
Open tools only: LINZ LiDAR (no API key), OpenStreetMap, ANUGA 2D shallow-water solver.

**Read [SPEC.md](SPEC.md) first** – what is needed, what has been assumed, and what a certified
assessment under the Building (Dam Safety) Regulations 2022 additionally requires.
Source facts with page references are in [docs/source-notes.md](docs/source-notes.md).

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

Production runs: `python scripts/01_fetch_dem.py --full` then add `--production` to scripts 04/05.

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
