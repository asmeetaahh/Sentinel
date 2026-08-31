import { useEffect, useRef } from 'react'

import { useIsMobile } from '@/hooks/useIsMobile'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const VIEWBOX = '0 0 1200 700'

/**
 * One continuous curve: a healthy rise (Growth → Rising risk) into a
 * peak (Chargebacks spike), then a sharp drop through Hold/freeze into
 * Cash crunch — "the line still looks fine right up until it doesn't,"
 * which is the whole point of "risk discovered too late." Vertices are
 * reused below as anchor points for labels/markers rather than guessed
 * separately, so everything stays visually attached to the actual curve.
 */
const PATH_D = 'M -20,540 C 160,480 300,380 460,290 C 540,245 590,190 630,150 C 740,175 810,320 870,440 C 970,530 1090,575 1220,600'

const VERTEX = {
  start: { x: -20, y: 540 },
  risingMid: { x: 460, y: 290 },
  peak: { x: 630, y: 150 },
  dropEnd: { x: 870, y: 440 },
  end: { x: 1220, y: 600 },
}

interface StageLabel {
  text: string
  x: number
  y: number
  threshold: number
  hideOnMobile?: boolean
}

/** Quiet, small-caps labels sitting near the curve itself — the "key
 * transition points" in the visual hierarchy, one tier below the two
 * dedicated annotation callouts. Each fades in once the drawn line has
 * reached roughly that point (see the `--reveal`-driven opacity below). */
const STAGE_LABELS: StageLabel[] = [
  { text: 'Growth', x: 20, y: 575, threshold: 0.03 },
  { text: 'Rising risk', x: 300, y: 355, threshold: 0.2, hideOnMobile: true },
  { text: 'Chargebacks spike', x: 560, y: 108, threshold: 0.42 },
  { text: 'Hold / freeze', x: 700, y: 345, threshold: 0.58, hideOnMobile: true },
  { text: 'Cash crunch', x: 1000, y: 640, threshold: 0.9 },
]

interface Annotation {
  text: string
  anchor: { x: number; y: number }
  labelY: number
  threshold: number
}

/** The two restrained, more prominent callouts — a marker dot, a thin
 * connector back to the curve, and a small pill label — reusing the same
 * visual language as the hero's signal markers so this graph reads as
 * part of the same system rather than a bolted-on chart component. */
const ANNOTATIONS: Annotation[] = [
  { text: 'Settlement shock', anchor: VERTEX.peak, labelY: 55, threshold: 0.47 },
  { text: 'Funds blocked', anchor: VERTEX.dropEnd, labelY: 560, threshold: 0.73 },
]

const PARTICLES = [
  { delay: 0, duration: '9s', size: 2 },
  { delay: -3.5, duration: '10s', size: 1.8 },
  { delay: -7, duration: '11s', size: 1.7 },
]

function AnnotationMarker({ annotation }: { annotation: Annotation }) {
  const above = annotation.labelY < annotation.anchor.y
  return (
    <g
      style={{
        opacity: `clamp(0, calc((var(--reveal, 0) - ${annotation.threshold}) * 9), 1)`,
        transform: `translateY(calc((1 - clamp(0, calc((var(--reveal, 0) - ${annotation.threshold}) * 9), 1)) * ${above ? 10 : -10}px))`,
      }}
    >
      <line
        x1={annotation.anchor.x}
        y1={annotation.anchor.y}
        x2={annotation.anchor.x}
        y2={annotation.labelY + (above ? 16 : -16)}
        stroke="#f0a35f"
        strokeWidth={1}
        opacity={0.5}
      />
      <circle cx={annotation.anchor.x} cy={annotation.anchor.y} r={3.5} fill="#f0a35f" style={{ filter: 'drop-shadow(0 0 5px rgba(240,163,95,0.8))' }} />
      <foreignObject x={annotation.anchor.x - 90} y={annotation.labelY - 12} width={180} height={26}>
        <div className="flex justify-center">
          <span className="rounded-full border border-[#f0a35f66] bg-[#0a0710cc] px-2.5 py-1 text-[10px] font-medium tracking-[0.1em] whitespace-nowrap text-[#f2b988] uppercase">
            {annotation.text}
          </span>
        </div>
      </foreignObject>
    </g>
  )
}

/**
 * The trajectory graph for TrajectorySection. The curve's own stroke is
 * progressively revealed by TrajectorySection scrubbing a `--reveal`
 * (0→1) CSS variable on this component's wrapper as the section scrolls
 * — this component just reads it via `stroke-dashoffset` (computed once
 * from the path's real measured length, not guessed) and via `calc()`
 * thresholds on the labels/markers/particles, so everything downstream
 * of the scroll trigger is plain CSS, no per-frame JS.
 */
