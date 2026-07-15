"""
LangGraph graph definition.
Nodes run sequentially: Attribution -> Forecast -> Reasoning -> Enforcement
State is passed as a typed PipelineState dict between nodes.
"""

import logging
from langgraph.graph import StateGraph, END
from agents.state import PipelineState
from agents.attribution_agent import attribution_agent
from agents.forecast_agent import forecast_agent
from agents.reasoning_agent import reasoning_agent
from agents.enforcement_agent import enforcement_agent

logger = logging.getLogger("graph")


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("attribution", attribution_agent)
    graph.add_node("forecast",    forecast_agent)
    graph.add_node("reasoning",   reasoning_agent)
    graph.add_node("enforcement", enforcement_agent)

    graph.set_entry_point("attribution")
    graph.add_edge("attribution", "forecast")
    graph.add_edge("forecast",    "reasoning")
    graph.add_edge("reasoning",   "enforcement")
    graph.add_edge("enforcement", END)

    return graph.compile()


# Singleton compiled graph
pipeline = build_graph()


def run_pipeline(lat: float, lon: float, timestamp: str,
                 observed_concentration_ugm3: float) -> PipelineState:
    initial_state: PipelineState = {
        "spike_input": {
            "lat": lat,
            "lon": lon,
            "timestamp": timestamp,
            "observed_concentration_ugm3": observed_concentration_ugm3,
        },
        "attribution_output": None,
        "attribution_status": {"status": "pending", "error": None},
        "forecast_output": None,
        "forecast_status": {"status": "pending", "error": None},
        "reasoning_text": None,
        "reasoning_status": {"status": "pending", "error": None},
        "enforcement_score": None,
        "enforcement_actions": None,
        "enforcement_text": None,
        "enforcement_status": {"status": "pending", "error": None},
        "trace": [],
    }

    logger.info("[Graph] starting pipeline for spike at (%s, %s) ts=%s", lat, lon, timestamp)
    result = pipeline.invoke(initial_state)
    logger.info("[Graph] pipeline complete. agents: %s",
                [t["agent"] + ":" + t["status"] for t in result.get("trace", [])])
    return result
