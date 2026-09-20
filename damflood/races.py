"""Water races in the 2D model: race chains from OSM, thalweg snapping on the LiDAR, crossing detection,
bed conditioning and a mesh with breaklines along the races.

Exploratory and self-contained – the main pipeline does not import this module (it reuses damflood.terrain
and damflood.model read-only).  Screening model, not a certified assessment.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from shapely.geometry import LineString, box

from .terrain import DEM


# --------------------------------------------------------------------------- #
# Race chains from the OSM waterways layer
# --------------------------------------------------------------------------- #
def follow_chain(waterways, start_osm_id: str, tol: float = 3.0) -> LineString:
    """Follow OSM ways downstream (end node -> start node of the next way) from `start_osm_id`."""
    w = waterways.reset_index(drop=True)
    key = lambda c: (round(c[0] / tol), round(c[1] / tol))
    starts = defaultdict(list)
    for i, g in enumerate(w.geometry):
        starts[key(g.coords[0])].append(i)
    hit = w.index[w.osm_id.astype(str) == str(start_osm_id)]
    if not len(hit):
        raise KeyError(f"OSM way {start_osm_id} not in the waterways layer")
    i, seen, pts = int(hit[0]), set(), []
    while i is not None and i not in seen:
        seen.add(i)
        c = list(w.geometry[i].coords)
        pts += c if not pts else c[1:]
        nxt = [j for j in starts.get(key(c[-1]), []) if j not in seen]
        i = nxt[0] if nxt else None
    return LineString([(x, y) for x, y, *_ in pts])


def clip_to_bbox(line: LineString, bbox, margin: float = 30.0) -> LineString:
    """First piece of `line` inside the bbox shrunk by `margin` (breaklines must not touch the boundary)."""
    W, S, E, N = bbox
    part = line.intersection(box(W + margin, S + margin, E - margin, N - margin))
    if part.geom_type == "MultiLineString":
        start = np.array(line.coords[0][:2])
        part = min(part.geoms, key=lambda g: np.hypot(*(np.array(g.coords[0][:2]) - start)))
    return part


# --------------------------------------------------------------------------- #
# Thalweg on the LiDAR
# --------------------------------------------------------------------------- #
@dataclass
class Thalweg:
    name: str
    s: np.ndarray               # chainage, m
    xy: np.ndarray              # snapped thalweg points (n, 2), NZTM
    z_raw: np.ndarray           # LiDAR level at the snapped points (road fills included)
    z_open: np.ndarray          # downstream-falling envelope = bed cut through the crossings
    ground: np.ndarray          # general ground level beside the race (median of the cross-section ends)
    crossings: list = field(default_factory=list)   # [{"s0","s1","x","y","hump_m"}]

    @property
    def line(self) -> LineString:
        return LineString(self.xy)

    def bed_edges(self, width: float) -> tuple[np.ndarray, np.ndarray]:
        """Left and right bed-edge lines, `width` apart.  Used as the mesh breaklines: with a single centre
        line every channel triangle has a vertex on the bank, which lifts the (centroid) bed by 1/3-2/3 of the
        bank height and chokes a small race; between two edge lines the triangles sit flat on the bed."""
        t = np.gradient(self.xy, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
        n = np.c_[-t[:, 1], t[:, 0]] * width / 2.0
        return self.xy + n, self.xy - n


def snap_thalweg(dem: DEM, line: LineString, name: str, station: float = 5.0, search: float = 14.0,
                 hump: float = 0.4) -> Thalweg:
    """Walk the OSM line every `station` m; at each station take the lowest LiDAR point across the line
    within ±`search` m, smooth the lateral offsets (so the snapped line does not zig-zag), and find the
    crossings: stretches where the bed rises more than `hump` above the downstream-falling envelope."""
    n = max(int(line.length // station), 2)
    s = np.linspace(0.0, line.length, n + 1)
    p = np.array([line.interpolate(v).coords[0][:2] for v in s])
    t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.c_[-t[:, 1], t[:, 0]]
    step = max(dem.res, 1.0)
    off = np.arange(-search, search + step / 2, step)
    X = p[:, 0, None] + nrm[:, 0, None] * off[None, :]
    Y = p[:, 1, None] + nrm[:, 1, None] * off[None, :]
    Z = dem.sample(X.ravel(), Y.ravel()).reshape(X.shape)
    k = median_filter(np.argmin(Z, axis=1).astype(float), size=9, mode="nearest")
    k = np.clip(np.rint(k).astype(int), 0, len(off) - 1)
    # lowest of the smoothed position and its neighbours (the median can land on the bank)
    kk = np.clip(k[:, None] + np.array([-1, 0, 1])[None, :], 0, len(off) - 1)
    best = np.take_along_axis(kk, np.argmin(np.take_along_axis(Z, kk, 1), axis=1)[:, None], 1)[:, 0]
    rows = np.arange(len(s))
    xy = np.c_[X[rows, best], Y[rows, best]]
    # smooth the snapped line (sharp kinks make sliver triangles) and re-space it evenly at `station`
    pad = np.r_[np.repeat(xy[:1], 3, 0), xy, np.repeat(xy[-1:], 3, 0)]
    xy = np.stack([np.convolve(pad[:, i], np.ones(7) / 7, mode="valid") for i in (0, 1)], axis=1)
    smooth = LineString(xy)
    m = max(int(round(smooth.length / station)), 2)
    xy = np.array([smooth.interpolate(v).coords[0] for v in np.linspace(0.0, smooth.length, m + 1)])
    s = np.linspace(0.0, smooth.length, m + 1)
    # bed level: lowest LiDAR value within one cell of the smoothed line
    jit = np.array([[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) * dem.res
    z_raw = np.min([dem.sample(xy[:, 0] + dx, xy[:, 1] + dy) for dx, dy in jit], axis=0)
    ground = np.interp(s, np.linspace(0.0, smooth.length, len(Z)), np.median(np.c_[Z[:, :3], Z[:, -3:]], axis=1))
    z_open = np.minimum.accumulate(z_raw)
    rise = z_raw - z_open
    crossings, i = [], 0
    while i < len(s):
        if rise[i] > hump:
            j = i
            while j + 1 < len(s) and rise[j + 1] > 0.1:
                j += 1
            m = i + int(np.argmax(rise[i:j + 1]))
            crossings.append({"s0": float(s[max(i - 1, 0)]), "s1": float(s[min(j + 1, len(s) - 1)]),
                              "x": float(xy[m, 0]), "y": float(xy[m, 1]), "hump_m": float(rise[m])})
            i = j + 1
        else:
            i += 1
    return Thalweg(name, s, xy, z_raw, z_open, ground, crossings)


def burn_bed(dem: DEM, arr: np.ndarray, th: Thalweg, bed_width: float, crossings_open: bool) -> np.ndarray:
    """Lower the DEM to the race bed along the snapped thalweg over `bed_width` (never raises a cell).
    crossings_open=True uses the downstream-falling envelope (fills cut through); False keeps the LiDAR
    level at the crossings, so only the channel between them is made continuous on the model grid."""
    z = th.z_open if crossings_open else th.z_raw
    out = arr.copy()
    half = bed_width / 2.0 + 1.5 * dem.res   # wider than the mesh bed so its edge vertices sample the bed level
    # densify so every cell along the line is touched
    sd = np.arange(0.0, th.s[-1], dem.res / 2.0)
    x = np.interp(sd, th.s, th.xy[:, 0]); y = np.interp(sd, th.s, th.xy[:, 1]); zz = np.interp(sd, th.s, z)
    if not crossings_open:   # blocked culverts: leave the LiDAR fill untouched over each crossing
        keep = np.ones(len(sd), bool)
        for c in th.crossings:
            keep &= (sd < c["s0"] - half) | (sd > c["s1"] + half)   # the burn disc must not reach into the fill
        x, y, zz = x[keep], y[keep], zz[keep]
    r = int(np.ceil(half / dem.res))
    col = np.floor((x - dem.transform.c) / dem.transform.a).astype(int)
    row = np.floor((y - dem.transform.f) / dem.transform.e).astype(int)
    for dr in range(-r, r + 1):
        for dc in range(-r, r + 1):
            if np.hypot(dr, dc) * dem.res > half + 1e-9:
                continue
            rr, cc = row + dr, col + dc
            ok = (rr >= 0) & (rr < out.shape[0]) & (cc >= 0) & (cc < out.shape[1])
            np.minimum.at(out, (rr[ok], cc[ok]), zz[ok].astype(out.dtype))
    return out


def bankfull_capacity(th: Thalweg, bed_width: float, n: float, side_slope: float = 1.5) -> dict:
    """Rough Manning bank-full capacity (median over the race) – a plausibility check of the dewatering rates."""
    depth = np.clip(th.ground - th.z_open, 0.0, None)
    d = float(np.median(depth))
    S = float((th.z_open[0] - th.z_open[-1]) / max(th.s[-1], 1.0))
    A = bed_width * d + side_slope * d * d
    P = bed_width + 2 * d * np.hypot(1.0, side_slope)
    Q = A * (A / P) ** (2 / 3) * np.sqrt(max(S, 1e-6)) / n if d > 0 else 0.0
    return {"median_depth_m": d, "mean_slope": S, "bankfull_Q_m3s": float(Q)}


# --------------------------------------------------------------------------- #
# Mesh with breaklines along the races
# --------------------------------------------------------------------------- #
def build_domain(dem_path: Path, bbox, mesh: dict, refine_polys: list[tuple], breaklines: list[np.ndarray],
                 run_dir: Path, name: str, friction: float, race_friction: float | None = None,
                 race_halfwidths: list[float] | None = None, verbose: bool = True):
    """As damflood.model.build_domain, plus `breaklines` (absolute NZTM point arrays): mesh vertices are placed
    on the race thalwegs at the station spacing, which also grades the triangles down to that size there."""
    import anuga

    from .model import _prepare_refinements, _rect, _rel

    dem = DEM(dem_path)
    x0, y0 = float(bbox[0]), float(bbox[1])
    georef = anuga.Geo_reference(xllcorner=x0, yllcorner=y0)
    interior = [(_rel(p, x0, y0), float(a)) for p, a in _prepare_refinements(refine_polys, bbox)]
    # ANUGA adds breakline points without a geo-reference, i.e. it expects ABSOLUTE coordinates here
    bl = [[[float(x), float(y)] for x, y in b] for b in breaklines]
    t0 = time.time()
    domain = anuga.create_domain_from_regions(
        _rel(_rect(bbox), x0, y0), boundary_tags={"outer": [0, 1, 2, 3]},
        maximum_triangle_area=float(mesh["max_area_m2"]), interior_regions=interior, breaklines=bl,
        poly_geo_reference=georef, mesh_geo_reference=georef, verbose=False)
    domain.set_name(name)
    domain.set_datadir(str(run_dir))
    domain.set_flow_algorithm(mesh.get("flow_algorithm", "DE0"))
    domain.set_minimum_allowed_height(0.01)
    domain.set_store_vertices_uniquely(False)
    domain.set_quantities_to_be_stored({"elevation": 1, "stage": 2, "xmomentum": 2, "ymomentum": 2})
    if verbose:
        a = domain.areas
        print(f"[races] mesh: {domain.number_of_triangles} triangles in {time.time()-t0:.0f}s; "
              f"area min/median/max {a.min():.1f}/{np.median(a):.0f}/{a.max():.0f} m2")

    domain.set_quantity("elevation", function=lambda x, y: dem.sample(np.asarray(x) + x0, np.asarray(y) + y0),
                        location="vertices")
    n = np.full(domain.number_of_triangles, float(friction))
    if race_friction is not None:
        c = domain.get_centroid_coordinates(absolute=True)
        from shapely import points
        for b_, hw in zip(breaklines, race_halfwidths or [3.0] * len(breaklines)):
            ln = LineString(b_)
            W, S, E, N = ln.bounds
            near = np.nonzero((c[:, 0] > W - hw) & (c[:, 0] < E + hw) & (c[:, 1] > S - hw) & (c[:, 1] < N + hw))[0]
            if near.size:
                n[near[ln.distance(points(c[near])) <= hw]] = float(race_friction)
    domain.set_quantity("friction", n, location="centroids")
    domain.set_quantity("stage", expression="elevation")
    domain.set_boundary({"outer": anuga.Transmissive_boundary(domain)})
    return domain, (x0, y0)
