"""
FastAPI app — POST /analyze-spike
Runs the full LangGraph pipeline and returns:
  - final structured recommendation
  - intermediate agent outputs (for demo transparency)
  - full observability trace
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))

from graph import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(
    title="Air Quality Intelligence API",
    description="Physics-informed pollution attribution + multi-agent enforcement pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpikeRequest(BaseModel):
    lat: float = Field(..., example=28.6139)
    lon: float = Field(..., example=77.2090)
    timestamp: str = Field(..., example="2024-11-01T09:00:00")
    observed_concentration_ugm3: float = Field(..., example=185.0)


@app.post("/analyze-spike")
def analyze_spike(req: SpikeRequest):
    logger.info("POST /analyze-spike lat=%s lon=%s ts=%s pm25=%s",
                req.lat, req.lon, req.timestamp, req.observed_concentration_ugm3)

    # Validate timestamp
    try:
        datetime.fromisoformat(req.timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="timestamp must be ISO-8601 format")

    state = run_pipeline(
        lat=req.lat,
        lon=req.lon,
        timestamp=req.timestamp,
        observed_concentration_ugm3=req.observed_concentration_ugm3,
    )

    # Top-level recommendation card
    top_zone = None
    if state.get("attribution_output") and state["attribution_output"].get("ranked_zones"):
        top_zone = state["attribution_output"]["ranked_zones"][0]

    recommendation = {
        "top_source_category":  top_zone.get("source_category") if top_zone else None,
        "confidence":           top_zone.get("confidence") if top_zone else None,
        "enforcement_score":    state.get("enforcement_score"),
        "enforcement_actions":  state.get("enforcement_actions"),
        "enforcement_text":     state.get("enforcement_text"),
        "forecast_peak_aqi":    state.get("forecast_output", {}).get("peak_aqi") if state.get("forecast_output") else None,
        "severe_threshold_breached": state.get("forecast_output", {}).get("threshold_breached") if state.get("forecast_output") else None,
    }

    return {
        "recommendation": recommendation,
        "agent_outputs": {
            "attribution": {
                "status":  state["attribution_status"],
                "output":  state.get("attribution_output"),
            },
            "forecast": {
                "status":  state["forecast_status"],
                "output":  state.get("forecast_output"),
            },
            "reasoning": {
                "status":  state["reasoning_status"],
                "text":    state.get("reasoning_text"),
            },
            "enforcement": {
                "status":  state["enforcement_status"],
                "score":   state.get("enforcement_score"),
                "actions": state.get("enforcement_actions"),
                "text":    state.get("enforcement_text"),
            },
        },
        "trace": state.get("trace", []),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
