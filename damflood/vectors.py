"""Roads, buildings and water features for the model domain.

Primary source: OpenStreetMap via the osm.org `map` API (no key; ODbL).
Optional: LINZ Data Service WFS (needs LINZ_API_KEY) for NZ Building Outlines
(layer 101290) and NZ Road Centrelines Topo50 (layer 50329) – authoritative
layers to use for a certified assessment.
"""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import numpy as np
import requests
from pyproj import Transformer
from shapely.geometry import LineString, Polygon

UA = {"User-Agent": "tripod-digital-damflood/0.1 (dam-breach flood study; thorsten@tripod-digital.co.nz)"}
_TO_LL = Transformer.from_crs(2193, 4326, always_xy=True)


def bbox_nztm_to_ll(bbox):
    W, S, E, N = bbox
    lons, lats = _TO_LL.transform([W, E, E, W], [S, S, N, N])
    return min(lons), min(lats), max(lons), max(lats)


def _fetch_tile(api: str, w, s, e, n, depth=0) -> list[ET.Element]:
    url = f"{api}?bbox={w:.5f},{s:.5f},{e:.5f},{n:.5f}"
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=180)
        except requests.exceptions.RequestException as exc:   # dropped connection / truncated body
            print(f"[osm] {exc.__class__.__name__} on attempt {attempt + 1}, retrying")
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 200:
            return [ET.fromstring(r.content)]
        if r.status_code in (400, 509) and depth < 4:  # too many nodes -> split
            mw, mn = (w + e) / 2, (s + n) / 2
            return (_fetch_tile(api, w, s, mw, mn, depth + 1) + _fetch_tile(api, mw, s, e, mn, depth + 1)
                    + _fetch_tile(api, w, mn, mw, n, depth + 1) + _fetch_tile(api, mw, mn, e, n, depth + 1))
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"OSM map API failed for {url}")


def fetch_osm(bbox_nztm, out_gpkg: Path, api: str, tile_deg: float = 0.05, verbose=True) -> Path:
    w, s, e, n = bbox_nztm_to_ll(bbox_nztm)
    roots: list[ET.Element] = []
    xs = np.arange(w, e, tile_deg); ys = np.arange(s, n, tile_deg)
    for x0 in xs:
        for y0 in ys:
            roots += _fetch_tile(api, x0, y0, min(x0 + tile_deg, e), min(y0 + tile_deg, n))
            if verbose:
                print(f"[osm] tile {x0:.3f},{y0:.3f} ok ({len(roots)} chunks)")
    nodes, ways = {}, {}
    for root in roots:
        for nd in root.findall("node"):
            nodes[nd.get("id")] = (float(nd.get("lon")), float(nd.get("lat")))
        for w_ in root.findall("way"):
            tags = {t.get("k"): t.get("v") for t in w_.findall("tag")}
            ways[w_.get("id")] = (tags, [x.get("ref") for x in w_.findall("nd")])
    roads, bldg, water, wways = [], [], [], []
    for wid, (tags, refs) in ways.items():
        pts = [nodes[r] for r in refs if r in nodes]
        if len(pts) < 2:
            continue
        closed = refs[0] == refs[-1] and len(pts) >= 4
        if "highway" in tags:
            roads.append({"osm_id": wid, "name": tags.get("name"), "highway": tags["highway"],
                          "surface": tags.get("surface"), "geometry": LineString(pts)})
        if "building" in tags and closed:
            bldg.append({"osm_id": wid, "building": tags["building"], "name": tags.get("name"),
                         "addr": tags.get("addr:housenumber"), "geometry": Polygon(pts)})
        if closed and (tags.get("natural") == "water" or tags.get("landuse") == "reservoir"):
            water.append({"osm_id": wid, "kind": tags.get("water") or tags.get("landuse"),
                          "name": tags.get("name"), "geometry": Polygon(pts)})
        if "waterway" in tags and not closed:
            wways.append({"osm_id": wid, "waterway": tags["waterway"], "name": tags.get("name"),
                          "geometry": LineString(pts)})
    out_gpkg.parent.mkdir(parents=True, exist_ok=True)
    if out_gpkg.exists():
        out_gpkg.unlink()
    for layer, rows in (("roads", roads), ("buildings", bldg), ("water", water), ("waterways", wways)):
        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326") if rows else \
            gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
        gdf.to_crs(2193).to_file(out_gpkg, layer=layer, driver="GPKG")
        if verbose:
            print(f"[osm] layer {layer}: {len(gdf)} features")
    return out_gpkg


def load(gpkg: Path, layer: str) -> gpd.GeoDataFrame:
    return gpd.read_file(gpkg, layer=layer)


def fetch_linz_wfs(layer_id: int, bbox_nztm, out_path: Path, api_key: str | None = None) -> Path:
    """Download a LINZ Data Service layer for a bbox as GeoJSON (needs API key)."""
    key = api_key or os.environ.get("LINZ_API_KEY")
    if not key:
        raise RuntimeError("Set LINZ_API_KEY (create one at https://data.linz.govt.nz/my/api/)")
    W, S, E, N = bbox_nztm
    url = (f"https://data.linz.govt.nz/services;key={key}/wfs?service=WFS&version=2.0.0"
           f"&request=GetFeature&typeNames=layer-{layer_id}&outputFormat=json&srsName=EPSG:2193"
           f"&bbox={W},{S},{E},{N},EPSG:2193")
    r = requests.get(url, headers=UA, timeout=300)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path
