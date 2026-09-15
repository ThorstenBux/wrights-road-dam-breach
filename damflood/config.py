"""Configuration loading and project paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_RAW = ROOT / "data" / "raw"
DATA_DERIVED = ROOT / "data" / "derived"
OUTPUTS = ROOT / "outputs"


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, "r") as fh:
        return yaml.safe_load(fh)


def site() -> dict:
    return load_yaml("site.yaml")


def dam() -> dict:
    return load_yaml("dam.yaml")


def scenario(name: str) -> dict:
    cfg = dam()
    try:
        sc = cfg["scenarios"][name]
    except KeyError as exc:
        raise KeyError(f"Unknown scenario '{name}'. Available: {list(cfg['scenarios'])}") from exc
    sc = dict(sc)
    sc["name"] = name
    return sc


MODES = ("shakedown", "extended", "production")


def mode_settings(mode: str) -> dict:
    """Domain bbox, DEM resolution/path and mesh/run settings for a model tier.
    shakedown: small domain (to Browns Road), coarse;  extended: full domain (to Diversion Road) at the
    shakedown resolution and mesh;  production: full domain, fine mesh."""
    if mode not in MODES:
        raise KeyError(f"Unknown mode '{mode}'. Available: {MODES}")
    s = site()
    if mode == "shakedown":
        bbox, res, tag = s["domain"]["shakedown_bbox_nztm"], s["dem"]["shakedown_resolution_m"], "shakedown"
    elif mode == "extended":
        bbox, res, tag = s["domain"]["bbox_nztm"], s["dem"].get("extended_resolution_m", s["dem"]["shakedown_resolution_m"]), "full"
    else:
        bbox, res, tag = s["domain"]["bbox_nztm"], s["dem"]["resolution_m"], "full"
    return {"mode": mode, "bbox": bbox, "dem_res": res, "dem_tag": tag,
            "dem_path": DATA_DERIVED / f"dem_{tag}_{res:g}m.tif",
            "mesh": s["mesh"][mode], "run": s["run"][mode]}


def add_mode_arg(ap) -> None:
    """--mode {shakedown,extended,production}; --production kept as an alias."""
    ap.add_argument("--mode", choices=MODES, default=None, help="model tier (default: shakedown)")
    ap.add_argument("--production", action="store_true", help="alias for --mode production")


def mode_from_args(a) -> str:
    return a.mode or ("production" if getattr(a, "production", False) else "shakedown")


def ensure_dirs() -> None:
    for d in (DATA_RAW, DATA_DERIVED, OUTPUTS):
        os.makedirs(d, exist_ok=True)


def scenario_dir(name: str) -> Path:
    d = OUTPUTS / name
    os.makedirs(d, exist_ok=True)
    return d


def breach_points(name: str) -> list:
    """All external breach locations (NZTM) of a scenario – one for the classic scenarios,
    several for a multi-breach (seismic) scenario."""
    sc = scenario(name)
    pts = [b["location_nztm"] for b in sc.get("breaches", []) if not b.get("feeds") and b.get("location_nztm")]
    return pts or [sc["breach_location_nztm"]]
