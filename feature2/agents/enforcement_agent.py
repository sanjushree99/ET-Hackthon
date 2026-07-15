"""
Enforcement Agent
Combines attribution confidence + population vulnerability + violation history
into a weighted priority score, then uses Claude to generate ranked actions.

Scoring formula:
  score = 0.4 * confidence
        + 0.3 * normalised_vulnerability   (hospital/school density — synthetic)
        + 0.3 * normalised_violations

Graceful degradation: deterministic actions returned if Claude fails.

Requires env var: ANTHROPIC_API_KEY
"""

import os
import logging
import anthropic
from agents.state import PipelineState

logger = logging.getLogger("enforcement_agent")

# SYNTHETIC vulnerability index per source category
# Real swap-in: spatial join with hospital/school GIS layer
VULNERABILITY_INDEX = {
    "industrial":   0.6,
    "vehicular":    0.9,   # roads → high population exposure
    "construction": 0.5,
    "biomass":      0.7,
    "other":        0.4,
}

SYSTEM_PROMPT = """You are an environmental enforcement officer writing action recommendations
for municipal authorities. Be specific, actionable, and prioritise by urgency.
Format as a numbered list. Keep under 200 words."""


def _compute_score(top_zone: dict) -> float:
    confidence = top_zone.get("confidence", 0.0)
    cat = top_zone.get("source_category", "other")
    vuln = VULNERABILITY_INDEX.get(cat, 0.4)
    violations = min(top_zone.get("contributing_features", {}).get("violation_count", 0), 10) / 10.0
    return round(0.4 * confidence + 0.3 * vuln + 0.3 * violations, 4)


def _deterministic_actions(top_zone: dict, score: float, forecast: dict) -> list[dict]:
    cat = top_zone.get("source_category", "unknown")
    conf = top_zone.get("confidence", 0) * 100
    zone = top_zone.get("zone", {})
    actions_map = {
        "industrial": [
            {"rank": 1, "action": f"Deploy inspection team to industrial zone ({zone.get('lat')}, {zone.get('lon')})", "urgency": "immediate"},
            {"rank": 2, "action": "Issue 24-hour emission reduction notice to registered units in zone", "urgency": "high"},
            {"rank": 3, "action": "Cross-check OCEMS real-time stack data for violations", "urgency": "high"},
        ],
        "vehicular": [
            {"rank": 1, "action": f"Activate traffic diversion at zone ({zone.get('lat')}, {zone.get('lon')})", "urgency": "immediate"},
            {"rank": 2, "action": "Deploy PUC (Pollution Under Control) check squads on identified corridor", "urgency": "high"},
            {"rank": 3, "action": "Issue public advisory for odd-even or heavy vehicle restriction", "urgency": "medium"},
        ],
        "construction": [
            {"rank": 1, "action": f"Issue stop-work notice to construction sites in zone ({zone.get('lat')}, {zone.get('lon')})", "urgency": "immediate"},
            {"rank": 2, "action": "Mandate water sprinkling and dust suppression within 500m radius", "urgency": "high"},
            {"rank": 3, "action": "Verify anti-smog net compliance at active sites", "urgency": "medium"},
        ],
        "biomass": [
            {"rank": 1, "action": f"Dispatch fire/waste management team to zone ({zone.get('lat')}, {zone.get('lon')})", "urgency": "immediate"},
            {"rank": 2, "action": "Issue burning ban notice under GRAP provisions", "urgency": "high"},
            {"rank": 3, "action": "Coordinate with agriculture dept on stubble burning alerts", "urgency": "medium"},
        ],
    }
    return actions_map.get(cat, [
        {"rank": 1, "action": "Deploy mobile monitoring unit to flagged zone", "urgency": "high"},
        {"rank": 2, "action": "Initiate source apportionment field study", "urgency": "medium"},
    ])


def _build_prompt(top_zone: dict, score: float, reasoning_text: str, forecast: dict) -> str:
    cat = top_zone.get("source_category", "unknown")
    conf = top_zone.get("confidence", 0) * 100
    zone = top_zone.get("zone", {})
    peak_aqi = forecast.get("peak_aqi", "?")
    breach = forecast.get("threshold_breached", False)
    violations = top_zone.get("contributing_features", {}).get("violation_count", 0)

    return f"""Pollution spike attribution summary:
- Source category: {cat} (confidence {conf:.0f}%)
- Zone: ({zone.get('lat')}, {zone.get('lon')})
- Priority score: {score:.2f}/1.0
- Past violations: {violations}
- Forecast peak AQI: {peak_aqi} | Severe threshold breached: {breach}
- Context: {reasoning_text}

Generate a ranked list of 3 enforcement actions for municipal authorities.
For each action include estimated health-cost-avoided framing in INR where relevant.
Be specific to the source category ({cat})."""


def enforcement_agent(state: PipelineState) -> dict:
    attribution = state.get("attribution_output", {})
    forecast = state.get("forecast_output", {})
    reasoning_text = state.get("reasoning_text", "")

    top_zone = attribution.get("ranked_zones", [{}])[0] if attribution.get("ranked_zones") else {}
    score = _compute_score(top_zone)

    logger.info("[EnforcementAgent] score=%.4f category=%s",
                score, top_zone.get("source_category"))

    # Always compute deterministic actions
    det_actions = _deterministic_actions(top_zone, score, forecast)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("[EnforcementAgent] ANTHROPIC_API_KEY not set, using deterministic actions")
        enf_text = "\n".join(f"{a['rank']}. [{a['urgency'].upper()}] {a['action']}" for a in det_actions)
        status = {"status": "degraded", "error": "ANTHROPIC_API_KEY not set"}
    else:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_prompt(top_zone, score, reasoning_text, forecast)}],
                timeout=15.0,
            )
            enf_text = response.content[0].text.strip()
            status = {"status": "done", "error": None}
            logger.info("[EnforcementAgent] Claude response received (%d chars)", len(enf_text))
        except Exception as e:
            logger.error("[EnforcementAgent] Claude call failed: %s", e)
            enf_text = "\n".join(f"{a['rank']}. [{a['urgency'].upper()}] {a['action']}" for a in det_actions)
            status = {"status": "degraded", "error": str(e)}

    trace_entry = {
        "agent": "EnforcementAgent",
        "input_summary": {
            "top_category": top_zone.get("source_category"),
            "confidence": top_zone.get("confidence"),
            "score": score,
        },
        "output_summary": {
            "enforcement_score": score,
            "action_count": len(det_actions),
            "llm_used": status["status"] == "done",
        },
        "status": status["status"],
    }

    return {
        "enforcement_score": score,
        "enforcement_actions": det_actions,
        "enforcement_text": enf_text,
        "enforcement_status": status,
        "trace": state.get("trace", []) + [trace_entry],
    }
