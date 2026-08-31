import { ORBITS, RING_CENTER_Y, ellipsePath } from '@/lib/orbitalGeometry'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const VIOLET = '#a89bfb'
const AMBER = '#f0a35f'

interface AssignedRing {
  key: string
  ring: { rx: number; ry: number }
  color: string
  width: number
  dash: string
  duration: string
  direction: 'cw' | 'ccw'
  opacity: number
}

/**
 * The four PRIMARY orbits — one per concept (see SignalMarkers), each
 * perfectly axis-aligned (no static tilt) so a marker's connector always
 * lands exactly on its boundary. Sized so Risk Signals is deliberately
 * the second-smallest — the "second inner ring" its marker points to.
 * Innermost/second rings are brightest and thickest (PRIMARY); the
 * outer two are visible but softer (SECONDARY). Financial Impact leans
 * amber; the rest stay violet.
 */
const ASSIGNED_RINGS: AssignedRing[] = [
  { key: 'merchant', ring: ORBITS.merchant, color: VIOLET, width: 2.8, dash: '4 5', duration: '22s', direction: 'cw', opacity: 0.85 },
  { key: 'riskSignals', ring: ORBITS.riskSignals, color: VIOLET, width: 2.4, dash: '2 6', duration: '34s', direction: 'ccw', opacity: 0.75 },
  { key: 'intelligence', ring: ORBITS.intelligence, color: VIOLET, width: 2, dash: '3 6', duration: '45s', direction: 'cw', opacity: 0.6 },
  { key: 'financialImpact', ring: ORBITS.financialImpact, color: AMBER, width: 1.9, dash: '3 9', duration: '62s', direction: 'ccw', opacity: 0.55 },
]

/** Purely atmospheric SECONDARY/OUTER rings — no marker depends on
 * these, so they're free to carry a small static tilt for visual
 * variety ("slightly different orientations") without breaking any
 * connector math. Every rx exceeds the sphere's own radius (~135px) so
 * each ring's sides genuinely clear its silhouette instead of being
 * hidden behind it entirely. Faintest at the outside, fading into the
 * background. */
const DECORATIVE_RINGS = [
  { rx: 150, ry: 44, tilt: 3, color: VIOLET, width: 1.4, dash: '1 5', duration: '28s', direction: 'ccw' as const, opacity: 0.3 },
  { rx: 195, ry: 56, tilt: -4, color: VIOLET, width: 1.2, dash: '2 8', duration: '50s', direction: 'cw' as const, opacity: 0.22 },
  { rx: 340, ry: 96, tilt: 5, color: VIOLET, width: 1, dash: '1 7', duration: '70s', direction: 'ccw' as const, opacity: 0.15 },
  { rx: 385, ry: 110, tilt: -6, color: AMBER, width: 1, dash: '2 12', duration: '95s', direction: 'cw' as const, opacity: 0.1 },
]

const AMBIENT_PARTICLES = [
  { x: -255, y: -20, size: 1.6, opacity: 0.4 },
  { x: -185, y: 75, size: 1.3, opacity: 0.3 },
  { x: 70, y: -70, size: 1.4, opacity: 0.35 },
  { x: 215, y: 95, size: 1.8, opacity: 0.4 },
  { x: 305, y: 15, size: 1.3, opacity: 0.3 },
  { x: -55, y: 115, size: 1.3, opacity: 0.28 },
  { x: -320, y: 40, size: 1, opacity: 0.2 },
  { x: 350, y: -30, size: 1, opacity: 0.18 },
  { x: 120, y: 130, size: 1.2, opacity: 0.22 },
]

/**
 * The orbital intelligence field behind the core: four PRIMARY orbits —
 * one per concept (Merchant, Intelligence, Risk Signals, Financial
 * Impact) — plus a few fainter atmospheric rings for density. Every
 * ring's geometry is completely static; only its dash phase animates
 * (`dash-flow-cw`/`-ccw`), which reads as clean, stable rotation with no
 * wobble, since the ellipse itself never moves. A colored particle rides
 * each primary ring's own path via `offset-path` (`orbit-travel-*`),
 * visibly tying that specific trajectory to its concept. Desktop/tablet
 * only — see HeroScene.
 *
 * Shares its coordinate origin with SignalMarkers (see
 * lib/orbitalGeometry) so a marker's connector can be computed to land
 * exactly on a ring's boundary rather than just floating near it.
 */
export function OrbitalField() {
  const reduceMotion = usePrefersReducedMotion()

  return (
    <svg
      aria-hidden
      width={900}
      height={560}
      viewBox="-450 -280 900 560"
      className="absolute overflow-visible"
      style={{ left: -450, top: -280 }}
    >
      <defs>
        <radialGradient id="fieldHaze" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(139,123,247,0.14)" />
          <stop offset="100%" stopColor="rgba(139,123,247,0)" />
        </radialGradient>
      </defs>

      <ellipse cx={0} cy={RING_CENTER_Y} rx={360} ry={155} fill="url(#fieldHaze)" />

      {DECORATIVE_RINGS.map((ring) => (
        <ellipse
          key={ring.rx}
          cx={0}
          cy={RING_CENTER_Y}
          rx={ring.rx}
          ry={ring.ry}
          fill="none"
          stroke={ring.color}
          strokeWidth={ring.width}
          strokeDasharray={ring.dash}
          opacity={ring.opacity}
          style={{
            transformOrigin: `0px ${RING_CENTER_Y}px`,
            transform: `rotate(${ring.tilt}deg)`,
            animation: reduceMotion ? 'none' : `${ring.direction === 'cw' ? 'dash-flow-cw' : 'dash-flow-ccw'} ${ring.duration} linear infinite`,
          }}
        />
      ))}

      {ASSIGNED_RINGS.map((ring) => {
        const path = ellipsePath(ring.ring)
        return (
          <g key={ring.key}>
            <ellipse
              cx={0}
              cy={RING_CENTER_Y}
              rx={ring.ring.rx}
              ry={ring.ring.ry}
              fill="none"
              stroke={ring.color}
              strokeWidth={ring.width}
              strokeDasharray={ring.dash}
              opacity={ring.opacity}
              style={{
                animation: reduceMotion ? 'none' : `${ring.direction === 'cw' ? 'dash-flow-cw' : 'dash-flow-ccw'} ${ring.duration} linear infinite`,
              }}
            />
            <circle
              r={ring.width + 1.2}
              fill={ring.color}
              style={{
                filter: `drop-shadow(0 0 4px ${ring.color})`,
                offsetPath: `path('${path}')`,
                offsetRotate: '0deg',
                animation: reduceMotion
                  ? 'none'
                  : `${ring.direction === 'cw' ? 'orbit-travel-cw' : 'orbit-travel-ccw'} ${ring.duration} linear infinite`,
              }}
            />
          </g>
        )
      })}

      {AMBIENT_PARTICLES.map((p) => (
        <circle key={`${p.x}-${p.y}`} cx={p.x} cy={p.y} r={p.size} fill="#c9befb" opacity={p.opacity} />
      ))}
    </svg>
  )
}
