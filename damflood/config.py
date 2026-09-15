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
