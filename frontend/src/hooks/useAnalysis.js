import { useState, useCallback } from "react"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

export const SAMPLE_SPIKES = [
  { id: 1, lat: 28.6139, lon: 77.2090, timestamp: "2024-11-01T09:00:00", observed_concentration_ugm3: 185, label: "Connaught Place — 09:00" },
  { id: 2, lat: 28.6350, lon: 77.1100, timestamp: "2024-11-01T14:00:00", observed_concentration_ugm3: 210, label: "Mayapuri — 14:00" },
  { id: 3, lat: 28.7000, lon: 77.1600, timestamp: "2024-11-01T18:00:00", observed_concentration_ugm3: 240, label: "Wazirpur — 18:00" },
  { id: 4, lat: 28.5355, lon: 77.2700, timestamp: "2024-11-02T08:00:00", observed_concentration_ugm3: 195, label: "Okhla — 08:00" },
  { id: 5, lat: 28.5921, lon: 77.0460, timestamp: "2024-11-02T11:00:00", observed_concentration_ugm3: 160, label: "Dwarka — 11:00" },
]

export function useAnalysis() {
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [agentStates, setAgentStates] = useState({})

  const analyze = useCallback(async (spike) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setAgentStates({
      attribution: { status: "running" },
      forecast:    { status: "pending" },
      reasoning:   { status: "pending" },
      enforcement: { status: "pending" },
    })

    try {
      const res = await fetch(`${API_BASE}/analyze-spike`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spike),
      })
      if (!res.ok) throw new Error(`API error ${res.status}`)
      const data = await res.json()

      const agents = ["attribution", "forecast", "reasoning", "enforcement"]
      for (let i = 0; i < agents.length; i++) {
        const agent = agents[i]
        await new Promise(r => setTimeout(r, i === 0 ? 0 : 450))
        setAgentStates(prev => ({
          ...prev,
          ...(agents[i + 1] ? { [agents[i + 1]]: { status: "running" } } : {}),
          [agent]: data.agent_outputs[agent],
        }))
      }
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, agentStates, analyze }
}
