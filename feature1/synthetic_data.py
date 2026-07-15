"""
SYNTHETIC DATA MODULE
All data here is synthetic/simulated. Replace each section with real data sources:
  - Wind data:    IMD API (https://mausam.imd.gov.in/) or ERA5 reanalysis
  - Industrial:   CPCB consent registry (https://cpcb.nic.in/)
  - Land use:     OSM Overpass API (https://overpass-api.de/)
  - Violations:   CPCB OCEMS data
  - Permits:      Municipal corporation open data portals
"""

import numpy as np
import pandas as pd
from datetime import datetime

# ── Grid definition (Delhi NCR bounding box, ~1km cells) ─────────────────────
GRID_LAT = np.arange(28.40, 28.80, 0.01)
GRID_LON = np.arange(76.90, 77.40, 0.01)
DETECTION_POINT = (28.6139, 77.2090)  # Connaught Place, Delhi

# ── Synthetic wind time series ────────────────────────────────────────────────
def get_wind_at(lat: float, lon: float, timestamp: datetime) -> dict:
    """
    SYNTHETIC. Real swap-in: query IMD AWS station nearest (lat,lon) at timestamp.
    Stability class per Pasquill-Gifford table (D=neutral, most common urban).
    """
    rng = np.random.default_rng(int(timestamp.timestamp()) % 10000)
    return {
        "speed_ms": float(rng.uniform(2.0, 6.0)),
        "direction_deg": float(rng.uniform(200, 280)),  # SW-W winds typical Delhi
        "stability_class": "D",
        "source": "SYNTHETIC",
    }

# ── Industrial / source registry ─────────────────────────────────────────────
INDUSTRIAL_SITES = pd.DataFrame([
    {"id": "IND001", "name": "Anand Parbat Industrial Area",   "lat": 28.6420, "lon": 77.1750, "category": "industrial",   "violation_count": 5},
    {"id": "IND002", "name": "Okhla Industrial Estate",        "lat": 28.5355, "lon": 77.2700, "category": "industrial",   "violation_count": 3},
    {"id": "IND003", "name": "Wazirpur Industrial Area",       "lat": 28.7000, "lon": 77.1600, "category": "industrial",   "violation_count": 8},
    {"id": "IND004", "name": "Mayapuri Industrial Area",       "lat": 28.6350, "lon": 77.1100, "category": "industrial",   "violation_count": 2},
    {"id": "CON001", "name": "Dwarka Expressway Construction", "lat": 28.5921, "lon": 77.0460, "category": "construction", "violation_count": 1},
    {"id": "BIO001", "name": "Bhalswa Landfill",               "lat": 28.7500, "lon": 77.1700, "category": "biomass",      "violation_count": 4},
    {"id": "VEH001", "name": "NH-48 High Traffic Corridor",    "lat": 28.5700, "lon": 77.1200, "category": "vehicular",    "violation_count": 0},
    {"id": "VEH002", "name": "Ring Road Congestion Zone",      "lat": 28.6300, "lon": 77.2500, "category": "vehicular",    "violation_count": 0},
])

# ── Land use lookup ───────────────────────────────────────────────────────────
LAND_USE_TYPES = ["industrial", "residential", "commercial", "green", "transport", "construction"]

def get_land_use(lat: float, lon: float) -> str:
    """SYNTHETIC. Real swap-in: OSM Overpass QL landuse=* within 500m of point."""
    idx = int((lat * 100 + lon * 100)) % len(LAND_USE_TYPES)
    return LAND_USE_TYPES[idx]

# ── Construction permit density ───────────────────────────────────────────────
def get_permit_density(lat: float, lon: float) -> float:
    """SYNTHETIC (permits/km²). Real swap-in: MCD building permit open data API."""
    return float(np.sin(lat * 50) ** 2 * 3.0)

# ── Traffic density (time-of-day weighted) ────────────────────────────────────
def get_traffic_density(lat: float, lon: float, hour: int) -> float:
    """SYNTHETIC (0-1). Real swap-in: HERE/TomTom Traffic API or Google Roads."""
    peak = 1.0 if hour in range(8, 10) or hour in range(17, 20) else 0.4
    base = float(abs(np.cos(lon * 30)) * 0.6)
    return min(1.0, base + peak * 0.4)

# ── Labeled training dataset ──────────────────────────────────────────────────
def get_training_data() -> pd.DataFrame:
    """
    SYNTHETIC: 500 labeled attribution events.
    Real swap-in: CPCB enforcement orders with confirmed source categories.
    """
    rng = np.random.default_rng(42)
    n = 500
    categories = ["industrial", "vehicular", "construction", "biomass", "other"]
    rows = []
    for i in range(n):
        cat = rng.choice(categories, p=[0.30, 0.30, 0.15, 0.15, 0.10])
        rows.append({
            "true_category": cat,
            "dist_to_nearest_industrial": rng.uniform(0.1, 5.0) if cat == "industrial" else rng.uniform(1.0, 8.0),
            "land_use_industrial":   int(cat == "industrial"   and rng.random() > 0.2),
            "land_use_construction": int(cat == "construction" and rng.random() > 0.2),
            "violation_count":  int(rng.integers(3, 10) if cat == "industrial" else rng.integers(0, 3)),
            "permit_density":   float(rng.uniform(1.5, 4.0) if cat == "construction" else rng.uniform(0.0, 1.5)),
            "traffic_density":  float(rng.uniform(0.6, 1.0) if cat == "vehicular"   else rng.uniform(0.0, 0.5)),
            "plume_weight":     float(rng.uniform(0.5, 1.0) if cat != "other"       else rng.uniform(0.0, 0.3)),
            "hour": int(rng.integers(0, 24)),
        })
    return pd.DataFrame(rows)
