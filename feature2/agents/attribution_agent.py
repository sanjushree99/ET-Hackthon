"""
Attribution Agent
Wraps Feature 1's run_attribution() as a LangGraph node.
Reads: spike_input
Writes: attribution_output, attribution_status, trace
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "feature1"))

from attribution import run_attribution
from agents.state import PipelineState

logger = logging.getLogger("attribution_agent")


def attribution_agent(state: PipelineState) -> dict:
    inp = state["spike_input"]
    logger.info("[AttributionAgent] input: %s", inp)

    try:
        result = run_attribution(
            detection_lat=inp["lat"],
            detection_lon=inp["lon"],
            timestamp=datetime.fromisoformat(inp["timestamp"]),
            observed_concentration_ugm3=inp["observed_concentration_ugm3"],
        )
        status = {"status": "done", "error": None}
        logger.info("[AttributionAgent] top zone: %s",
                    result["ranked_zones"][0] if result.get("ranked_zones") else "none")
    except Exception as e:
        logger.error("[AttributionAgent] failed: %s", e)
        result = {"error": str(e)}
        status = {"status": "degraded", "error": str(e)}

    trace_entry = {
        "agent": "AttributionAgent",
        "input": inp,
        "output_summary": {
            "candidate_count": result.get("candidate_count"),
            "top_zone": result.get("ranked_zones", [{}])[0] if result.get("ranked_zones") else None,
        },
        "status": status["status"],
    }

    return {
        "attribution_output": result,
        "attribution_status": status,
        "trace": state.get("trace", []) + [trace_entry],
    }
