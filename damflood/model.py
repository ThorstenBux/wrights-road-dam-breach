"""ANUGA 2D shallow-water flood routing of a breach hydrograph.

Approach (baseline): the reservoir is *not* resolved in the 2D domain.  The
breach outflow hydrograph from `breach.py` is injected with an
`Inlet_operator` on a small polygon just outside the embankment toe at the
breach location, and the pond footprint is represented as a solid block at
crest level.  This is the usual "hydrograph inflow" method and keeps breach
assumptions explicit and separately reviewable.

Coordinates: the mesh is built in local coordinates relative to the SW corner
of the domain bbox (x0, y0); ANUGA stores the offset as `geo_reference` so the
SWW output can be georeferenced back to NZTM (EPSG:2193).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

import numpy as np

from .terrain import DEM


def _rect(bbox):
    W, S, E, N = bbox
    return [[W, S], [E, S], [E, N], [W, N]]


def _rel(poly, x0, y0):
    return [[float(x) - x0, float(y) - y0] for x, y in poly]


def _prepare_refinements(refine_polys, bbox, margin=60.0):
    """Clip refinement polygons to the domain (ANUGA requires interior regions strictly
    inside the bounding polygon) and make them mutually non-overlapping (earlier entries
    take precedence).  Returns [(coords, area), ...] in absolute coordinates."""
    from shapely.geometry import Polygon, box
    W, S, E, N = bbox
    clip = box(W + margin, S + margin, E - margin, N - margin)
    taken = None
    out = []
    for poly, area in refine_polys:
        g = Polygon(poly).buffer(0).intersection(clip)
        if taken is not None:
            g = g.difference(taken.buffer(1.0))
        parts = [g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]
        for q in parts:
            if q.area < 10 * area:
                continue
            if q.interiors:  # ANUGA interior regions cannot have holes: use the outer ring
                q = Polygon(q.exterior)
            q = q.simplify(5.0)
            out.append(([list(c) for c in q.exterior.coords[:-1]], float(area)))
        taken = g if taken is None else taken.union(g)
    return out


def build_domain(dem_path: Path, bbox, mesh: dict, refine_polys: list[tuple], run_dir: Path,
                 name: str, friction: float, verbose: bool = True):
    """Create the ANUGA domain.

    mesh: {"max_area_m2": coarse triangle area}
    refine_polys: [(polygon_xy_abs, max_area_m2), ...]  (clipped / de-overlapped here)
    """
    import anuga

    dem = DEM(dem_path)
    W, S, E, N = bbox
    x0, y0 = float(W), float(S)
    georef = anuga.Geo_reference(xllcorner=x0, yllcorner=y0)
    bounding = _rel(_rect(bbox), x0, y0)
    interior = [(_rel(p, x0, y0), float(a)) for p, a in _prepare_refinements(refine_polys, bbox)]
    if verbose:
        print(f"[model] {len(interior)} refinement regions after clipping: areas {[a for _, a in interior]}")
    t0 = time.time()
    domain = anuga.create_domain_from_regions(
        bounding, boundary_tags={"outer": [0, 1, 2, 3]},
        maximum_triangle_area=float(mesh["max_area_m2"]), interior_regions=interior,
        poly_geo_reference=georef, mesh_geo_reference=georef, verbose=verbose)
    domain.set_name(name)
    domain.set_datadir(str(run_dir))
    domain.set_flow_algorithm(mesh.get("flow_algorithm", "DE0"))
    domain.set_minimum_allowed_height(0.01)
    domain.set_store_vertices_uniquely(False)
    domain.set_quantities_to_be_stored({"elevation": 1, "stage": 2, "xmomentum": 2, "ymomentum": 2})
    if verbose:
        print(f"[model] mesh: {domain.number_of_triangles} triangles in {time.time()-t0:.0f}s; "
              f"geo_reference xll={domain.geo_reference.get_xllcorner()} yll={domain.geo_reference.get_yllcorner()}")

    def elev(x, y):
        return dem.sample(np.asarray(x) + x0, np.asarray(y) + y0)

    domain.set_quantity("elevation", function=elev, location="vertices")
    domain.set_quantity("friction", float(friction))
    domain.set_quantity("stage", expression="elevation")
    domain.set_boundary({"outer": anuga.Transmissive_boundary(domain)})
    return domain, (x0, y0)


def add_inlet(domain, offset, polygon_xy_abs, Q: Callable[[float], float], label="breach"):
    """Inject Q(t) over a polygon.  ANUGA's Region/Inlet_operator select mesh
    cells using ABSOLUTE coordinates (domain.get_centroid_coordinates(absolute=True)),
    so the polygon is passed in NZTM as-is.  Verifies that cells were captured."""
    import anuga
    poly = [[float(x), float(y)] for x, y in polygon_xy_abs]
    op = anuga.Inlet_operator(domain, poly, Q=Q, label=label, verbose=False)
    area = float(op.inlet.get_area())
    if area <= 0:
        raise RuntimeError("Inlet polygon did not capture any mesh cells – check location vs domain bbox")
    print(f"[model] inlet '{label}' area {area:.0f} m2 over {len(op.inlet.triangle_indices)} triangles")
    return op


def run(domain, Q: Callable[[float], float], finaltime: float, yieldstep: float, log_path: Path,
        verbose: bool = True) -> Path:
    t0 = time.time()
    rows = []
    for t in domain.evolve(yieldstep=yieldstep, finaltime=finaltime):
        stage = domain.quantities["stage"].centroid_values
        elev = domain.quantities["elevation"].centroid_values
        depth = np.maximum(stage - elev, 0.0)
        areas = domain.areas
        vol = float((depth * areas).sum())
        wet = float((areas[depth > 0.05]).sum())
        rows.append({"t_s": float(t), "Q_in_m3s": float(Q(t)), "volume_m3": vol,
                     "wet_area_km2": wet / 1e6, "max_depth_m": float(depth.max()),
                     "wall_s": time.time() - t0})
        if verbose:
            print(f"[model] t={t/3600:6.2f} h  Q={Q(t):8.1f} m3/s  V={vol/1e6:6.3f} Mm3  "
                  f"wet={wet/1e6:6.2f} km2  dmax={depth.max():5.2f} m  wall={time.time()-t0:6.0f}s", flush=True)
    log_path.write_text(json.dumps(rows, indent=1))
    return Path(domain.get_datadir()) / f"{domain.get_name()}.sww"
