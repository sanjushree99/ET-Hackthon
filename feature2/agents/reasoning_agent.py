"""
Reasoning Agent
Takes Attribution Agent's structured JSON and uses Claude (claude-sonnet-4-5)
to generate a plain-language explanation for non-technical officials.

Graceful degradation: if Claude call fails/times out, returns a deterministic
template-based explanation so the pipeline never crashes.

Requires env var: ANTHROPIC_API_KEY
"""

import os
import logging
import anthropic
from agents.state import PipelineState

logger = logging.getLogger("reasoning_agent")

SYSTEM_PROMPT = """You are an air quality analyst writing briefings for municipal officials.
Write clearly, avoid jargon, and be specific about locations and causes.
Keep the explanation under 150 words."""

def _build_prompt(attribution: dict, forecast: dict) -> str:
    top = attribution.get("ranked_zones", [{}])[0]
    wind = attribution.get("wind", {})
    breach = forecast.get("threshold_breached", False)
    peak_aqi = forecast.get("peak_aqi", "unknown")

    return f"""A pollution spike of {attribution.get('observed_concentration_ugm3')} µg/m³ PM2.5
was detected at ({attribution['detection_point']['lat']}, {attribution['detection_point']['lon']})
on {attribution.get('timestamp')}.

Wind: {wind.get('speed_ms', '?'):.1f} m/s from {wind.get('direction_deg', '?'):.0f}°.

Top attributed source zone: ({top.get('zone', {}).get('lat')}, {top.get('zone', {}).get('lon')})
Category: {top.get('source_category')} | Confidence: {top.get('confidence', 0)*100:.0f}%
Key signals: {top.get('contributing_features', {})}

Forecast: peak AQI {peak_aqi}. Severe threshold breached: {breach}.

Write a 2-3 sentence plain-language explanation of why this source was flagged,
suitable for a non-technical municipal official."""


def _deterministic_fallback(attribution: dict, forecast: dict) -> str:
    top = attribution.get("ranked_zones", [{}])[0] if attribution.get("ranked_zones") else {}
    cat = top.get("source_category", "unknown")
    conf = top.get("confidence", 0) * 100
    wind = attribution.get("wind", {})
    return (
        f"A pollution spike was detected and traced upwind using atmospheric dispersion modelling. "
        f"The most likely source category is {cat} (confidence: {conf:.0f}%), "
        f"based on wind direction ({wind.get('direction_deg', '?'):.0f}°), "
        f"land use data, and proximity to registered emission sources. "
        f"Forecast indicates peak AQI of {forecast.get('peak_aqi', '?')}."
    )


def reasoning_agent(state: PipelineState) -> dict:
    attribution = state.get("attribution_output", {})
    forecast = state.get("forecast_output", {})
    logger.info("[ReasoningAgent] building explanation for top zone: %s",
                attribution.get("ranked_zones", [{}])[0].get("source_category") if attribution.get("ranked_zones") else "none")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("[ReasoningAgent] ANTHROPIC_API_KEY not set, using fallback")
        text = _deterministic_fallback(attribution, forecast)
        status = {"status": "degraded", "error": "ANTHROPIC_API_KEY not set"}
    else:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_prompt(attribution, forecast)}],
                timeout=15.0,
            )
            text = response.content[0].text.strip()
            status = {"status": "done", "error": None}
            logger.info("[ReasoningAgent] Claude response received (%d chars)", len(text))
        except Exception as e:
            logger.error("[ReasoningAgent] Claude call failed: %s", e)
            text = _deterministic_fallback(attribution, forecast)
            status = {"status": "degraded", "error": str(e)}

    trace_entry = {
        "agent": "ReasoningAgent",
        "input_summary": {
            "top_category": attribution.get("ranked_zones", [{}])[0].get("source_category") if attribution.get("ranked_zones") else None,
            "peak_aqi": forecast.get("peak_aqi"),
        },
        "output_summary": {"text_length": len(text), "llm_used": status["status"] == "done"},
        "status": status["status"],
    }

    return {
        "reasoning_text": text,
        "reasoning_status": status,
        "trace": state.get("trace", []) + [trace_entry],
    }
