#!/usr/bin/env python
"""Fetch roads, buildings and water features for the study domain from OpenStreetMap."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, vectors  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shakedown", action="store_true", help="only the shakedown bbox")
    a = ap.parse_args()
    config.ensure_dirs()
    site = config.site()
    bbox = site["domain"]["shakedown_bbox_nztm"] if a.shakedown else site["domain"]["bbox_nztm"]
    out = config.DATA_RAW / ("osm_shakedown.gpkg" if a.shakedown else "osm_domain.gpkg")
    vectors.fetch_osm(bbox, out, site["osm"]["api"], site["osm"]["tile_deg"])
    roads = vectors.load(out, "roads")
    names = sorted(set(roads["name"].dropna()))
    wanted = config.dam()["consequence"]["roads_of_interest"]
    missing = [r for r in wanted if r not in names]
    print(f"[osm] {len(names)} named roads; roads of interest missing from OSM extract: {missing}")


if __name__ == "__main__":
    main()
