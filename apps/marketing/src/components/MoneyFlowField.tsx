import { useIsMobile } from '@/hooks/useIsMobile'
import { useIsTablet } from '@/hooks/useIsTablet'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

interface FlowParticle {
  delay: number
  duration: string
  size: number
  color?: string
}

interface FlowPath {
  d: string
  color: string
  width: number
  opacity: number
  dashFlow?: true
  dashFlowDuration?: string
  particles: FlowParticle[]
}

interface FlowNode {
  x: number
  y: number
  size: number
  color: string
  duration: string
}

const DESKTOP_VIEWBOX = '0 0 1440 900'

/**
 * All paths run left-to-right (`d` always starts at negative x and ends
 * past 1440) and every particle's `offset-distance` animates 0%→100% in
 * that same direction — the whole field reads as one consistent
 * left-to-right current, matching "money moving through the system"
 * rather than an ambiguous drift.
 *
 * Foreground paths deliberately stay clear of the y≈260–600 band on the
 * left where the headline sits, so the brightest strokes never cross
 * directly through the text; background/middle paths do cross it, but
 * at low enough opacity that thin lines behind bold text don't hurt
 * readability (the same trade already proven out in RiskDivergence).
 */
const BACKGROUND_PATHS: FlowPath[] = [
  { d: 'M -50,100 C 350,80 750,130 1490,90', color: '#8b7bf7', width: 0.5, opacity: 0.1, particles: [{ delay: 0, duration: '22s', size: 1.3 }] },
  {
    d: 'M -50,300 C 380,280 800,330 1490,290',
    color: '#8b7bf7',
    width: 0.5,
    opacity: 0.09,
    dashFlow: true,
    dashFlowDuration: '80s',
    particles: [{ delay: -9, duration: '20s', size: 1.2 }],
  },
  { d: 'M -50,400 C 350,420 780,370 1490,410', color: '#8b7bf7', width: 0.5, opacity: 0.08, particles: [{ delay: -14, duration: '24s', size: 1.2 }] },
  { d: 'M -50,500 C 400,480 830,520 1490,490', color: '#8b7bf7', width: 0.5, opacity: 0.09, particles: [{ delay: -4, duration: '21s', size: 1.3 }] },
  {
    d: 'M -50,640 C 420,660 850,610 1490,650',
    color: '#8b7bf7',
    width: 0.5,
    opacity: 0.11,
    dashFlow: true,
    dashFlowDuration: '95s',
    particles: [{ delay: -17, duration: '23s', size: 1.2 }],
  },
  { d: 'M -50,820 C 450,800 900,840 1490,810', color: '#8b7bf7', width: 0.5, opacity: 0.1, particles: [{ delay: -11, duration: '19s', size: 1.3 }] },
]

const MIDDLE_PATHS: FlowPath[] = [
  { d: 'M -50,250 C 320,220 700,290 1490,240', color: '#a89bfb', width: 1, opacity: 0.26, particles: [{ delay: 0, duration: '13s', size: 1.7 }, { delay: -6, duration: '13s', size: 1.5 }] },
  { d: 'M -50,340 C 350,310 780,390 1490,330', color: '#a89bfb', width: 0.9, opacity: 0.22, particles: [{ delay: -4, duration: '15s', size: 1.6 }] },
  { d: 'M -50,460 C 380,500 820,420 1490,470', color: '#a89bfb', width: 0.9, opacity: 0.22, particles: [{ delay: -9, duration: '14s', size: 1.6 }] },
  { d: 'M -50,560 C 400,590 830,530 1490,580', color: '#a89bfb', width: 1, opacity: 0.28, particles: [{ delay: -2, duration: '12s', size: 1.8 }, { delay: -7, duration: '12s', size: 1.5, color: '#f0a35f' }] },
  { d: 'M -50,600 C 420,570 850,640 1490,600', color: '#a89bfb', width: 0.9, opacity: 0.24, particles: [{ delay: -12, duration: '16s', size: 1.6 }] },
  { d: 'M 50,780 C 450,740 900,810 1490,760', color: '#a89bfb', width: 1, opacity: 0.26, particles: [{ delay: -5, duration: '14s', size: 1.7 }] },
]

