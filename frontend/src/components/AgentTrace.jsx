import { useState } from "react"

const STATUS_STYLES = {
  pending:  "bg-surface border-border text-muted",
  running:  "bg-panel border-accent/50 text-text",
  done:     "bg-panel border-green-500/40 text-text",
  degraded: "bg-panel border-yellow-500/40 text-text",
}

const STATUS_DOT = {
  pending:  <span className="w-2 h-2 rounded-full bg-muted inline-block" />,
  running:  <span className="w-2 h-2 rounded-full bg-accent inline-block spin" />,
  done:     <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />,
  degraded: <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />,
}

const AGENT_META = {
  attribution: { label: "Attribution Agent", icon: "🔬", desc: "Gaussian plume + XGBoost classifier" },
  forecast:    { label: "Forecast Agent",    icon: "📈", desc: "24h AQI forecast + threshold check" },
  reasoning:   { label: "Reasoning Agent",   icon: "🧠", desc: "Claude — plain-language explanation" },
  enforcement: { label: "Enforcement Agent", icon: "⚖️",  desc: "Claude — ranked action recommendation" },
}

function JsonBlock({ data }) {
  return (
    <pre className="text-[10px] font-mono text-green-300/80 bg-surface rounded p-3 overflow-auto max-h-48 leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

function AgentCard({ agentKey, agentState, recommendation }) {
  const [expanded, setExpanded] = useState(false)
  const meta   = AGENT_META[agentKey]
  const status = agentState?.status || "pending"
  const isDegraded = status === "degraded"

  const summaryLine = () => {
    if (status === "pending") return "Waiting..."
    if (status === "running") return "Processing..."
    if (agentKey === "attribution") {
      const zones = agentState?.output?.ranked_zones
      return zones ? `${zones.length > 0 ? zones[0].source_category : "?"} · ${(zones?.[0]?.confidence * 100).toFixed(0)}% confidence · ${agentState.output.candidate_count} candidates` : "Done"
    }
    if (agentKey === "forecast") {
      const out = agentState?.output
      return out ? `Peak AQI ${out.peak_aqi} · Severe: ${out.threshold_breached ? "YES" : "no"}` : "Done"
    }
    if (agentKey === "reasoning") return isDegraded ? "Deterministic fallback" : "Claude explanation ready"
    if (agentKey === "enforcement") return isDegraded ? "Deterministic actions" : `Score ${recommendation?.enforcement_score?.toFixed(2)} · Claude recommendation ready`
    return "Done"
  }

  return (
    <div className={`rounded-lg border transition-all slide-in ${STATUS_STYLES[status]}`}>
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
        onClick={() => status !== "pending" && setExpanded(e => !e)}
      >
        <span className="text-lg">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {STATUS_DOT[status]}
            <span className="text-xs font-semibold tracking-wide">{meta.label}</span>
            {isDegraded && (
              <span className="text-[9px] font-mono bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">
                DEGRADED
              </span>
            )}
          </div>
          <div className="text-[11px] text-muted mt-0.5 truncate">{summaryLine()}</div>
        </div>
        {status !== "pending" && (
          <span className="text-muted text-xs">{expanded ? "▲" : "▼"}</span>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border/50 pt-3">
          {isDegraded && (
            <div className="text-[10px] font-mono bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 rounded px-3 py-2">
              ⚠ Claude API unavailable — showing deterministic output only
            </div>
          )}

          {/* Claude prose for reasoning + enforcement */}
          {agentKey === "reasoning" && agentState?.text && (
            <div className="text-xs text-text leading-relaxed bg-surface rounded p-3 border border-border">
              {agentState.text}
            </div>
          )}
          {agentKey === "enforcement" && agentState?.text && (
            <div className="text-xs text-text leading-relaxed bg-surface rounded p-3 border border-border whitespace-pre-line">
              {agentState.text}
            </div>
          )}

          {/* Structured JSON output */}
          {agentKey === "attribution" && agentState?.output && (
            <JsonBlock data={{
              candidate_count: agentState.output.candidate_count,
              wind: agentState.output.wind,
              top_zones: agentState.output.ranked_zones?.slice(0, 2),
            }} />
          )}
          {agentKey === "forecast" && agentState?.output && (
            <JsonBlock data={{
              peak_aqi: agentState.output.peak_aqi,
              threshold_breached: agentState.output.threshold_breached,
              breach_hour: agentState.output.breach_hour,
              model: agentState.output.model,
            }} />
          )}
          {agentKey === "enforcement" && agentState?.actions && (
            <JsonBlock data={{ score: agentState.score, actions: agentState.actions }} />
          )}
        </div>
      )}
    </div>
  )
}

function RecommendationCard({ recommendation, loading }) {
  if (loading) return (
    <div className="rounded-lg border border-accent/30 bg-panel p-4 text-center">
      <div className="text-accent text-xs font-mono animate-pulse">Running pipeline...</div>
    </div>
  )
  if (!recommendation) return null

  const urgencyColor = { immediate: "#ef4444", high: "#f97316", medium: "#f59e0b" }

  return (
    <div className="rounded-lg border-2 border-accent bg-panel p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-accent font-bold text-xs font-mono tracking-widest">RECOMMENDATION</span>
        <span className="ml-auto text-xs font-mono text-muted">
          score <span className="text-accent font-bold">{recommendation.enforcement_score?.toFixed(2)}</span>
        </span>
      </div>

      <div className="flex gap-3 text-xs">
        <div className="bg-surface rounded px-3 py-2 flex-1 text-center">
          <div className="text-muted text-[10px]">SOURCE</div>
          <div className="text-accent font-bold capitalize">{recommendation.top_source_category}</div>
        </div>
        <div className="bg-surface rounded px-3 py-2 flex-1 text-center">
          <div className="text-muted text-[10px]">CONFIDENCE</div>
          <div className="text-text font-bold">{(recommendation.confidence * 100).toFixed(0)}%</div>
        </div>
        <div className={`bg-surface rounded px-3 py-2 flex-1 text-center ${recommendation.severe_threshold_breached ? "border border-alert/40" : ""}`}>
          <div className="text-muted text-[10px]">PEAK AQI</div>
          <div className={`font-bold ${recommendation.severe_threshold_breached ? "text-alert" : "text-text"}`}>
            {recommendation.forecast_peak_aqi?.toFixed(0)}
          </div>
        </div>
      </div>

      {recommendation.enforcement_actions?.map(a => (
        <div key={a.rank} className="flex items-start gap-2 text-xs">
          <span className="font-mono text-muted shrink-0">{a.rank}.</span>
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0"
            style={{ background: (urgencyColor[a.urgency] || "#6b7280") + "22", color: urgencyColor[a.urgency] || "#6b7280" }}
          >
            {a.urgency.toUpperCase()}
          </span>
          <span className="text-text leading-relaxed">{a.action}</span>
        </div>
      ))}
    </div>
  )
}

export default function AgentTrace({ agentStates, result, loading }) {
  const agents = ["attribution", "forecast", "reasoning", "enforcement"]

  return (
    <div className="w-80 flex flex-col bg-panel border-l border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="text-xs font-mono text-muted tracking-widest">AGENT TRACE</div>
        <div className="text-[10px] text-muted/60 mt-0.5">spike → attribution → forecast → reasoning → enforcement</div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {agents.map(key => (
          <AgentCard
            key={key}
            agentKey={key}
            agentState={agentStates[key]}
            recommendation={result?.recommendation}
          />
        ))}

        <RecommendationCard recommendation={result?.recommendation} loading={loading} />
      </div>
    </div>
  )
}
