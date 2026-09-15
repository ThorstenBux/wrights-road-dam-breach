"""Dam-breach outflow estimation.

Implements the pieces needed for an NZSOLD "intermediate"-level breach outflow
hydrograph (NZSOLD Dam Safety Guidelines 2024, Module 2, s2.3.4–2.3.5):

* a simple stage–storage relationship for a lined, excavated storage pond,
* empirical breach parameters after Froehlich (2008) – average width, side slope
  and formation time – and the Froehlich (1995) peak-outflow check,
* level-pool routing of the reservoir through a progressively enlarging
  trapezoidal breach treated as a broad-crested weir,
* a pond cascade (upper pond breaches into the lower pond, which then overtops
  and fails), which is the governing mechanism identified by Damwatch for the
  East / South / North embankments of the Wrights Road ponds.

Everything is pure numpy so it can be unit-tested without ANUGA.

References
----------
Froehlich, D.C. (1995). Peak outflow from breached embankment dam.
    J. Water Resour. Plann. Manage. 121(1), 90–97.
Froehlich, D.C. (2008). Embankment dam breach parameters and their uncertainties.
    J. Hydraul. Eng. 134(12), 1708–1721.
Froehlich, D.C. (2016a, 2016b). Updated breach-parameter and peak-discharge
    relations recommended by NZSOLD (2024).  NOT implemented here – a
    Recognised Engineer should confirm the exact published coefficients before
    they are used for a certified PIC.  Hooks are provided in `BreachGeometry`
    so user-supplied parameters can replace the Froehlich (2008) defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

G = 9.81  # m/s^2


# --------------------------------------------------------------------------- #
# Reservoir stage–storage
# --------------------------------------------------------------------------- #
@dataclass
class Reservoir:
    """Stage–storage for a pond, assuming wetted area varies linearly with level
    between the invert and full supply level (a truncated pyramid).  Good
    enough for a 1V:3H lined pond; replace `area()`/`volume()` with the
    surveyed stage–storage table from the design drawings when available.

    Parameters
    ----------
    fsl        : full supply level, m RL
    invert     : lowest pond floor level, m RL
    area_fsl   : wetted surface area at FSL, m2
    volume_fsl : live storage at FSL, m3
    crest      : embankment crest level, m RL
    """

    name: str
    fsl: float
    invert: float
    area_fsl: float
    volume_fsl: float
    crest: float

    def __post_init__(self) -> None:
        if self.fsl <= self.invert:
            raise ValueError("fsl must be above invert")
        H = self.fsl - self.invert
        # V = H (A0 + A1)/2  ->  A0 = 2V/H - A1
        self.area_invert = max(2.0 * self.volume_fsl / H - self.area_fsl, 0.0)
        self._k = (self.area_fsl - self.area_invert) / H  # dA/dz

    # -- geometry ----------------------------------------------------------- #
    def area(self, z):
        h = np.clip(np.asarray(z, dtype=float) - self.invert, 0.0, None)
        return self.area_invert + self._k * h

    def volume(self, z):
        h = np.clip(np.asarray(z, dtype=float) - self.invert, 0.0, None)
        return self.area_invert * h + 0.5 * self._k * h**2

    def level(self, V: float) -> float:
        V = max(float(V), 0.0)
        if self._k < 1e-12:
            h = V / self.area_invert
        else:
            h = (-self.area_invert + np.sqrt(self.area_invert**2 + 2.0 * self._k * V)) / self._k
        return self.invert + h

    def volume_above(self, z_ref: float, z_pool: Optional[float] = None) -> float:
        """Volume stored above `z_ref` when the pool is at `z_pool` (default FSL).
        This is the Froehlich `V_w` when z_ref is the final breach invert."""
        z_pool = self.fsl if z_pool is None else z_pool
        return float(self.volume(z_pool) - self.volume(z_ref))


# --------------------------------------------------------------------------- #
# Breach parameter estimation
# --------------------------------------------------------------------------- #
def froehlich_2008(V_w: float, h_b: float, mode: str) -> dict:
    """Froehlich (2008) breach parameters (SI units).

    V_w  : volume of water above the final breach invert at failure, m3
    h_b  : height of the breach (pool level at failure – breach invert), m
    mode : 'overtopping' or 'piping'

    Returns dict with average width B_avg (m), bottom width B_bot (m), side
    slope z (H:V), and formation time t_f (s).
    """
    if V_w <= 0 or h_b <= 0:
        raise ValueError("V_w and h_b must be positive")
    overtop = mode.lower().startswith("over")
    k_o = 1.3 if overtop else 1.0
    z = 1.0 if overtop else 0.7
    B_avg = 0.27 * k_o * V_w**0.32 * h_b**0.04
    t_f = 63.2 * np.sqrt(V_w / (G * h_b**2))
    B_bot = max(B_avg - z * h_b, 0.0)  # trapezoid: B_avg = B_bot + z*h_b
    return {"B_avg": B_avg, "B_bot": B_bot, "z": z, "t_f": float(t_f), "method": "Froehlich (2008)"}


def froehlich_1995_peak(V_w: float, h_w: float) -> float:
    """Froehlich (1995) empirical peak breach outflow, m3/s.
    h_w = height of water above breach invert at failure (m)."""
    return 0.607 * V_w**0.295 * h_w**1.24


# --------------------------------------------------------------------------- #
# Breach geometry and routing
# --------------------------------------------------------------------------- #
@dataclass
class BreachGeometry:
    mode: str                     # 'overtopping' | 'piping'
    invert: float                 # final breach bottom level, m RL (≈ natural ground at toe)
    bottom_width: float           # final bottom width, m
    side_slope: float             # z (horizontal per vertical)
    formation_time: float         # s, from first erosion to full size
    progression: str = "linear"   # 'linear' | 'sine'
    method: str = "user"
    notes: str = ""

    @classmethod
    def from_froehlich_2008(cls, res: Reservoir, invert: float, mode: str,
                            pool_level: Optional[float] = None, **kw) -> "BreachGeometry":
        pool = res.fsl if pool_level is None else pool_level
        h_b = pool - invert
        V_w = res.volume_above(invert, pool)
        p = froehlich_2008(V_w, h_b, mode)
        return cls(mode=mode, invert=invert, bottom_width=p["B_bot"], side_slope=p["z"],
                   formation_time=p["t_f"], method=p["method"],
                   notes=f"V_w={V_w:.3e} m3, h_b={h_b:.2f} m, B_avg={p['B_avg']:.1f} m", **kw)

    def fraction(self, tau: float) -> float:
        """Breach development fraction 0..1 at time `tau` since initiation."""
        f = np.clip(tau / self.formation_time, 0.0, 1.0)
        if self.progression == "sine":
            f = np.sin(0.5 * np.pi * f)
        return float(f)

    def top_width(self, depth_of_cut: float, frac: float) -> float:
        return self.bottom_width * frac + 2 * self.side_slope * depth_of_cut


@dataclass
class BreachEvent:
    reservoir: Reservoir
    geometry: BreachGeometry
    initial_level: Optional[float] = None   # pool level at t=0 (default FSL)
    trigger_level: Optional[float] = None   # breach initiates when pool >= this level
    start_time: float = 0.0                 # s; used when trigger_level is None
    weir_coeff_rect: float = 1.7            # broad-crested weir, SI (Q = C b H^1.5)
    weir_coeff_tri: float = 1.4             # triangular sides, SI (Q = C z H^2.5)
    crest_overflow_length: Optional[float] = None  # m; uncontrolled crest overflow before breach


def _weir_flow(H: float, b: float, z: float, c_r: float, c_t: float) -> float:
    if H <= 0.0:
        return 0.0
    return c_r * b * H**1.5 + c_t * z * H**2.5


def route(event: BreachEvent, t_end: float, dt: float = 1.0,
          inflow: Optional[Callable[[float], float]] = None) -> dict:
    """Level-pool routing of a breach.  Returns arrays of t, Q_out, Q_in, level,
    breach_bottom, breach_bottom_width, breach_top_width (all numpy)."""
    res, geom = event.reservoir, event.geometry
    n = int(np.ceil(t_end / dt)) + 1
    t = np.arange(n) * dt
    Q_out = np.zeros(n); Q_in = np.zeros(n); lev = np.zeros(n)
    zb_arr = np.zeros(n); bw = np.zeros(n); tw = np.zeros(n)

    z = res.fsl if event.initial_level is None else event.initial_level
    V = float(res.volume(z))
    overtop = geom.mode.lower().startswith("over")
    t_init: Optional[float] = None if event.trigger_level is not None else event.start_time
    zb_start = None

    for i in range(n):
        ti = t[i]
        qin = float(inflow(ti)) if inflow else 0.0
        # breach initiation
        if t_init is None and event.trigger_level is not None and z >= event.trigger_level:
            t_init = ti
        q = 0.0
        if t_init is not None and ti >= t_init:
            if zb_start is None:
                # overtopping: erosion starts at the crest; piping: at the pool level
                zb_start = res.crest if overtop else min(z, res.crest)
            frac = geom.fraction(ti - t_init)
            zb = zb_start - (zb_start - geom.invert) * frac
            b = geom.bottom_width * frac
            H = z - zb
            q = _weir_flow(H, b, geom.side_slope, event.weir_coeff_rect, event.weir_coeff_tri)
            zb_arr[i], bw[i] = zb, b
            tw[i] = b + 2 * geom.side_slope * max(zb_start - zb, 0.0)
        else:
            zb_arr[i] = res.crest
        # uncontrolled overflow over the remaining crest (optional)
        if event.crest_overflow_length and z > res.crest:
            q += event.weir_coeff_rect * event.crest_overflow_length * (z - res.crest) ** 1.5
        # cannot release more than what is stored above the breach invert this step
        avail = max(V - float(res.volume(zb_arr[i])), 0.0) + qin * dt
        q = min(q, avail / dt)
        Q_out[i], Q_in[i], lev[i] = q, qin, z
        V = max(V + (qin - q) * dt, 0.0)
        z = res.level(V)

    return {"t": t, "Q_out": Q_out, "Q_in": Q_in, "level": lev, "breach_bottom": zb_arr,
            "breach_bottom_width": bw, "breach_top_width": tw,
            "t_init": t_init, "volume_released": float(np.trapezoid(Q_out, t))}


def cascade(events: list[BreachEvent], t_end: float, dt: float = 1.0) -> list[dict]:
    """Route a chain of ponds: outflow of events[i] is the inflow to events[i+1]."""
    results: list[dict] = []
    inflow = None
    for ev in events:
        r = route(ev, t_end, dt, inflow=inflow)
        results.append(r)
        tt, qq = r["t"], r["Q_out"]
        inflow = lambda s, tt=tt, qq=qq: float(np.interp(s, tt, qq, left=0.0, right=0.0))
    return results


def hydrograph_summary(r: dict) -> dict:
    i = int(np.argmax(r["Q_out"]))
    above = r["Q_out"] > 0.01 * r["Q_out"][i] if r["Q_out"][i] > 0 else np.zeros_like(r["Q_out"], bool)
    return {
        "peak_Q_m3s": float(r["Q_out"][i]),
        "time_to_peak_s": float(r["t"][i]),
        "t_init_s": r["t_init"],
        "volume_released_m3": r["volume_released"],
        "duration_gt_1pct_peak_s": float(above.sum() * (r["t"][1] - r["t"][0])) if above.any() else 0.0,
        "final_level_m": float(r["level"][-1]),
        "max_level_m": float(r["level"].max()),
    }


def write_hydrograph_csv(path, r: dict, every: int = 1) -> None:
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "Q_out_m3s", "Q_in_m3s", "level_mRL", "breach_bottom_mRL",
                    "breach_bottom_width_m", "breach_top_width_m"])
        for i in range(0, len(r["t"]), every):
            w.writerow([f"{r['t'][i]:.0f}", f"{r['Q_out'][i]:.3f}", f"{r['Q_in'][i]:.3f}",
                        f"{r['level'][i]:.3f}", f"{r['breach_bottom'][i]:.3f}",
                        f"{r['breach_bottom_width'][i]:.2f}", f"{r['breach_top_width'][i]:.2f}"])


def read_hydrograph_csv(path) -> Callable[[float], float]:
    """Return Q(t) interpolator from a CSV written by write_hydrograph_csv."""
    data = np.genfromtxt(path, delimiter=",", names=True)
    t, q = data["t_s"], data["Q_out_m3s"]
    return lambda s: float(np.interp(s, t, q, left=0.0, right=0.0))
