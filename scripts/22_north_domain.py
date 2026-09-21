#!/usr/bin/env python
"""EXPLORATORY: DEM and OSM vectors for the domain extended north to the Eyre River beside the ponds (config/north.yaml).

As scripts/01_fetch_dem.py + 02_fetch_vectors.py for the larger bbox, written to NEW files (data/derived/dem_north_20m.tif,
data/raw/osm_north.gpkg) so nothing of the main pipeline is touched. Also reports LiDAR coverage gaps in the new area
(outputs/north_eyre/dem_gaps.json) – the standard fetch fills them silently.
Screening model, not a certified assessment.
"""
import argparse
import json
import sys
from pathlib import Path

import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, north, vectors  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skip-dem", action="store_true"); ap.add_argument("--skip-osm", action="store_true")
    a = ap.parse_args()
    config.ensure_dirs()
    site, cfg = config.site(), config.load_yaml("north.yaml")["domain"]
    bbox = cfg["bbox_nztm"]; out = config.OUTPUTS / "north_eyre"; out.mkdir(parents=True, exist_ok=True)
    dem_path, gaps_path = config.DATA_DERIVED / cfg["dem_name"], config.DATA_DERIVED / cfg["gaps_name"]
    if not a.skip_dem:
        info = north.fetch_dem_with_gaps(bbox, cfg["dem_res_m"], dem_path, gaps_path, site["dem"]["bucket"], site["dem"]["collection"])
        with rasterio.open(gaps_path) as ds:
            info["gaps_over_0p01_km2"] = north.gap_report(ds.read(1) == 1, cfg["dem_res_m"], ds.transform)
        info["bbox_nztm"] = bbox; info["collection"] = site["dem"]["collection"]
        (out / "dem_gaps.json").write_text(json.dumps(info, indent=2)); print(json.dumps(info, indent=2))
    if not a.skip_osm:
        vectors.fetch_osm(bbox, config.DATA_RAW / cfg["osm_name"], site["osm"]["api"], site["osm"]["tile_deg"])


if __name__ == "__main__":
    main()
