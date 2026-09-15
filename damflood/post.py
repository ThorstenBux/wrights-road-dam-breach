"""Post-processing of ANUGA SWW output into hazard products.

Produces (EPSG:2193 GeoTIFFs at the requested cell size):
  max_depth, max_speed, max_dv (depth x speed, same timestep), arrival_time
  (first time depth > threshold, hours), hazard class H1-H6 (ARR 2019 Book 6
  thresholds, as used by NZSOLD 2024 Module 2 Table 2.5 / Figure 2.9).
Plus tables: roads (arrival time and max depth per named road), buildings
(max depth, DV, hazard class, "at risk" flag), and a PAR estimate.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from matplotlib.tri import LinearTriInterpolator, Triangulation
from netCDF4 import Dataset
from rasterio.transform import from_origin
from shapely.geometry import Point

# ARR 2019 (Smith et al. 2014) hazard thresholds: (max D*V, max D, max V)
ARR_THRESHOLDS = {1: (0.3, 0.3, 2.0), 2: (0.6, 0.5, 2.0), 3: (0.6, 1.2, 2.0),
                  4: (1.0, 2.0, 2.0), 5: (4.0, 4.0, 4.0)}


def hazard_class(D, V):
    D = np.asarray(D, float); V = np.asarray(V, float); DV = D * V
    cls = np.full(D.shape, 6, dtype="int16")
    for h in (5, 4, 3, 2, 1):
        dv, d, v = ARR_THRESHOLDS[h]
        cls[(DV <= dv) & (D <= d) & (V <= v)] = h
    cls[D <= 0.0] = 0
    return cls


class SWW:
    def __init__(self, path: Path):
        self.ds = Dataset(path)
        self.xll = float(getattr(self.ds, "xllcorner", 0.0)); self.yll = float(getattr(self.ds, "yllcorner", 0.0))
        self.x = self.ds.variables["x"][:] + self.xll
        self.y = self.ds.variables["y"][:] + self.yll
        self.volumes = self.ds.variables["volumes"][:]
        self.time = self.ds.variables["time"][:]
        self.elev = self.ds.variables["elevation"][:]
        if self.elev.ndim == 2:
            self.elev = self.elev[0]
        self.tri = Triangulation(self.x, self.y, self.volumes)

    def maxima(self, depth_threshold=0.1, min_depth_for_speed=0.05, t_breach=0.0):
        """Per-vertex maxima over time.  `t_breach` (s) is the moment the breach opens: times are reported
        relative to it, and arrival is the first time the depth exceeds the pre-breach depth by more than
        `depth_threshold` (so rain or a river already flowing does not count as the breach wave arriving)."""
        n = len(self.x)
        dmax = np.zeros(n); vmax = np.zeros(n); dvmax = np.zeros(n)
        arrival = np.full(n, np.nan); tpeak = np.zeros(n)
        st, xm, ym = self.ds.variables["stage"], self.ds.variables["xmomentum"], self.ds.variables["ymomentum"]
        k0 = int(np.searchsorted(self.time, t_breach - 1e-6)) if t_breach > 0 else 0
        base = np.maximum(st[min(k0, len(self.time) - 1), :] - self.elev, 0.0) if t_breach > 0 else np.zeros(n)
        for k, t in enumerate(self.time):
            t = t - t_breach
            d = np.maximum(st[k, :] - self.elev, 0.0)
            with np.errstate(divide="ignore", invalid="ignore"):
                v = np.where(d > min_depth_for_speed, np.hypot(xm[k, :], ym[k, :]) / np.maximum(d, 1e-6), 0.0)
            dv = d * v
            newpeak = d > dmax
            tpeak[newpeak] = t
            dmax = np.maximum(dmax, d); vmax = np.maximum(vmax, v); dvmax = np.maximum(dvmax, dv)
            arr = np.isnan(arrival) & (d - base > depth_threshold) & (t >= 0)
            arrival[arr] = t
        return {"max_depth": dmax, "max_speed": vmax, "max_dv": dvmax,
                "arrival_h": arrival / 3600.0, "t_peak_h": tpeak / 3600.0,
                "hazard": hazard_class(dmax, vmax).astype(float)}

    def grid(self, values, bbox, res):
        W, S, E, N = bbox
        xs = np.arange(W + res / 2, E, res); ys = np.arange(N - res / 2, S, -res)
        X, Y = np.meshgrid(xs, ys)
        interp = LinearTriInterpolator(self.tri, values)
        Z = interp(X, Y)
        arr = np.where(np.ma.getmaskarray(Z), np.nan, np.ma.filled(Z, np.nan))
        return arr, from_origin(W, N, res, res)

    def timeseries(self, points_xy, depth_only=False) -> pd.DataFrame:
        interp_e = LinearTriInterpolator(self.tri, self.elev)
        px = np.array([p[0] for p in points_xy]); py = np.array([p[1] for p in points_xy])
        e = np.ma.filled(interp_e(px, py), np.nan)
        st = self.ds.variables["stage"]
        rows = []
        for k, t in enumerate(self.time):
            s = np.ma.filled(LinearTriInterpolator(self.tri, st[k, :])(px, py), np.nan)
            rows.append([t] + list(np.maximum(s - e, 0.0)))
        return pd.DataFrame(rows, columns=["t_s"] + [f"p{i}" for i in range(len(points_xy))])


def write_tif(path: Path, arr, transform, nodata=-9999.0, dtype="float32"):
    a = np.where(np.isfinite(arr), arr, nodata).astype(dtype)
    with rasterio.open(path, "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1,
                       dtype=dtype, crs="EPSG:2193", transform=transform, nodata=nodata,
                       compress="deflate", tiled=True) as dst:
        dst.write(a, 1)
    return path


def sample_raster(path: Path, xs, ys):
    with rasterio.open(path) as ds:
        vals = np.array([v[0] for v in ds.sample(zip(xs, ys))], dtype=float)
        vals[vals == ds.nodata] = np.nan
    return vals


def road_table(roads: gpd.GeoDataFrame, rasters: dict, names: list[str], spacing=25.0) -> pd.DataFrame:
    out = []
    for name in names:
        sub = roads[roads["name"].fillna("").str.lower() == name.lower()]
        if sub.empty:
            out.append({"road": name, "note": "not in roads layer"}); continue
        pts = []
        for geom in sub.geometry:
            L = geom.length
            for d in np.arange(0, L, spacing):
                p = geom.interpolate(d); pts.append((p.x, p.y))
        if not pts:
            continue
        xs, ys = zip(*pts)
        dep = sample_raster(rasters["max_depth"], xs, ys); arr = sample_raster(rasters["arrival_h"], xs, ys)
        wet = np.isfinite(dep) & (dep > 0.1)
        rec = {"road": name, "sample_points": len(pts), "points_inundated_gt_0.1m": int(wet.sum()),
               "first_arrival_h": float(np.nanmin(arr)) if np.isfinite(arr).any() else np.nan,
               "max_depth_m": float(np.nanmax(dep)) if np.isfinite(dep).any() else 0.0}
        if wet.any():
            i = int(np.nanargmin(np.where(wet, arr, np.nan)))
            rec["first_arrival_E"], rec["first_arrival_N"] = xs[i], ys[i]
        out.append(rec)
    return pd.DataFrame(out)


def building_table(bldg: gpd.GeoDataFrame, rasters: dict, persons_per_dwelling=2.5,
                   at_risk_depth=0.5) -> tuple[pd.DataFrame, dict]:
    if bldg.empty:
        return pd.DataFrame(), {"buildings": 0}
    c = bldg.geometry.centroid
    dep = sample_raster(rasters["max_depth"], c.x, c.y)
    spd = sample_raster(rasters["max_speed"], c.x, c.y)
    dv = sample_raster(rasters["max_dv"], c.x, c.y)
    arr = sample_raster(rasters["arrival_h"], c.x, c.y)
    dep = np.nan_to_num(dep); spd = np.nan_to_num(spd); dv = np.nan_to_num(dv)
    hz = hazard_class(dep, spd)
    df = pd.DataFrame({"osm_id": bldg["osm_id"].values, "building": bldg.get("building", pd.Series([None]*len(bldg))).values,
                       "E": c.x.round(0), "N": c.y.round(0), "max_depth_m": dep.round(2), "max_speed_ms": spd.round(2),
                       "max_dv_m2s": dv.round(2), "hazard_H": hz, "arrival_h": np.round(arr, 2)})
    df["at_risk_depth0.5"] = df["max_depth_m"] >= at_risk_depth
    df["at_risk_gtH2"] = df["hazard_H"] >= 3
    dwelling_like = df["building"].isin(["house", "residential", "yes", "detached", "farm", "bungalow", "apartments"]) | df["building"].isna()
    summary = {
        "buildings": int(len(df)),
        "buildings_inundated_gt_0.1m": int((df["max_depth_m"] > 0.1).sum()),
        "buildings_at_risk_depth_ge_0.5m": int(df["at_risk_depth0.5"].sum()),
        "buildings_at_risk_hazard_gt_H2": int(df["at_risk_gtH2"].sum()),
        "dwelling_like_at_risk_gt_H2": int((df["at_risk_gtH2"] & dwelling_like).sum()),
        "PAR_estimate_gtH2_x_persons": float((df["at_risk_gtH2"] & dwelling_like).sum() * persons_per_dwelling),
        "PAR_estimate_depth0.5_x_persons": float((df["at_risk_depth0.5"] & dwelling_like).sum() * persons_per_dwelling),
        "persons_per_dwelling": persons_per_dwelling,
        "note": "Screening estimate from OSM building footprints; NZSOLD PAR requires occupancy per Table 2.7 and no evacuation credit.",
    }
    return df, summary


def _road_labels(ax, roads: gpd.GeoDataFrame, bounds, priority: list[str], max_labels: int = 70):
    """Label named roads at the midpoint of their longest piece, rotated along the road."""
    from shapely.geometry import box
    clipped = gpd.clip(roads[roads["name"].notna()], box(bounds.left, bounds.bottom, bounds.right, bounds.top))
    if clipped.empty:
        return
    best = {}
    for _, r in clipped.iterrows():
        geoms = [r.geometry] if r.geometry.geom_type == "LineString" else list(getattr(r.geometry, "geoms", []))
        for g in geoms:
            if g.length > best.get(r["name"], (0, None))[0]:
                best[r["name"]] = (g.length, g)
    names = sorted(best, key=lambda n: ((priority.index(n) if n in priority else 99), -best[n][0]))[:max_labels]
    for name in names:
        g = best[name][1]
        p = g.interpolate(0.5, normalized=True); p2 = g.interpolate(min(0.5 + 200 / max(g.length, 1), 1.0), normalized=True)
        p1 = g.interpolate(max(0.5 - 200 / max(g.length, 1), 0.0), normalized=True)
        ang = np.degrees(np.arctan2(p2.y - p1.y, p2.x - p1.x))
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
        key = name in priority
        ax.text(p.x, p.y, name.replace(" Road", " Rd"), rotation=ang, rotation_mode="anchor", ha="center", va="center",
                fontsize=5.2 if key else 4.2, color="#1d2a3a" if key else "#4a5566", fontweight="bold" if key else "normal",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.65), zorder=6)


def quick_map(png: Path, depth_tif: Path, footprint=None, roads: gpd.GeoDataFrame | None = None,
              title: str = "", priority_roads: list[str] | None = None, breach_xy=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    with rasterio.open(depth_tif) as ds:
        a = ds.read(1); a = np.where(a == ds.nodata, np.nan, a); b = ds.bounds
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(b.left, b.right); ax.set_ylim(b.bottom, b.top)
    im = ax.imshow(np.ma.masked_invalid(a), extent=(b.left, b.right, b.bottom, b.top), cmap="Blues",
                   vmin=0, vmax=max(1.0, float(np.nanpercentile(a, 99)) if np.isfinite(a).any() else 1.0), zorder=3)
    if roads is not None and not roads.empty:
        rc = gpd.clip(roads, box(b.left, b.bottom, b.right, b.top))
        major = rc[rc["highway"].isin(["primary", "secondary", "tertiary", "unclassified", "residential"])]
        minor = rc[~rc.index.isin(major.index)]
        if not minor.empty: minor.plot(ax=ax, color="0.75", linewidth=0.3, zorder=4)
        if not major.empty: major.plot(ax=ax, color="0.35", linewidth=0.6, zorder=5)
        _road_labels(ax, rc, b, priority_roads or [])
    if footprint is not None:
        xs, ys = zip(*(footprint + [footprint[0]])); ax.plot(xs, ys, "-", color="#e8542a", lw=1.4, zorder=7, label="pond footprint")
    if breach_xy is not None:
        pts = breach_xy if np.ndim(breach_xy) == 2 else [breach_xy]
        for i, (bx, by) in enumerate(pts):
            ax.plot(bx, by, marker="v", color="#e8542a", ms=7, zorder=8, label="breach" if i == 0 else None)
    ax.set_title(title); ax.set_xlabel("NZTM E (m)"); ax.set_ylabel("NZTM N (m)"); ax.set_aspect("equal")
    ax.ticklabel_format(style="plain", useOffset=False); ax.tick_params(labelsize=7)
    ax.legend(loc="lower right", fontsize=7, frameon=True)
    fig.colorbar(im, ax=ax, label="max depth (m)", shrink=0.8); fig.tight_layout(); fig.savefig(png, dpi=170); plt.close(fig)
    return png
