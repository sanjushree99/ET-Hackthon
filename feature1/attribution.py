"""
Main attribution pipeline.
Input:  detection location + timestamp
Output: structured JSON with ranked candidate zones, source categories,
        calibrated confidence, contributing features, and plume backtrace path.
"""

import json
import numpy as np
from datetime import datetime
from typing import Optional

from synthetic_data import GRID_LAT, GRID_LON, DETECTION_POINT, get_wind_at
from plume import backward_trace, PlumeParams
from features import build_feature_matrix, engineer_features, CLASSIFIER_FEATURES
from classifier import predict_zones


def run_attribution(
    detection_lat: float,
    detection_lon: float,
    timestamp: datetime,
    observed_concentration_ugm3: float = 150.0,
    top_k: int = 5,
    plume_params: Optional[PlumeParams] = None,
) -> dict:
    """
    Full attribution pipeline. Returns a structured dict ready for JSON serialisation.
    """
    # 1. Get wind conditions
    wind = get_wind_at(detection_lat, detection_lon, timestamp)

    # 2. Gaussian plume backward trace
    candidates = backward_trace(
        detection_lat=detection_lat,
        detection_lon=detection_lon,
        wind_speed=wind["speed_ms"],
        wind_direction_deg=wind["direction_deg"],
        stability_class=wind["stability_class"],
        grid_lats=GRID_LAT,
        grid_lons=GRID_LON,
        params=plume_params or PlumeParams(),
        concentration_threshold=0.005,
        max_distance_km=12.0,
    )

    if not candidates:
        return {"error": "No candidate zones found upwind", "wind": wind}

    # Limit to top-K by plume weight before feature engineering (performance)
    candidates = candidates[:min(50, len(candidates))]

    # 3. Feature engineering
    hour = timestamp.hour
    feat_df = build_feature_matrix(candidates, hour)

    # 4. Classifier inference
    result_df = predict_zones(feat_df)

    # 5. Sort by confidence × plume_weight (physics-informed ranking)
    result_df["score"] = result_df["confidence"] * result_df["plume_weight"]
    result_df = result_df.sort_values("score", ascending=False).head(top_k).reset_index(drop=True)

    # 6. Build plume backtrace path (polyline from detection point upwind)
    ue = -np.sin(np.radians(wind["direction_deg"]))
    un = -np.cos(np.radians(wind["direction_deg"]))
    backtrace_path = [
        {
            "lat": detection_lat + un * d / 110540,
            "lon": detection_lon + ue * d / (111320 * np.cos(np.radians(detection_lat))),
            "distance_m": d,
        }
        for d in np.linspace(0, 12000, 25)
    ]

    # 7. Assemble output
    ranked_zones = []
    for _, row in result_df.iterrows():
        contributing = {
            "plume_weight":               round(row["plume_weight"], 3),
            "dist_to_nearest_industrial": round(row["dist_to_nearest_industrial"], 2),
            "violation_count":            int(row["violation_count"]),
            "land_use":                   row["land_use"],
            "permit_density":             round(row["permit_density"], 2),
            "traffic_density":            round(row["traffic_density"], 2),
            "downwind_distance_km":       round(row["downwind_distance_km"], 2),
        }
        ranked_zones.append({
            "zone": {"lat": round(row["lat"] if "lat" in row else 0, 4),
                     "lon": round(row["lon"] if "lon" in row else 0, 4)},
            "source_category":      row["predicted_category"],
            "confidence":           round(float(row["confidence"]), 4),
            "score":                round(float(row["score"]), 4),
            "contributing_features": contributing,
            "class_probabilities": {
                cat: round(float(row[f"proba_{cat}"]), 4)
                for cat in ["industrial", "vehicular", "construction", "biomass", "other"]
                if f"proba_{cat}" in row
            },
        })

    # Attach zone lat/lon from candidates list
    for i, row_dict in enumerate(ranked_zones):
        if i < len(candidates):
            row_dict["zone"]["lat"] = round(candidates[i].lat, 4)
            row_dict["zone"]["lon"] = round(candidates[i].lon, 4)

    return {
        "detection_point": {"lat": detection_lat, "lon": detection_lon},
        "timestamp": timestamp.isoformat(),
        "observed_concentration_ugm3": observed_concentration_ugm3,
        "wind": wind,
        "candidate_count": len(candidates),
        "ranked_zones": ranked_zones,
        "plume_backtrace_path": backtrace_path,
        "data_sources": {
            "wind": wind["source"],
            "industrial_registry": "SYNTHETIC (swap: CPCB consent registry)",
            "land_use": "SYNTHETIC (swap: OSM Overpass API)",
            "model": "XGBoost + Platt calibration, trained on synthetic labels",
        },
    }


if __name__ == "__main__":
    result = run_attribution(
        detection_lat=DETECTION_POINT[0],
        detection_lon=DETECTION_POINT[1],
        timestamp=datetime(2024, 11, 1, 9, 0),
        observed_concentration_ugm3=185.0,
    )
    print(json.dumps(result, indent=2))
