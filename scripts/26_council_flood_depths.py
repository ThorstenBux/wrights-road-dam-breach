#!/usr/bin/env python
"""EXPLORATORY: what the councils' published flood model shows at the north embankment.

Samples ECan's "Adopted Scenarios – Depth" image service (Waimakariri District items: DHI May 2020 rain-on-grid model,
100 / 200 / 500 year, RCP 8.5 2081-2100 rainfall; no Eyre River inflow or breakout scenario) at the gauge points outside
the north embankment (config/north.yaml). Writes outputs/north_eyre/council_depths_north_embankment.csv.
Third-party model results quoted for comparison only. Screening model, not a certified assessment.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from damflood import config, north  # noqa: E402

URL = "https://gisimagery.ecan.govt.nz/arcgis/rest/services/FloodModels/Adopted_Scenarios_Depth/ImageServer/identify"
ITEMS = {"100yr": 109, "200yr": 110, "500yr": 111}     # OBJECTIDs of the Waimakariri District rasters in the mosaic


def depth(x, y, oid):
    q = urllib.parse.urlencode({"geometry": json.dumps({"x": x, "y": y, "spatialReference": {"wkid": 2193}}), "geometryType": "esriGeometryPoint",
                                "mosaicRule": json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [oid]}),
                                "returnCatalogItems": "false", "f": "json"})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=60) as r:
        v = json.load(r).get("value")
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0                                      # NoData = below the 0.05-0.1 m the published rasters keep


def main():
    site, ecfg = config.site(), config.load_yaml("north.yaml")["embankment"]
    fp = np.array(site["site"]["footprint_nztm"], float); rows = []
    for off in ecfg["gauge_offsets_m"]:
        for i, (x, y) in enumerate(north.embankment_samples(fp[0], fp[1], 2 * ecfg["sample_spacing_m"], off)):
            row = {"offset_m": off, "i": i, "E": round(x, 1), "N": round(y, 1)}
            for k, oid in ITEMS.items():
                row[f"depth_{k}_m"] = round(depth(x, y, oid), 3); time.sleep(0.1)
            rows.append(row)
    df = pd.DataFrame(rows); out = config.OUTPUTS / "north_eyre"; out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "council_depths_north_embankment.csv", index=False)
    print(df.groupby("offset_m")[[f"depth_{k}_m" for k in ITEMS]].agg(["median", "max"]).round(2).to_string())


if __name__ == "__main__":
    main()
