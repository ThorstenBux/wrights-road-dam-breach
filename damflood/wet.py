"""Wet worst case: breach (or several) on a plain that is already wet, with the Eyre River in flood.

Helpers for scripts/18_run_wet_worstcase.py, 19_wet_compare.py and 20_eyre_capacity.py: inlet timing with a
spin-up, the Eyre River centreline and mesh refinement strip, and discharge through transects of an SWW.
Exploratory and self-contained – the main pipeline does not import this module.
Screening model, not a certified assessment.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from shapely.geometry import LineString, box
from shapely.ops import linemerge, unary_union


def delayed(Q_raw: Callable[[float], float], pre_s: float, t0_s: float = 0.0, on: bool = True) -> Callable[[float], float]:
    """Breach inflow for a run with a `pre_s` spin-up: nothing before the breach opens, then the hydrograph from
    its own time `t0_s` (the cascade lag). `on=False` is the same storm without the breach (baseline run)."""
    if not on:
        return lambda t: 0.0
    return lambda t: float(Q_raw(t - pre_s + t0_s)) if t >= pre_s else 0.0


def river_line(waterways, name: str, bbox, margin: float = 0.0) -> LineString:
    """Longest piece of the named OSM river inside the bbox, ordered downstream (OSM way direction)."""
    sub = waterways[waterways["name"] == name]
    if sub.empty:
        raise ValueError(f"no waterway named '{name}'")
    u = unary_union(list(sub.geometry))
    m = u if u.geom_type == "LineString" else linemerge(u)
    W, S, E, N = bbox
    c = m.intersection(box(W + margin, S + margin, E - margin, N - margin))
    parts = [g for g in getattr(c, "geoms", [c]) if g.geom_type == "LineString"]
    return max(parts, key=lambda g: g.length)


def river_strip(line: LineString, half_width: float) -> list:
    """Refinement polygon along a river: the centreline buffered by `half_width` (outer ring, simplified)."""
    g = line.simplify(20.0).buffer(half_width, cap_style=2, join_style=2).simplify(20.0)
    return [list(c) for c in g.exterior.coords[:-1]]


def offset_line(line: LineString, dist: float) -> LineString:
    """Line parallel to `line` at `dist` m: positive = left of the downstream direction."""
    o = line.simplify(30.0).parallel_offset(abs(dist), "left" if dist > 0 else "right", join_style=2)
    if o.geom_type != "LineString":
        o = max(o.geoms, key=lambda g: g.length)
    # shapely < 2 reverses right-hand offsets; keep the downstream order either way
    if o.project(line.interpolate(0.0)) > o.project(line.interpolate(1.0, normalized=True)):
        o = LineString(list(o.coords)[::-1])
    return o


class Transects:
    """Discharge through lines of an SWW (post.SWW), positive towards the LEFT of the direction the line is drawn
    in: a cross-section drawn from the left bank to the right bank (looking downstream) counts downstream flow as
    positive; a bank line drawn downstream counts water leaving over the left bank as positive (draw the right
    bank upstream for the same).  Interpolation weights are found once, so a time series costs two matrix products per step."""

    def __init__(self, sww, lines: dict, spacing: float = 10.0):
        self.sww, self.names, self.sl = sww, list(lines), {}
        tri = sww.tri; finder = tri.get_trifinder()
        px, py, nx, ny, ds = [], [], [], [], []
        for name in self.names:
            ln = lines[name] if isinstance(lines[name], LineString) else LineString(lines[name])
            k = max(int(np.ceil(ln.length / spacing)), 1); step = ln.length / k
            i0 = len(px)
            for j in range(k):
                a, b = ln.interpolate(j * step), ln.interpolate((j + 1) * step)
                tx, ty = b.x - a.x, b.y - a.y; L = np.hypot(tx, ty) or 1.0
                px.append((a.x + b.x) / 2); py.append((a.y + b.y) / 2); nx.append(-ty / L); ny.append(tx / L); ds.append(L)
            self.sl[name] = slice(i0, len(px))
        self.px, self.py = np.array(px), np.array(py); self.nx, self.ny, self.ds = np.array(nx), np.array(ny), np.array(ds)
        t = finder(self.px, self.py); self.inside = t >= 0
        v = sww.volumes[np.where(self.inside, t, 0)]
        x, y = sww.x[v], sww.y[v]                                   # (points, 3)
        det = (y[:, 1] - y[:, 2]) * (x[:, 0] - x[:, 2]) + (x[:, 2] - x[:, 1]) * (y[:, 0] - y[:, 2])
        w0 = ((y[:, 1] - y[:, 2]) * (self.px - x[:, 2]) + (x[:, 2] - x[:, 1]) * (self.py - y[:, 2])) / det
        w1 = ((y[:, 2] - y[:, 0]) * (self.px - x[:, 2]) + (x[:, 0] - x[:, 2]) * (self.py - y[:, 2])) / det
        self.v, self.w = v, np.stack([w0, w1, 1.0 - w0 - w1], axis=1) * self.inside[:, None]

    def _at(self, vals):
        return (np.asarray(vals)[self.v] * self.w).sum(axis=1)

    def unit_flux(self, k: int) -> np.ndarray:
        """Discharge per metre (m2/s) through every sample segment at output step k."""
        ds_ = self.sww.ds.variables
        return self._at(ds_["xmomentum"][k, :]) * self.nx + self._at(ds_["ymomentum"][k, :]) * self.ny

    def integrate(self, t_from: float = 0.0) -> dict:
        """One pass over the output steps. Returns {"Q": {name: Q(t) m3/s}, "s": {name: chainage m},
        "net": {name: volume m3 per sample segment from `t_from` on}, "out": {same, positive flux only}}."""
        t = np.asarray(self.sww.time, float)
        Q = {n: np.zeros(len(t)) for n in self.names}; net = np.zeros(len(self.px)); out = np.zeros(len(self.px))
        for k in range(len(t)):
            q = self.unit_flux(k) * self.ds
            for n in self.names:
                Q[n][k] = q[self.sl[n]].sum()
            if k and t[k] > t_from:
                net += q * (t[k] - t[k - 1]); out += np.maximum(q, 0.0) * (t[k] - t[k - 1])
        return {"Q": Q, "s": {n: np.cumsum(self.ds[self.sl[n]]) - self.ds[self.sl[n]] / 2 for n in self.names},
                "net": {n: net[self.sl[n]] for n in self.names}, "out": {n: out[self.sl[n]] for n in self.names}}
