import { useState } from "react"
import PlumeMap from "./components/PlumeMap"
import AgentTrace from "./components/AgentTrace"
import SpikeTimeline from "./components/SpikeTimeline"
import { useAnalysis } from "./hooks/useAnalysis"

export default function App() {
  const [selectedSpike, setSelectedSpike] = useState(null)
  const { result, loading, error, agentStates, analyze } = useAnalysis()

  const handleSpikeSelect = (spike) => {
    setSelectedSpike(spike)
    analyze(spike)
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-surface overflow-hidden">

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-4 px-5 py-2.5 bg-panel border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-accent text-lg">🌫️</span>
          <span className="font-bold text-sm tracking-wide text-text">AirWatch</span>
          <span className="text-[10px] font-mono text-muted bg-surface px-2 py-0.5 rounded border border-border ml-1">
            INTELLIGENCE PLATFORM
          </span>
        </div>

        {selectedSpike && (
          <div className="flex items-center gap-2 ml-4 text-xs font-mono text-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-accent inline-block" />
            {selectedSpike.label}
            <span className="text-accent font-bold">{selectedSpike.observed_concentration_ugm3} µg/m³</span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-3">
          {loading && (
            <div className="flex items-center gap-2 text-xs font-mono text-accent">
              <span className="w-2 h-2 rounded-full bg-accent spin inline-block" />
              Analyzing...
            </div>
          )}
          {error && (
            <div className="text-xs font-mono text-alert bg-alert/10 border border-alert/30 px-3 py-1 rounded">
              ⚠ {error}
            </div>
          )}
          <div className="text-[10px] font-mono text-muted border border-border rounded px-2 py-1">
            {result ? (
              <span className="text-green-400">● LIVE</span>
            ) : (
              <span className="text-muted">○ IDLE</span>
            )}
          </div>
        </div>
      </header>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Panel A — Map */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <PlumeMap
            result={result}
            selectedSpike={selectedSpike}
            onMapClick={null}
          />
          <SpikeTimeline
            selectedId={selectedSpike?.id}
            onSelect={handleSpikeSelect}
            loading={loading}
          />
        </div>

        {/* Panel B — Agent Trace */}
        <AgentTrace
          agentStates={agentStates}
          result={result}
          loading={loading}
        />
      </div>
    </div>
  )
}
