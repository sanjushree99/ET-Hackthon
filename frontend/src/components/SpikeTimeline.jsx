import { SAMPLE_SPIKES } from "../hooks/useAnalysis"

export default function SpikeTimeline({ selectedId, onSelect, loading }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-panel border-t border-border overflow-x-auto">
      <span className="text-muted text-xs font-mono shrink-0">SPIKES</span>
      {SAMPLE_SPIKES.map(spike => (
        <button
          key={spike.id}
          onClick={() => !loading && onSelect(spike)}
          className={`shrink-0 px-3 py-1.5 rounded text-xs font-mono border transition-all
            ${selectedId === spike.id
              ? "bg-accent border-accent text-white"
              : "bg-surface border-border text-muted hover:border-accent hover:text-text"
            } ${loading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        >
          <span className="block text-[10px] opacity-60">
            {spike.timestamp.split("T")[1].slice(0, 5)}
          </span>
          {spike.label.split("—")[0].trim()}
          <span className="ml-1 text-accent font-bold">{spike.observed_concentration_ugm3}</span>
          <span className="text-[9px] opacity-50"> µg/m³</span>
        </button>
      ))}
      <div className="shrink-0 ml-auto text-[10px] text-muted font-mono">
        ← select spike to analyze
      </div>
    </div>
  )
}
