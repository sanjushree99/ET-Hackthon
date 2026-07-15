"""
Feature engineering: enriches each CandidateZone with contextual signals
needed by the classifier.
"""

import numpy as np
import pandas as pd
from typing import List
from plume import CandidateZone
from synthetic_data import (
    INDUSTRIAL_SITES, get_land_use, get_permit_density, get_traffic_density,
)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1))*np.cos(np.radians(lat2))*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def nearest_site_features(lat: float, lon: float) -> dict:
    """Distance and violation count for the nearest registered industrial site."""
    dists = INDUSTRIAL_SITES.apply(
        lambda r: haversine_km(lat, lon, r["lat"], r["lon"]), axis=1
    )
    idx = dists.idxmin()
    site = INDUSTRIAL_SITES.loc[idx]
    return {
        "dist_to_nearest_industrial": float(dists[idx]),
        "nearest_site_category": site["category"],
        "violation_count": int(site["violation_count"]),
    }


def land_use_features(lat: float, lon: float) -> dict:
    lu = get_land_use(lat, lon)
    return {
        "land_use": lu,
        "land_use_industrial":   int(lu == "industrial"),
        "land_use_construction": int(lu == "construction"),
        "land_use_transport":    int(lu == "transport"),
    }


def engineer_features(zone: CandidateZone, hour: int) -> dict:
    """
    Returns a flat feature dict for one candidate zone.
    All features are numeric (classifier-ready) plus metadata strings.
    """
    site_feats = nearest_site_features(zone.lat, zone.lon)
    lu_feats   = land_use_features(zone.lat, zone.lon)

    return {
        # Physics-derived
        "plume_weight":          zone.plume_weight,
        "downwind_distance_km":  zone.downwind_distance_m / 1000.0,
        "crosswind_offset_km":   abs(zone.crosswind_offset_m) / 1000.0,
        "sigma_y_m":             zone.sigma_y_m,
        "sigma_z_m":             zone.sigma_z_m,
        # Proximity / registry
        "dist_to_nearest_industrial": site_feats["dist_to_nearest_industrial"],
        "violation_count":            site_feats["violation_count"],
        "nearest_site_category":      site_feats["nearest_site_category"],
        # Land use
        **lu_feats,
        # Activity signals
        "permit_density":   get_permit_density(zone.lat, zone.lon),
        "traffic_density":  get_traffic_density(zone.lat, zone.lon, hour),
        "hour":             hour,
    }


def build_feature_matrix(zones: List[CandidateZone], hour: int) -> pd.DataFrame:
    """Returns a DataFrame with one row per candidate zone, ready for inference."""
    return pd.DataFrame([engineer_features(z, hour) for z in zones])


# Columns used by the classifier (must match training)
CLASSIFIER_FEATURES = [
    "plume_weight",
    "dist_to_nearest_industrial",
    "land_use_industrial",
    "land_use_construction",
    "violation_count",
    "permit_density",
    "traffic_density",
    "hour",
]
