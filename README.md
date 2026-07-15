# ET-Hackthon
AirWatch — Agentic Air Quality Intelligence Platform

An agentic system that identifies who or what is causing a pollution spike —
using physics, not just correlation — and turns that into a ranked, explainable
enforcement recommendation and citizen alert, all coordinated by LLM-driven agents.

Built for [Hackathon Name]. Core differentiator: physics-informed source
attribution (Gaussian plume dispersion + ML classifier) feeding a multi-agent
orchestration layer (LangGraph + Claude), instead of a dashboard bolted onto raw
sensor data.


Table of Contents


Overview
Architecture
Features
Tech Stack
Project Structure
Getting Started
Environment Variables
Running the Project
API Reference
Data Sources
Roadmap / Stretch Features
License



Overview

Most air quality tools stop at "here's the AQI right now." AirWatch goes further:
when a pollution spike is detected, it works backward through wind data to identify
which zone plausibly caused it, classifies the likely source category
(industrial / vehicular / construction / biomass burning), and hands that off to a
chain of LLM-driven agents that generate a human-readable explanation and a ranked
enforcement action — with an estimated health cost avoided.

The result is presented on a live map (animated plume visualization) alongside a
transparent, step-by-step trace of every agent's reasoning, so the output isn't a
black box.

Architecture

                    ┌─────────────────────────┐
                    │   Ground + Satellite     │
                    │   + Weather Data Layer   │
                    │  (CAAQMS, Sentinel-5P,   │
                    │      IMD, OSM)           │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │  Source Attribution Engine     │
                 │  1. Gaussian plume backtrace    │
                 │  2. Feature engineering         │
                 │  3. XGBoost classifier +        │
                 │     calibrated confidence       │
                 └───────────────┬───────────────┘
                                 │  structured JSON
                                 ▼
        ┌────────────────────────────────────────────────┐
        │            Multi-Agent Orchestration            │
        │                 (LangGraph)                      │
        │                                                    │
        │  Attribution Agent → Forecast Agent →             │
        │  Reasoning/Explanation Agent (Claude) →           │
        │  Enforcement Agent (Claude)                        │
        └───────────────────────┬────────────────────────┘
                                 │  ranked recommendation
                                 ▼
                 ┌───────────────────────────────┐
                 │        FastAPI Backend         │
                 │      POST /analyze-spike       │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │      React + Mapbox Frontend    │
                 │  • Animated plume map view       │
                 │  • Agent trace dashboard          │
                 └───────────────────────────────┘

Features

#FeatureStatus1Physics-informed pollution source attribution (Gaussian plume + XGBoost classifier)Core — built2Multi-agent orchestration (LangGraph + Claude reasoning/enforcement agents)Core — built3Advanced UI: map-based plume visualization + agent trace dashboardCore — built4AQI monitoring with satellite gap-fill (Kriging/IDW + AOD)Roadmap5AQI forecasting with RMSE-vs-persistence benchmarkingRoadmap6Satellite anomaly detection (Isolation Forest on MODIS/Sentinel-5P)Roadmap7Digital twin map view (animated what-if scenario sliders)Roadmap8Citizen health risk personalizationRoadmap9Regional language advisories (Kannada/Tamil via Claude)Roadmap

See Roadmap for details on items not yet built.

Tech Stack

LayerTechnologyFrontendReact, Tailwind CSS, Mapbox GL JSBackend/APIFastAPI (Python)Agent orchestrationLangGraphLLM reasoningClaude API (Sonnet)Attribution physicsNumPy / SciPy (Gaussian plume model)Attribution MLXGBoost / scikit-learn (calibrated classifier)Geospatial dataPostgreSQL + PostGIS, GeoPandasTime-series storageTimescaleDBExternal dataCPCB/data.gov.in (CAAQMS), IMD weather API, OpenStreetMap

Project Structure

