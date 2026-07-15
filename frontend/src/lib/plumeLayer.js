/**
 * Builds a GeoJSON polygon representing the Gaussian plume cone.
 * Width at each point is proportional to sigma_y (crosswind spread).
 * Opacity gradient is encoded in a separate stops array for the fill-opacity expression.
 */

const DEG = Math.PI / 180

function offsetPoint(lat, lon, bearingDeg, distM) {
  const R = 6371000
  const d = distM / R
  const b = bearingDeg * DEG
  const lat1 = lat * DEG
  const lon1 = lon * DEG
  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b))
  const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2))
  return [lon2 / DEG, lat2 / DEG]
}

export function buildPlumeGeoJSON(backtracePoints, windDirectionDeg) {
  if (!backtracePoints || backtracePoints.length < 2) return null

  // Perpendicular bearing to wind direction
  const perpBearing = (windDirectionDeg + 90) % 360

  // Build left and right edges of the plume cone
  const left  = []
  const right = []

  backtracePoints.forEach((pt, i) => {
    const progress = i / (backtracePoints.length - 1)
    // Width grows with distance (Gaussian spread proxy): max ~2km at 12km
    const halfWidthM = 200 + progress * 1800
    left.push(offsetPoint(pt.lat, pt.lon, perpBearing, halfWidthM))
    right.push(offsetPoint(pt.lat, pt.lon, (perpBearing + 180) % 360, halfWidthM))
  })

  const coords = [...left, ...[...right].reverse(), left[0]]

  return {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [coords] },
    properties: { windDirection: windDirectionDeg },
  }
}

export function confidenceToColor(confidence) {
  // amber → orange → red scale
  if (confidence >= 0.8) return "#ef4444"
  if (confidence >= 0.6) return "#f97316"
  if (confidence >= 0.4) return "#f59e0b"
  return "#eab308"
}

export function categoryIcon(category) {
  const icons = {
    industrial:   "🏭",
    vehicular:    "🚗",
    construction: "🏗️",
    biomass:      "🔥",
    other:        "❓",
  }
  return icons[category] || "❓"
}
