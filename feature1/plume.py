"""
Gaussian plume dispersion model + backward trace.

Forward model (Gaussian plume equation):
    C(x,y,z) = Q/(2π·u·σy·σz) · exp(-y²/2σy²) · [exp(-(z-H)²/2σz²) + exp(-(z+H)²/2σz²)]

Backward trace: invert wind direction, walk upwind from detection point,
collect grid cells whose forward plume concentration at the detection point
exceeds a threshold — these are candidate source zones.

σy, σz from Pasquill-Gifford empirical fits (Seinfeld & Pandis Table 18.2).
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple

# ── P-G sigma coefficients (a,b for σy = a·x^b; c,d,f for σz) ───────────────
# Source: Seinfeld & Pandis "Atmospheric Chemistry and Physics", Table 18.2
# x in km, σ in metres
PG_PARAMS = {
    #  class: (ay, by, az, bz)   — simplified power-law fit
    "A": (0.22, 0.894, 0.20, 0.894),
    "B": (0.16, 0.894, 0.12, 0.894),
    "C": (0.11, 0.894, 0.08, 0.894),
    "D": (0.08, 0.894, 0.06, 0.894),
    "E": (0.06, 0.894, 0.03, 0.894),
    "F": (0.04, 0.894, 0.016, 0.894),
}

def sigma_y(x_km: float, stability: str) -> float:
    ay, by, _, _ = PG_PARAMS[stability]
    return ay * (x_km ** by) * 1000  # metres

def sigma_z(x_km: float, stability: str) -> float:
    _, _, az, bz = PG_PARAMS[stability]
    return az * (x_km ** bz) * 1000  # metres


@dataclass
class PlumeParams:
    emission_rate_gs: float = 10.0   # g/s (normalised; we care about relative weights)
    stack_height_m: float   = 20.0   # effective release height
    receptor_height_m: float = 2.0   # measurement height


def gaussian_concentration(
    x_m: float, y_m: float, z_m: float,
    wind_speed: float, stability: str,
    params: PlumeParams,
) -> float:
    """
    Concentration (µg/m³) at downwind (x_m, y_m, z_m) from a unit source.
    x_m: downwind distance (m), y_m: crosswind offset (m), z_m: height (m).
    Returns 0 for x <= 0 (upwind).
    """
    if x_m <= 0:
        return 0.0
    x_km = x_m / 1000.0
    sy = sigma_y(x_km, stability)
    sz = sigma_z(x_km, stability)
    H = params.stack_height_m
    Q = params.emission_rate_gs * 1e6  # convert g/s → µg/s

    horizontal = np.exp(-0.5 * (y_m / sy) ** 2)
    vertical   = (np.exp(-0.5 * ((z_m - H) / sz) ** 2) +
                  np.exp(-0.5 * ((z_m + H) / sz) ** 2))
    denom = 2 * np.pi * wind_speed * sy * sz
    return float(Q / denom * horizontal * vertical)


def latlon_to_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """Approximate lat/lon → metres offset from reference point."""
    dx = (lon - ref_lon) * 111320 * np.cos(np.radians(ref_lat))
    dy = (lat - ref_lat) * 110540
    return dx, dy


def wind_to_unit_vector(direction_deg: float) -> Tuple[float, float]:
    """Wind direction (meteorological, FROM) → unit vector (u_east, u_north)."""
    rad = np.radians(direction_deg)
    return -np.sin(rad), -np.cos(rad)   # wind blows TOWARD this direction


@dataclass
class CandidateZone:
    lat: float
    lon: float
    plume_weight: float          # normalised concentration contribution
    downwind_distance_m: float
    crosswind_offset_m: float
    sigma_y_m: float
    sigma_z_m: float


def backward_trace(
    detection_lat: float,
    detection_lon: float,
    wind_speed: float,
    wind_direction_deg: float,
    stability_class: str,
    grid_lats: np.ndarray,
    grid_lons: np.ndarray,
    params: PlumeParams = None,
    concentration_threshold: float = 0.01,   # µg/m³ minimum to be a candidate
    max_distance_km: float = 15.0,
) -> List[CandidateZone]:
    """
    For each grid cell, compute what concentration it would produce at the
    detection point if it were the source. Cells above threshold are candidates.

    This is the backward Gaussian plume: we treat each upwind grid cell as a
    hypothetical source and evaluate C at the receptor (detection point).
    """
    if params is None:
        params = PlumeParams()

    ue, un = wind_to_unit_vector(wind_direction_deg)  # wind transport direction
    candidates = []

    for lat in grid_lats:
        for lon in grid_lons:
            # Vector from candidate cell → detection point
            dx, dy = latlon_to_xy(detection_lat, detection_lon, lat, lon)

            # Downwind component (along wind transport direction)
            x_m = dx * ue + dy * un
            # Crosswind component
            y_m = dx * (-un) + dy * ue

            dist_km = np.sqrt(dx**2 + dy**2) / 1000.0
            if x_m <= 0 or dist_km > max_distance_km:
                continue

            c = gaussian_concentration(
                x_m, y_m, params.receptor_height_m,
                wind_speed, stability_class, params,
            )
            if c >= concentration_threshold:
                candidates.append(CandidateZone(
                    lat=lat, lon=lon,
                    plume_weight=c,
                    downwind_distance_m=x_m,
                    crosswind_offset_m=y_m,
                    sigma_y_m=sigma_y(x_m / 1000, stability_class),
                    sigma_z_m=sigma_z(x_m / 1000, stability_class),
                ))

    # Normalise weights to [0, 1]
    if candidates:
        max_w = max(c.plume_weight for c in candidates)
        for c in candidates:
            c.plume_weight = c.plume_weight / max_w

    return sorted(candidates, key=lambda c: c.plume_weight, reverse=True)
