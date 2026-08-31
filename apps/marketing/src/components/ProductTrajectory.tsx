import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const VIEWBOX = '0 0 600 260'
const TODAY_X = 380

// Observed (solid, confident) and projected (dashed, modeled) halves of
// one curve, sharing the junction point at TODAY_X — a real product's
// "here's what happened, here's where the model thinks it's headed"
// convention, not the narrative "growth into a crash" shape Sections
// 03/05 draw. Deliberately its own smaller viewBox and shape so this
// reads as a product screen, not a recreation of the trajectory hero.
const OBSERVED_D = 'M 0,205 C 80,196 150,172 230,158 C 280,150 330,138 380,120'
const PROJECTED_D = 'M 380,120 C 430,104 480,84 600,52'

interface ProductTrajectoryProps {
  className?: string
}

/**
 * The trajectory view inside Sentinel's product panel (see
 * ProductSection). Same gradient/line language as RiskTrajectory and
 * SimulationTrajectory (violet → amber, round caps, a soft drop-shadow)
 * but a single line with a "today" marker splitting observed history
 * from a dashed modeled projection — the product's own view, not a copy
 * of Section 03's curve.
 */
export function ProductTrajectory({ className }: ProductTrajectoryProps) {
  const reduceMotion = usePrefersReducedMotion()
  const wrapperRef = useRef<SVGSVGElement>(null)
  const observedRef = useRef<SVGPathElement>(null)

  useEffect(() => {
    const svg = wrapperRef.current
    const path = observedRef.current
    if (!svg || !path) return

    const length = path.getTotalLength()
    path.style.strokeDasharray = String(length)

    if (reduceMotion) {
      path.style.strokeDashoffset = '0'
      return
    }

    path.style.strokeDashoffset = String(length)
    path.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)'

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
      { threshold: 0.4 },
    )
    observer.observe(svg)
    return () => observer.disconnect()
  }, [reduceMotion])

  return (
    <svg
      ref={wrapperRef}
      aria-hidden
      viewBox={VIEWBOX}
      preserveAspectRatio="xMidYMid meet"
      className={`pointer-events-none h-full w-full overflow-visible ${className ?? ''}`}
    >
      <defs>
        <linearGradient id="productGradient" x1="0%" y1="0%" x2="100%" y2="0%" gradientUnits="objectBoundingBox">
          <stop offset="0%" stopColor="#a89bfb" />
          <stop offset="55%" stopColor="#8b7bf7" />
          <stop offset="100%" stopColor="#c8a37e" />
        </linearGradient>
      </defs>

      <line x1={TODAY_X} y1={20} x2={TODAY_X} y2={240} stroke="#8b93ab" strokeWidth={1.25} strokeDasharray="3 5" opacity={0.4} />
      <text x={TODAY_X} y={14} fontSize={10} fontWeight={500} letterSpacing="0.12em" fill="rgba(244,246,250,0.45)" textAnchor="middle" style={{ textTransform: 'uppercase' }}>
        Today
      </text>

      <path ref={observedRef} d={OBSERVED_D} fill="none" stroke="url(#productGradient)" strokeWidth={3} strokeLinecap="round" style={{ filter: 'drop-shadow(0 0 5px rgba(139,123,247,0.35))' }} />
      <path d={PROJECTED_D} fill="none" stroke="url(#productGradient)" strokeWidth={2.25} strokeLinecap="round" strokeDasharray="1 7" opacity={0.85} />

      <circle cx={TODAY_X} cy={120} r={3} fill="#c9befb" style={{ filter: 'drop-shadow(0 0 4px rgba(201,190,251,0.7))' }} />
      <g>
        <circle
          cx={600}
          cy={52}
          r={3.5}
          fill="#c8a37e"
          style={{ animation: reduceMotion ? 'none' : 'glow-breathe 4.5s ease-in-out infinite', filter: 'drop-shadow(0 0 5px rgba(200,163,126,0.6))' }}
        />
      </g>
    </svg>
  )
}
