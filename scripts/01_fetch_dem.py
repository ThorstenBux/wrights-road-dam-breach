#!/usr/bin/env python
"""Fetch and mosaic the LINZ LiDAR DEM for the model domain (no API key needed)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, terrain  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="full study domain (default: shakedown bbox)")
    ap.add_argument("--res", type=float, help="cell size in m (default from site.yaml)")
    ap.add_argument("--alt", action="store_true", help="use the 2023 Waimakariri collection (gaps east of Downs Rd)")
    a = ap.parse_args()
    config.ensure_dirs()
    site = config.site()
    bbox = site["domain"]["bbox_nztm"] if a.full else site["domain"]["shakedown_bbox_nztm"]
    res = a.res or (site["dem"]["resolution_m"] if a.full else site["dem"]["shakedown_resolution_m"])
    coll = site["dem"]["alt_collection"] if a.alt else site["dem"]["collection"]
    tag = "full" if a.full else "shakedown"
    out = config.DATA_DERIVED / f"dem_{tag}_{res:g}m.tif"
    terrain.fetch_dem(bbox, res, out, site["dem"]["bucket"], coll)
    dem = terrain.DEM(out)
    cx, cy = site["site"]["centre_nztm"]
    print(f"[dem] ground at site centre ({cx},{cy}): {dem.sample(cx, cy):.2f} m NZVD2016")
    for name, (x, y) in zip(("NW", "NE", "SE", "SW"), site["site"]["footprint_nztm"]):
        print(f"[dem] ground at footprint {name} corner: {dem.sample(x, y):.2f} m")


if __name__ == "__main__":
    main()