const FOREGROUND_PATHS: FlowPath[] = [
  {
    d: 'M -50,150 C 350,120 800,190 1490,140',
    color: '#c9befb',
    width: 1.7,
    opacity: 0.55,
    particles: [
      { delay: 0, duration: '6.5s', size: 2.3 },
      { delay: -0.4, duration: '6.5s', size: 2 },
      { delay: -3.5, duration: '6.5s', size: 2.1 },
    ],
  },
  {
    d: 'M -50,210 C 380,240 820,170 1490,220',
    color: '#c9befb',
    width: 1.5,
    opacity: 0.48,
    particles: [
      { delay: -2, duration: '7.5s', size: 2 },
      { delay: -5, duration: '7.5s', size: 1.9 },
    ],
  },
  {
    d: 'M -50,660 C 420,630 860,700 1490,650',
    color: '#c9befb',
    width: 1.5,
    opacity: 0.48,
    particles: [
      { delay: -1, duration: '8s', size: 2.1 },
      { delay: -4.5, duration: '8s', size: 1.9, color: '#f0a35f' },
    ],
  },
  {
    d: 'M -50,720 C 400,760 850,680 1490,740',
    color: '#c9befb',
    width: 1.7,
    opacity: 0.55,
    particles: [
      { delay: 0, duration: '7s', size: 2.2 },
      { delay: -3, duration: '7s', size: 2 },
    ],
  },
]

/** A handful of static, gently pulsing points along the busier paths —
 * "occasional brighter nodes representing transaction activity," not
 * moving particles. */
const TRANSACTION_NODES: FlowNode[] = [
  { x: 700, y: 245, size: 2.4, color: '#c9befb', duration: '5s' },
  { x: 900, y: 700, size: 2.2, color: '#f0a35f', duration: '6.5s' },
  { x: 420, y: 150, size: 2, color: '#c9befb', duration: '5.8s' },
  { x: 1100, y: 660, size: 2, color: '#a89bfb', duration: '7s' },
]

const TABLET_BACKGROUND_COUNT = 4
const TABLET_MIDDLE_COUNT = 4
const TABLET_FOREGROUND_COUNT = 3

const MOBILE_VIEWBOX = '0 0 500 800'
const MOBILE_PATHS: FlowPath[] = [
  { d: 'M -20,120 C 150,100 350,150 520,110', color: '#8b7bf7', width: 0.6, opacity: 0.14, particles: [{ delay: 0, duration: '16s', size: 1.3 }] },
  { d: 'M -20,220 C 150,190 350,260 520,210', color: '#a89bfb', width: 1, opacity: 0.28, particles: [{ delay: -4, duration: '10s', size: 1.7 }] },
  {
    d: 'M -20,420 C 180,460 350,380 520,430',
    color: '#c9befb',
    width: 1.5,
    opacity: 0.44,
    particles: [
      { delay: -1, duration: '7.5s', size: 2 },
      { delay: -4, duration: '7.5s', size: 1.8, color: '#f0a35f' },
    ],
  },
  { d: 'M -20,560 C 200,540 380,600 520,570', color: '#a89bfb', width: 0.9, opacity: 0.24, particles: [{ delay: -6, duration: '12s', size: 1.5 }] },
  { d: 'M -20,700 C 200,680 380,730 520,700', color: '#8b7bf7', width: 0.6, opacity: 0.15, particles: [{ delay: -9, duration: '14s', size: 1.3 }] },
]

const LAYER_PARALLAX = { background: 4, middle: 8, foreground: 14 }

