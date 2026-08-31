/**
 * Shared geometry for the hero's orbital field (OrbitalField.tsx) and its
 * signal markers (SignalMarkers.tsx). Both live inside the same local
 * pixel coordinate space, anchored at the SAME point as IntelligenceCore
 * itself (see HeroScene — all three use the same `left`/`top` percentage
 * anchor) so the rings' geometric center exactly coincides with the
 * sphere's own center, rather than sitting some distance below it.
 *
 * Ring sizes are chosen relative to the sphere's on-screen radius
 * (~135px on desktop): every ring's rx exceeds that radius so at least
 * its left/right extremities clear the sphere's silhouette and read as
 * genuine orbits — Saturn's-rings-around-a-planet, not lines hidden
 * entirely behind an opaque disc.
 *
 * Each of the four concepts gets its own named, axis-aligned (untilted)
 * orbit so a marker's straight-line connector always lands exactly where
 * the ring actually is. Sized so Risk Signals is deliberately the
 * second-smallest ring — the "second inner ring" its marker points to.
 * OrbitalField additionally draws a couple of purely decorative rings
 * (not exported here) for atmospheric density — those may carry a small
 * static tilt since nothing needs to compute an exact intersection with
 * them.
 */

export const RING_CENTER_Y = 0

export const ORBITS = {
  merchant: { rx: 175, ry: 50 },
  riskSignals: { rx: 215, ry: 62 },
  intelligence: { rx: 260, ry: 74 },
  financialImpact: { rx: 310, ry: 88 },
} as const

export type OrbitName = keyof typeof ORBITS

/**
 * The y-coordinate where a vertical line at local x-offset `x` crosses
 * the given ring's boundary. `upper` picks the branch closer to the
 * core (smaller y); pass false for the branch further from it.
 */
export function ellipseY(x: number, ring: { rx: number; ry: number }, upper: boolean): number {
  const t = Math.max(0, 1 - (x / ring.rx) ** 2)
  const dy = ring.ry * Math.sqrt(t)
  return RING_CENTER_Y + (upper ? -dy : dy)
}

/**
 * The ring traced as a closed SVG path — used both to draw it and as an
 * `offset-path` for a particle traveling along it. Two half-arcs rather
 * than one full ellipse arc, since a single 360° arc command is
 * ambiguous in SVG.
 */
export function ellipsePath(ring: { rx: number; ry: number }): string {
  const { rx, ry } = ring
  const cy = RING_CENTER_Y
  return `M ${-rx},${cy} A ${rx},${ry} 0 1 1 ${rx},${cy} A ${rx},${ry} 0 1 1 ${-rx},${cy} Z`
}
