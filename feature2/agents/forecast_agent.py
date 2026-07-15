"""
Forecast Agent
Produces a 24-hour AQI forecast from the spike location/timestamp.
Uses a lightweight synthetic model (sine + trend) — clearly marked.
Flags when predicted AQI crosses the severe threshold (AQI > 300).

Swap-in: replace _synthetic_forecast() with a call to CPCB SAFAR API
         or a trained LSTM/Prophet model on historical CPCB station data.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from agents.state import PipelineState, ForecastResult

logger = logging.getLogger("forecast_agent")

AQI_SEVERE_THRESHOLD = 300  # India CPCB AQI scale: >300 = Severe


def _pm25_to_aqi(pm25: float) -> float:
    """Linear approximation of India CPCB AQI breakpoints for PM2.5."""
    breakpoints = [
        (0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200),
        (90, 120, 201, 300), (120, 250, 301, 400), (250, 500, 401, 500),
    ]
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c_lo <= pm25 <= c_hi:
            return i_lo + (pm25 - c_lo) / (c_hi - c_lo) * (i_hi - i_lo)
    return 500.0


def _synthetic_forecast(base_pm25: float, start_hour: int) -> list[dict]:
    """
    SYNTHETIC: 24-hour PM2.5 forecast using diurnal pattern + decay.
    Real swap-in: CPCB SAFAR API or trained time-series model.
    """
    rng = np.random.default_rng(int(base_pm25) % 100)
    hours = np.arange(24)
    # Diurnal pattern: peaks at morning (8h) and evening (19h) rush
    diurnal = 0.3 * np.sin(2 * np.pi * (hours - 8) / 24) + \
              0.2 * np.sin(2 * np.pi * (hours - 19) / 12)
    # Decay from spike over 24h
    decay = np.exp(-hours / 18)
    noise = rng.normal(0, 5, 24)
    pm25_series = base_pm25 * (0.6 + 0.4 * decay) * (1 + diurnal) + noise
    pm25_series = np.clip(pm25_series, 20, 500)

    return [
        {
            "hour": int((start_hour + h) % 24),
            "pm25": round(float(pm25_series[h]), 1),
            "aqi": round(_pm25_to_aqi(float(pm25_series[h])), 1),
        }
        for h in hours
    ]


def forecast_agent(state: PipelineState) -> dict:
    inp = state["spike_input"]
    logger.info("[ForecastAgent] input: lat=%s lon=%s ts=%s",
                inp["lat"], inp["lon"], inp["timestamp"])

    try:
        start_hour = datetime.fromisoformat(inp["timestamp"]).hour
        forecast = _synthetic_forecast(inp["observed_concentration_ugm3"], start_hour)

        peak = max(forecast, key=lambda x: x["aqi"])
        breach = next((f for f in forecast if f["aqi"] > AQI_SEVERE_THRESHOLD), None)

        result: ForecastResult = {
            "forecast_aqi": forecast,
            "threshold_breached": breach is not None,
            "breach_hour": breach["hour"] if breach else None,
            "peak_aqi": peak["aqi"],
            "model": "SYNTHETIC (swap: CPCB SAFAR API)",
        }
        status = {"status": "done", "error": None}
        logger.info("[ForecastAgent] peak_aqi=%.1f breached=%s",
                    result["peak_aqi"], result["threshold_breached"])
    except Exception as e:
        logger.error("[ForecastAgent] failed: %s", e)
        result = {"forecast_aqi": [], "threshold_breached": False,
                  "breach_hour": None, "peak_aqi": 0.0, "model": "failed"}
        status = {"status": "degraded", "error": str(e)}

    trace_entry = {
        "agent": "ForecastAgent",
        "input": {"lat": inp["lat"], "lon": inp["lon"],
                  "base_pm25": inp["observed_concentration_ugm3"]},
        "output_summary": {
            "peak_aqi": result["peak_aqi"],
            "threshold_breached": result["threshold_breached"],
            "breach_hour": result["breach_hour"],
        },
        "status": status["status"],
    }

    return {
        "forecast_output": result,
        "forecast_status": status,
        "trace": state.get("trace", []) + [trace_entry],
    }