function FlowLayer({ paths, reduceMotion, parallax }: { paths: FlowPath[]; reduceMotion: boolean; parallax: number }) {
  return (
    <g
      style={{
        transform: `translate3d(calc(var(--parallax-x, 0) * ${parallax}px), calc(var(--parallax-y, 0) * ${parallax}px), 0)`,
      }}
    >
      {paths.map((path) => (
        <g key={path.d}>
          <path
            d={path.d}
            fill="none"
            stroke={path.color}
            strokeWidth={path.width}
            opacity={path.opacity}
            strokeDasharray={path.dashFlow ? '2 16' : undefined}
            style={path.dashFlow && !reduceMotion ? { animation: `dash-flow-cw ${path.dashFlowDuration} linear infinite` } : undefined}
          />
          {!reduceMotion &&
            path.particles.map((particle, index) => (
              <circle
                key={index}
                r={particle.size}
                fill={particle.color ?? path.color}
                style={{
                  offsetPath: `path('${path.d}')`,
                  offsetRotate: '0deg',
                  animation: `flow-particle ${particle.duration} linear infinite`,
                  animationDelay: `${particle.delay}s`,
                  filter: `drop-shadow(0 0 3px ${particle.color ?? path.color})`,
                }}
              />
            ))}
        </g>
      ))}
    </g>
  )
}

function TransactionNodes({ nodes, reduceMotion }: { nodes: FlowNode[]; reduceMotion: boolean }) {
  return (
    <>
      {nodes.map((node) => (
        <circle
          key={`${node.x}-${node.y}`}
          cx={node.x}
          cy={node.y}
          r={node.size}
          fill={node.color}
          style={{
            filter: `drop-shadow(0 0 4px ${node.color})`,
            animation: reduceMotion ? 'none' : `glow-breathe ${node.duration} ease-in-out infinite`,
          }}
        />
      ))}
    </>
  )
}

/**
 * The "money is moving" visual for MoneyMovesSection: a dense, layered
 * field of left-to-right curved flow paths (background/middle/
 * foreground), each carrying small luminous particles that travel
 * continuously via CSS `offset-path` — the same technique the hero's
 * OrbitalField uses for its ring particles, reused here rather than
 * inventing a second motion system. A few static, gently pulsing
 * "transaction nodes" sit along the busier paths.
 *
 * Sixteen paths on desktop (6 background / 6 middle / 4 foreground) is a
 * deliberate step up from an earlier, much sparser version that read as
 * "a few decorative curves" rather than a system. Tablet renders a
 * moderately trimmed subset of the same desktop paths (not a redesign);
 * mobile gets its own simpler five-path set in a portrait viewBox, sized
 * so nothing overflows horizontally.
 *
 * Kept as small, independent path+particle data structures (rather than
 * one hardcoded blob of markup) so a future "risk" variant can add a
 * diverging path without rebuilding this.
 */
export function MoneyFlowField() {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const isTablet = useIsTablet()

  if (isMobile) {
    return (
      <svg
        aria-hidden
        viewBox={MOBILE_VIEWBOX}
        preserveAspectRatio="xMidYMid slice"
        className="pointer-events-none absolute inset-0 h-full w-full"
      >
        <FlowLayer paths={MOBILE_PATHS} reduceMotion={reduceMotion} parallax={0} />
      </svg>
    )
  }

  const background = isTablet ? BACKGROUND_PATHS.slice(0, TABLET_BACKGROUND_COUNT) : BACKGROUND_PATHS
  const middle = isTablet ? MIDDLE_PATHS.slice(0, TABLET_MIDDLE_COUNT) : MIDDLE_PATHS
  const foreground = isTablet ? FOREGROUND_PATHS.slice(0, TABLET_FOREGROUND_COUNT) : FOREGROUND_PATHS
  const nodes = isTablet ? TRANSACTION_NODES.slice(0, 2) : TRANSACTION_NODES

  return (
    <svg
      aria-hidden
      viewBox={DESKTOP_VIEWBOX}
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <FlowLayer paths={background} reduceMotion={reduceMotion} parallax={LAYER_PARALLAX.background} />
      <FlowLayer paths={middle} reduceMotion={reduceMotion} parallax={LAYER_PARALLAX.middle} />
      <FlowLayer paths={foreground} reduceMotion={reduceMotion} parallax={LAYER_PARALLAX.foreground} />
      <TransactionNodes nodes={nodes} reduceMotion={reduceMotion} />
    </svg>
  )
}
