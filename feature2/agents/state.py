"""
LangGraph state schema.
Every agent reads from and writes to this dict.
LLM-generated content is a specific field — never the entire payload.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class SpikeInput(TypedDict):
    lat: float
    lon: float
    timestamp: str                      # ISO-8601
    observed_concentration_ugm3: float


class ForecastResult(TypedDict):
    forecast_aqi: list[dict]            # [{hour, aqi, pm25}]
    threshold_breached: bool
    breach_hour: Optional[int]
    peak_aqi: float
    model: str                          # "synthetic" | "real"


class AgentStatus(TypedDict):
    status: str                         # "pending" | "running" | "done" | "degraded"
    error: Optional[str]


class PipelineState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    spike_input: SpikeInput

    # ── Attribution Agent output ──────────────────────────────────────────────
    attribution_output: Optional[dict]          # full Feature 1 JSON
    attribution_status: AgentStatus

    # ── Forecast Agent output ─────────────────────────────────────────────────
    forecast_output: Optional[ForecastResult]
    forecast_status: AgentStatus

    # ── Reasoning Agent output ────────────────────────────────────────────────
    reasoning_text: Optional[str]               # Claude-generated prose
    reasoning_status: AgentStatus

    # ── Enforcement Agent output ──────────────────────────────────────────────
    enforcement_score: Optional[float]          # weighted priority score
    enforcement_actions: Optional[list[dict]]   # ranked action list
    enforcement_text: Optional[str]             # Claude-generated recommendation
    enforcement_status: AgentStatus

    # ── Observability ─────────────────────────────────────────────────────────
    trace: list[dict]                           # per-agent input/output log
