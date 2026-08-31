import { useEffect, useRef } from 'react'

import { useIsMobile } from '@/hooks/useIsMobile'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const VIEWBOX = '0 0 1200 700'

/**
 * Same 13-point cubic-bezier structure as RiskTrajectory's own curve (see
 * that component) — the X anchors are identical, and BASELINE_Y is
 * literally the same curve Section 03 draws, so "baseline" here reads as
 * the exact trajectory the visitor already saw, not a new shape. The
 * first four points (through x=460, "growth into rising risk") are
 * identical between the two Y arrays on purpose: the past hasn't
 * changed, only what happens next has — so the two lines share a start
 * and only diverge from the point where an intervention could take
 * effect.
 */
const POINTS_X = [-20, 160, 300, 460, 540, 590, 630, 740, 810, 870, 970, 1090, 1220]
const BASELINE_Y = [540, 480, 380, 290, 245, 190, 150, 175, 320, 440, 530, 575, 600]
const IMPROVED_Y = [540, 480, 380, 290, 270, 235, 210, 220, 245, 260, 250, 235, 220]
const DIVERGE_X = 540

function buildPath(xs: number[], ys: number[]): string {
  let d = `M ${xs[0]},${ys[0]}`
  for (let i = 1; i < xs.length; i += 3) {
    d += ` C ${xs[i]},${ys[i]} ${xs[i + 1]},${ys[i + 1]} ${xs[i + 2]},${ys[i + 2]}`
  }
  return d
}

function lerp(a: number[], b: number[], t: number): number[] {
  return a.map((v, i) => v + (b[i] - v) * t)
}

// The DRAWN baseline is offset a few SVG units below its true Y values —
// purely a rendering choice, not a change to what "baseline" means (the
// simulated line's t=0 shape below still lerps from the real BASELINE_Y).
// At the default, no-intervention slider position the two paths are
// otherwise pixel-identical, and since simulated paints on top, baseline
// would be completely invisible rather than merely faint — a few units
// of separation keeps it visible and traceable at every scenario, not
// just after the user has already moved a slider. (Baseline is now the
// THINNER, duller line — see the two <path> elements below — so this
// offset carries more of the "still clearly visible" weight than stroke
// width does.)
const BASELINE_RENDER_Y = BASELINE_Y.map((y) => y + 11)
const BASELINE_D = buildPath(POINTS_X, BASELINE_RENDER_Y)

interface SimulationTrajectoryProps {
  /** 0 = no intervention (simulated line sits on top of baseline), 1 =
   * full intervention (simulated line reaches its best modeled shape). */
  interventionT: number
}

/**
 * Section 05's graph: the same visual language as RiskTrajectory (same
 * viewBox, same violet→amber gradient, same particle-on-path technique)
 * but showing TWO lines at once — a dim, static "baseline" reference and
 * a bright "simulated" line whose shape is a live interpolation between
 * `BASELINE_Y` and `IMPROVED_Y` driven by `interventionT`. The simulated
 * path's `d` attribute is written directly on every render and a CSS
 * `transition: d` does the smoothing — no per-frame JS animation loop.
 */
export function SimulationTrajectory({ interventionT }: SimulationTrajectoryProps) {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const wrapperRef = useRef<SVGSVGElement>(null)
  const simulatedPathRef = useRef<SVGPathElement>(null)

  useEffect(() => {
    const svg = wrapperRef.current
    const path = simulatedPathRef.current
    if (!svg || !path) return

    const length = path.getTotalLength()
    path.style.strokeDasharray = String(length)

    if (reduceMotion) {
      path.style.strokeDashoffset = '0'
      return
    }

    path.style.strokeDashoffset = String(length)
    path.style.transition = 'stroke-dashoffset 1.8s cubic-bezier(0.4,0,0.2,1), d 0.5s cubic-bezier(0.4,0,0.2,1)'

    if (typeof IntersectionObserver === 'undefined') {
      path.style.strokeDashoffset = '0'
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          path.style.strokeDashoffset = '0'
          observer.disconnect()
        }
      },
      { threshold: 0.35 },
    )
    observer.observe(svg)
    return () => observer.disconnect()
    // Only the mount-time reveal depends on this effect; interventionT
    // changes are handled by the `d` attribute re-render below, smoothed
    // by the same CSS transition set here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduceMotion])

  const simulatedY = lerp(BASELINE_Y, IMPROVED_Y, interventionT)
  const simulatedD = buildPath(POINTS_X, simulatedY)

  return (
    <svg
      ref={wrapperRef}
      aria-hidden
      viewBox={VIEWBOX}
      preserveAspectRatio="xMidYMid meet"
      className="pointer-events-none h-full w-full overflow-visible"
    >
      <defs>
        <linearGradient id="simulatedGradient" x1="0%" y1="0%" x2="100%" y2="0%" gradientUnits="objectBoundingBox">
          <stop offset="0%" stopColor="#c9befb" />
          <stop offset="42%" stopColor="#a89bfb" />
          <stop offset="100%" stopColor="#8b7bf7" />
        </linearGradient>
      </defs>

      {/* The point where "now" sits — everything left of this shares one
          history; everything right of it is where the scenario diverges.
          Thicker and brighter than before (it was reading as almost
          invisible), but still a plain dashed line — secondary to both
          trajectories, just a readable temporal marker. */}
      <line
        x1={DIVERGE_X}
        y1={40}
        x2={DIVERGE_X}
        y2={660}
        stroke="#8b93ab"
        strokeWidth={1.75}
        strokeDasharray="3 5"
        opacity={0.55}
      />
      <text x={DIVERGE_X} y={26} fontSize={12} fontWeight={500} letterSpacing="0.14em" fill="rgba(244,246,250,0.55)" textAnchor="middle" style={{ textTransform: 'uppercase' }}>
        Now
      </text>

      {/* Baseline — secondary: darker, muted gray-violet, no gradient, no
          glow, and thinner than the simulated line, but still opaque and
          solid enough to trace start to end. "If nothing changes." (See
          BASELINE_RENDER_Y above for why it's drawn a few units below its
          true position — otherwise it can go fully invisible under an
          identical-shaped simulated line at the default slider state.) */}
      <path d={BASELINE_D} fill="none" stroke="#6b7086" strokeWidth={isMobile ? 2 : 2.5} strokeLinecap="round" opacity={0.8} />

      {/* Simulated — primary: brighter gradient, thicker, a visible glow —
          the dominant line, its shape driven live by `interventionT`. */}
      <path
        ref={simulatedPathRef}
        d={simulatedD}
        fill="none"
        stroke="url(#simulatedGradient)"
        strokeWidth={isMobile ? 3.5 : 4.5}
        strokeLinecap="round"
        style={{ filter: 'drop-shadow(0 0 7px rgba(168,155,251,0.5))' }}
      />
    </svg>
  )
}
