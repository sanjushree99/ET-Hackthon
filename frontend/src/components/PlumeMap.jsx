import { useEffect, useRef, useState } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import { buildPlumeGeoJSON, confidenceToColor, categoryIcon } from "../lib/plumeLayer"

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ""
const DELHI_CENTER = [77.209, 28.6139]

export default function PlumeMap({ result, selectedSpike, onMapClick }) {
  const mapContainer = useRef(null)
  const map          = useRef(null)
  const markers      = useRef([])
  const [mapReady, setMapReady] = useState(false)
  const [noToken]    = useState(!MAPBOX_TOKEN)

  // Init map
  useEffect(() => {
    if (noToken || map.current) return
    mapboxgl.accessToken = MAPBOX_TOKEN
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: DELHI_CENTER,
      zoom: 11,
      attributionControl: false,
    })
    map.current.on("load", () => setMapReady(true))
    map.current.on("click", e => onMapClick && onMapClick(e.lngLat))
    return () => map.current?.remove()
  }, [noToken])

  // Render plume + markers when result changes
  useEffect(() => {
    if (!mapReady || !result || noToken) return
    const m = map.current
    const attribution = result.agent_outputs?.attribution?.output
    if (!attribution) return

    // Clear old markers
    markers.current.forEach(mk => mk.remove())
    markers.current = []

    const wind = attribution.wind
    const zones = attribution.ranked_zones || []
    const backtrace = attribution.plume_backtrace_path || []

    // ── Plume cone layer ──────────────────────────────────────────────────
    const plumeGeo = buildPlumeGeoJSON(backtrace, wind.direction_deg)
    if (plumeGeo) {
      if (m.getLayer("plume-fill")) m.removeLayer("plume-fill")
      if (m.getSource("plume"))     m.removeSource("plume")
      m.addSource("plume", { type: "geojson", data: plumeGeo })
      m.addLayer({
        id: "plume-fill",
        type: "fill",
        source: "plume",
        paint: {
          "fill-color": "#f97316",
          "fill-opacity": 0.18,
        },
      })
      // Animate opacity 0 → 0.18 over 2s
      let start = null
      const animatePlume = (ts) => {
        if (!start) start = ts
        const progress = Math.min((ts - start) / 2000, 1)
        if (m.getLayer("plume-fill")) {
          m.setPaintProperty("plume-fill", "fill-opacity", progress * 0.18)
        }
        if (progress < 1) requestAnimationFrame(animatePlume)
      }
      requestAnimationFrame(animatePlume)
    }

    // ── Detection point pulse marker ──────────────────────────────────────
    const dp = attribution.detection_point
    const pulseEl = document.createElement("div")
    pulseEl.innerHTML = `
      <div style="position:relative;width:24px;height:24px">
        <div class="pulse-ring" style="position:absolute;inset:0;border-radius:50%;border:2px solid #ef4444;"></div>
        <div style="position:absolute;inset:4px;border-radius:50%;background:#ef4444;"></div>
      </div>`
    markers.current.push(
      new mapboxgl.Marker({ element: pulseEl, anchor: "center" })
        .setLngLat([dp.lon, dp.lat])
        .setPopup(new mapboxgl.Popup({ offset: 16, className: "mapbox-popup-dark" })
          .setHTML(`<div style="font-family:monospace;font-size:12px;color:#e2e8f0;background:#161b27;padding:8px;border-radius:6px">
            <b style="color:#ef4444">DETECTION POINT</b><br/>
            PM2.5: <b>${attribution.observed_concentration_ugm3} µg/m³</b><br/>
            Wind: ${wind.speed_ms.toFixed(1)} m/s @ ${wind.direction_deg.toFixed(0)}°
          </div>`))
        .addTo(m)
    )

    // ── Candidate zone markers ────────────────────────────────────────────
    zones.forEach((zone, i) => {
      const color = confidenceToColor(zone.confidence)
      const size  = i === 0 ? 36 : 26
      const el    = document.createElement("div")
      el.innerHTML = `
        <div style="
          width:${size}px;height:${size}px;border-radius:50%;
          background:${color};border:${i === 0 ? "3px solid white" : "2px solid " + color};
          display:flex;align-items:center;justify-content:center;
          font-size:${i === 0 ? 16 : 12}px;
          box-shadow:${i === 0 ? "0 0 12px " + color : "none"};
          cursor:pointer;
        ">${categoryIcon(zone.source_category)}</div>`

      const cf = zone.contributing_features
      const popup = new mapboxgl.Popup({ offset: 20, className: "mapbox-popup-dark" })
        .setHTML(`<div style="font-family:monospace;font-size:11px;color:#e2e8f0;background:#161b27;padding:10px;border-radius:6px;min-width:200px">
          <b style="color:${color}">${zone.source_category.toUpperCase()}</b>
          <span style="float:right;color:${color}">${(zone.confidence * 100).toFixed(0)}%</span><br/>
          <hr style="border-color:#1e2535;margin:6px 0"/>
          <div style="color:#9ca3af">dist industrial: <b style="color:#e2e8f0">${cf.dist_to_nearest_industrial} km</b></div>
          <div style="color:#9ca3af">violations: <b style="color:#e2e8f0">${cf.violation_count}</b></div>
          <div style="color:#9ca3af">traffic: <b style="color:#e2e8f0">${(cf.traffic_density * 100).toFixed(0)}%</b></div>
          <div style="color:#9ca3af">land use: <b style="color:#e2e8f0">${cf.land_use}</b></div>
          <div style="color:#9ca3af">downwind: <b style="color:#e2e8f0">${cf.downwind_distance_km} km</b></div>
        </div>`)

      markers.current.push(
        new mapboxgl.Marker({ element: el, anchor: "center" })
          .setLngLat([zone.zone.lon, zone.zone.lat])
          .setPopup(popup)
          .addTo(m)
      )
    })

    // ── Wind vector marker ────────────────────────────────────────────────
    const windEl = document.createElement("div")
    const arrowRot = (wind.direction_deg + 180) % 360
    windEl.innerHTML = `
      <div style="background:#161b27;border:1px solid #1e2535;border-radius:6px;padding:6px 10px;font-family:monospace;font-size:11px;color:#e2e8f0;display:flex;align-items:center;gap:6px">
        <span style="display:inline-block;transform:rotate(${arrowRot}deg);font-size:16px">↑</span>
        <span><b style="color:#f97316">${wind.speed_ms.toFixed(1)}</b> m/s · ${wind.direction_deg.toFixed(0)}°</span>
      </div>`
    markers.current.push(
      new mapboxgl.Marker({ element: windEl, anchor: "bottom-left" })
        .setLngLat([dp.lon + 0.04, dp.lat + 0.02])
        .addTo(m)
    )

    // Fly to detection point
    m.flyTo({ center: [dp.lon, dp.lat], zoom: 12, duration: 1200 })
  }, [result, mapReady])

  if (noToken) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-surface text-muted gap-3">
        <div className="text-4xl">🗺️</div>
        <div className="text-sm font-mono">VITE_MAPBOX_TOKEN not set</div>
        <div className="text-xs opacity-60">Add your Mapbox token to frontend/.env to enable the map</div>
        <div className="mt-4 text-xs font-mono bg-panel border border-border rounded px-4 py-2">
          VITE_MAPBOX_TOKEN=pk.eyJ1...
        </div>
        {result && (
          <div className="mt-4 text-xs text-green-400 font-mono">
            ✓ API data loaded — map will render once token is set
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex-1 relative">
      <div ref={mapContainer} className="w-full h-full" />
      {!result && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-panel/80 border border-border rounded-lg px-6 py-4 text-center">
            <div className="text-2xl mb-2">🌫️</div>
            <div className="text-sm text-muted font-mono">Select a spike below to run analysis</div>
          </div>
        </div>
      )}
    </div>
  )
}