airwatch/
├── backend/
│   ├── attribution/
│   │   ├── plume_model.py        # Gaussian plume dispersion + backtrace
│   │   ├── features.py           # Feature engineering per candidate zone
│   │   └── classifier.py         # XGBoost source classifier + calibration
│   ├── agents/
│   │   ├── graph.py               # LangGraph state graph definition
│   │   ├── attribution_agent.py
│   │   ├── forecast_agent.py
│   │   ├── reasoning_agent.py     # Claude-powered explanation generation
│   │   └── enforcement_agent.py   # Claude-powered action ranking
│   ├── api/
│   │   └── main.py                # FastAPI app, POST /analyze-spike
│   ├── data/
│   │   └── sample/                # Synthetic sample data (wind, industrial registry, OSM extract)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PlumeMap.jsx       # Mapbox plume visualization panel
│   │   │   ├── AgentTrace.jsx     # Agent trace dashboard panel
│   │   │   └── SpikeTimeline.jsx  # Timeline scrubber
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── tailwind.config.js
├── .env.example
└── README.md

Getting Started

Prerequisites


Python 3.10+
Node.js 18+
PostgreSQL 14+ with PostGIS extension
A Claude API key (console.anthropic.com)
(Optional, for live data) CPCB/data.gov.in API key, IMD API access, Google Earth
Engine service account


Installation

bash# Clone the repo
git clone https://github.com/<your-org>/airwatch.git
cd airwatch

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

Environment Variables

Copy .env.example to .env in both backend/ and frontend/ and fill in:

bash# backend/.env
ANTHROPIC_API_KEY=your_claude_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/airwatch
USE_SYNTHETIC_DATA=true          # set false once live API keys are configured
CPCB_API_KEY=                    # optional — leave blank to use sample data
IMD_API_KEY=                     # optional — leave blank to use sample data

# frontend/.env
VITE_MAPBOX_TOKEN=your_mapbox_token
VITE_API_BASE_URL=http://localhost:8000

Running the Project

bash# Terminal 1 — backend
cd backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev

Open http://localhost:5173 to view the dashboard. With USE_SYNTHETIC_DATA=true,
the app runs fully on realistic sample data — no external API keys required to demo.

API Reference

POST /analyze-spike

Runs the full attribution → agent pipeline for a given location and timestamp.

Request body:

json{
  "latitude": 12.9716,
  "longitude": 77.5946,
  "timestamp": "2026-07-15T09:00:00Z"
}

Response:

json{
  "attribution": {
    "candidates": [
      {
        "zone": "...",
        "source_category": "industrial",
        "confidence": 0.82,
        "contributing_features": ["0.4km from registered industrial site", "high traffic density"],
        "plume_backtrace_path": [[...], [...]]
      }
    ]
  },
  "agent_trace": [
    { "agent": "attribution", "status": "done", "output": {} },
    { "agent": "forecast", "status": "done", "output": {} },
    { "agent": "reasoning", "status": "done", "output": { "explanation": "..." } },
    { "agent": "enforcement", "status": "done", "output": { "recommendation": "...", "health_cost_avoided_inr": 0 } }
  ]
}

Data Sources

SourceUsed forAccessCPCB CAAQMSGround-station AQIdata.gov.in APIIMDWind speed/directionIMD APIOpenStreetMapLand use, traffic, amenitiesOverpass APISample/synthetic dataDefault demo modeBundled in backend/data/sample/

If live keys aren't configured, the pipeline automatically falls back to bundled
synthetic data with the same schema, so the demo always runs end-to-end.

Roadmap / Stretch Features

The following were scoped in the original brief but are not part of this build —
listed here for transparency and future work:


AQI monitoring with satellite gap-fill (Kriging/IDW spatial interpolation)
AQI forecasting service with RMSE-vs-persistence benchmarking
Satellite anomaly detection (Isolation Forest on MODIS/Sentinel-5P)
Full digital-twin map view with animated what-if scenario sliders
Citizen health risk personalization and alerting
Regional language (Kannada/Tamil) advisories via Claude + IVR
