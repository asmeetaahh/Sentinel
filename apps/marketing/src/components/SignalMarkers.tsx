import { Activity, Sparkles, Store, TrendingUp } from 'lucide-react'
import type { ComponentType } from 'react'

import { ORBITS, ellipseY, type OrbitName } from '@/lib/orbitalGeometry'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

/** The icon+label pill sits above the connector line before the ring
 * intersection point is reached, so the raw geometric line length
 * overshoots the ring by roughly the pill's own height — this trims it
 * back. */
const TOP_HEADER_OFFSET = 50

interface TopMarker {
  label: string
  icon: ComponentType<{ size?: number; strokeWidth?: number }>
  x: number
  nodeY: number
  orbit: OrbitName
  color: string
  labelColor: string
}

/**
 * Each marker is wired to its OWN named orbit (see lib/orbitalGeometry
 * and OrbitalField's ASSIGNED_RINGS) — every concept has an unmistakably
 * distinct trajectory:
 *
 * - Merchant: dead-center above the sphere, targeting the innermost
 *   ring — since that ring's top arc sits behind the sphere itself, the
 *   connector visually plugs straight into the core, which is the
 *   intended read ("points directly toward the central orb").
 * - Risk Signals: upper-LEFT, outside the sphere, targeting the
 *   second-smallest ring (the "second inner ring").
 * - Financial Impact: upper-right, targeting the outermost ring,
 *   restrained amber.
 * - Intelligence: below, offset just enough that its connector reaches
 *   a point on its ring that clears the sphere's silhouette (a purely
 *   vertical line at x=0 would land behind the sphere, the same way
 *   Merchant's does — Intelligence needs to visibly touch its own ring,
 *   not disappear into the core).
 */
const TOP_MARKERS: TopMarker[] = [
  { label: 'MERCHANT', icon: Store, x: 0, nodeY: -190, orbit: 'merchant', color: '#a89bfb', labelColor: 'rgba(244,246,250,0.75)' },
  { label: 'RISK SIGNALS', icon: Activity, x: -160, nodeY: -205, orbit: 'riskSignals', color: '#a89bfb', labelColor: 'rgba(244,246,250,0.65)' },
  { label: 'FINANCIAL IMPACT', icon: TrendingUp, x: 260, nodeY: -155, orbit: 'financialImpact', color: '#f0a35f', labelColor: 'rgba(240,163,95,0.85)' },
]

const BOTTOM_MARKER = {
  label: 'INTELLIGENCE',
  icon: Sparkles,
  x: 140,
  nodeY: 195,
  orbit: 'intelligence' as OrbitName,
  color: '#a89bfb',
  labelColor: 'rgba(244,246,250,0.65)',
}

function Pill({
  icon: Icon,
  label,
  color,
  labelColor,
}: {
  icon: ComponentType<{ size?: number; strokeWidth?: number }>
  label: string
  color: string
  labelColor: string
}) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 whitespace-nowrap backdrop-blur-sm"
      style={{ borderColor: `${color}40`, background: 'rgba(8,7,16,0.55)' }}
    >
      <Icon size={11} strokeWidth={2} />
      <span className="text-[10px] font-medium tracking-[0.14em] uppercase" style={{ color: labelColor }}>
        {label}
      </span>
    </div>
  )
}

/**
 * The four signal points, each wired to a real intersection with its own
 * named orbit (via lib/orbitalGeometry) rather than a connector line of
 * an arbitrary guessed length. Every assigned orbit is axis-aligned (no
 * static tilt), so this straight-line intersection is exact and stays
 * exact — the ring's geometry never moves; only its dash phase animates.
 * Markers are fixed in place (only a small CSS float/pulse). Desktop/
 * tablet only — see HeroScene; too dense to keep legible below ~768px.
 */
export function SignalMarkers() {
  const reduceMotion = usePrefersReducedMotion()

  return (
    <div className="absolute" style={{ left: 0, top: 0 }}>
      {TOP_MARKERS.map((marker, index) => {
        const ring = ORBITS[marker.orbit]
        const endY = ellipseY(marker.x, ring, true)
        const lineHeight = Math.max(24, endY - marker.nodeY - TOP_HEADER_OFFSET)
        return (
          <div
            key={marker.label}
            className="absolute flex -translate-x-1/2 flex-col items-center"
            style={{
              left: marker.x,
              top: marker.nodeY,
              animation: reduceMotion ? 'none' : `marker-float ${6 + index}s ease-in-out infinite`,
              animationDelay: `${index * 0.6}s`,
              color: marker.color,
            }}
          >
            <Pill icon={marker.icon} label={marker.label} color={marker.color} labelColor={marker.labelColor} />
            <span className="mt-2 h-2 w-2 rotate-45" style={{ background: marker.color, boxShadow: `0 0 10px 1px ${marker.color}` }} />
            <span
              className="w-px"
              style={{ height: lineHeight, background: `linear-gradient(to bottom, ${marker.color}, transparent)`, opacity: 0.45 }}
            />
          </div>
        )
      })}

      {(() => {
        const ring = ORBITS[BOTTOM_MARKER.orbit]
        const endY = ellipseY(BOTTOM_MARKER.x, ring, false)
        const lineHeight = Math.max(24, BOTTOM_MARKER.nodeY - endY)
        return (
          <div
            className="absolute flex -translate-x-1/2 flex-col items-center"
            style={{
              left: BOTTOM_MARKER.x,
              top: endY,
              animation: reduceMotion ? 'none' : 'marker-float 8s ease-in-out infinite',
              animationDelay: '0.3s',
              color: BOTTOM_MARKER.color,
            }}
          >
            <span
              className="w-px"
              style={{
                height: lineHeight,
                background: `linear-gradient(to top, ${BOTTOM_MARKER.color}, transparent)`,
                opacity: 0.45,
              }}
            />
            <span
              className="mt-2 h-2 w-2 rotate-45"
              style={{ background: BOTTOM_MARKER.color, boxShadow: `0 0 10px 1px ${BOTTOM_MARKER.color}` }}
            />
            <div className="mt-2">
              <Pill icon={BOTTOM_MARKER.icon} label={BOTTOM_MARKER.label} color={BOTTOM_MARKER.color} labelColor={BOTTOM_MARKER.labelColor} />
            </div>
          </div>
        )
      })()}
    </div>
  )
}