export function RiskTrajectory() {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const pathRef = useRef<SVGPathElement>(null)

  useEffect(() => {
    const path = pathRef.current
    if (!path) return
    const length = path.getTotalLength()
    path.style.strokeDasharray = String(length)
    // A live `calc()` referencing `--reveal`, not a one-time number —
    // this is what actually makes the stroke draw in as the section
    // scrolls; TrajectorySection updates `--reveal` on an ancestor and
    // this recomputes automatically, the same way the label/marker
    // opacities below do.
    path.style.strokeDashoffset = `calc(${length} * (1 - var(--reveal, 0)))`
  }, [])

  const stageLabels = isMobile ? STAGE_LABELS.filter((label) => !label.hideOnMobile) : STAGE_LABELS

  return (
    <svg aria-hidden viewBox={VIEWBOX} preserveAspectRatio="xMidYMid meet" className="pointer-events-none h-full w-full overflow-visible">
      <defs>
        <linearGradient id="trajectoryGradient" x1="0%" y1="0%" x2="100%" y2="0%" gradientUnits="objectBoundingBox">
          <stop offset="0%" stopColor="#a89bfb" />
          <stop offset="42%" stopColor="#8b7bf7" />
          <stop offset="58%" stopColor="#c8a37e" />
          <stop offset="100%" stopColor="#f0a35f" />
        </linearGradient>
      </defs>

      {/* a very faint, fully-drawn ghost of the same curve — reads as
          "the shape was always there," while the bright stroke on top is
          what's actually revealing */}
      <path d={PATH_D} fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.08} />

      <path
        ref={pathRef}
        d={PATH_D}
        fill="none"
        stroke="url(#trajectoryGradient)"
        strokeWidth={isMobile ? 3.2 : 4.2}
        strokeLinecap="round"
        style={{
          // A single restrained shadow — luminous through the stroke's
          // own color/gradient, not a visible halo. An earlier version
          // stacked three shadows (including a near-white one) for a
          // stronger glow; that read as a neon blob rather than premium,
          // so this reverts to one small, colored shadow.
          filter: 'drop-shadow(0 0 5px rgba(139,123,247,0.3))',
        }}
      />

      {/* Each pulsing/traveling element below is gated by an OUTER <g>'s
          static `opacity: clamp(...)`, with the running `animation` kept
          on the INNER circle only — SVG opacity is multiplicative, so
          this is the only way to have a `--reveal`-driven appear-gate
          coexist with a CSS animation that also declares `opacity`
          (`flow-particle`, `glow-breathe`): a running animation
          continuously overrides a competing static opacity on the SAME
          element for as long as it's active, which silently defeated the
          gate when both lived on one node. */}
      {!reduceMotion &&
        PARTICLES.map((particle, index) => (
          <g key={index} style={{ opacity: 'clamp(0, calc((var(--reveal, 0) - 0.06) * 12), 1)' }}>
            <circle
              r={particle.size}
              fill="#c9befb"
              style={{
                offsetPath: `path('${PATH_D}')`,
                offsetRotate: '0deg',
                animation: `flow-particle ${particle.duration} linear infinite`,
                animationDelay: `${particle.delay}s`,
                filter: 'drop-shadow(0 0 3px rgba(201,190,251,0.8))',
              }}
            />
          </g>
        ))}

      <g style={{ opacity: 'clamp(0, calc((var(--reveal, 0) - 0.45) * 10), 1)' }}>
        <circle
          cx={VERTEX.peak.x}
          cy={VERTEX.peak.y}
          r={3}
          fill="#c9a37e"
          style={{
            animation: reduceMotion ? 'none' : 'glow-breathe 5s ease-in-out infinite',
            filter: 'drop-shadow(0 0 5px rgba(240,163,95,0.6))',
          }}
        />
      </g>
      <g style={{ opacity: 'clamp(0, calc((var(--reveal, 0) - 0.9) * 10), 1)' }}>
        <circle
          cx={VERTEX.end.x}
          cy={VERTEX.end.y}
          r={2.6}
          fill="#f0a35f"
          style={{
            animation: reduceMotion ? 'none' : 'glow-breathe 6s ease-in-out infinite',
            filter: 'drop-shadow(0 0 5px rgba(240,163,95,0.7))',
          }}
        />
      </g>

      {stageLabels.map((label) => (
        <text
          key={label.text}
          x={label.x}
          y={label.y}
          fontSize={15}
          fontWeight={500}
          letterSpacing="0.14em"
          fill="rgba(244,246,250,0.55)"
          style={{
            textTransform: 'uppercase',
            opacity: `clamp(0, calc((var(--reveal, 0) - ${label.threshold}) * 9), 1)`,
          }}
        >
          {label.text}
        </text>
      ))}

      {!isMobile && ANNOTATIONS.map((annotation) => <AnnotationMarker key={annotation.text} annotation={annotation} />)}
    </svg>
  )
}
