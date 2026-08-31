import { useIsMobile } from '@/hooks/useIsMobile'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const DESKTOP_VIEWBOX = '0 0 1100 320'
const DESKTOP_TRUSTED = [
  'M 0,150 C 300,138 620,162 1100,150',
  'M 0,205 C 300,195 620,213 1100,198',
  'M 0,258 C 300,250 620,262 1100,248',
]
const DESKTOP_DIVERGENT = 'M 0,222 C 300,214 520,150 1100,58'
const DESKTOP_TIP = { cx: 1100, cy: 58 }

const MOBILE_VIEWBOX = '0 0 400 220'
const MOBILE_TRUSTED = ['M 0,110 C 120,104 260,116 400,108']
const MOBILE_DIVERGENT = 'M 0,132 C 120,126 240,92 400,42'
const MOBILE_TIP = { cx: 400, cy: 42 }

/**
 * The signal-visual for the section right after the hero: several faint
 * trajectories moving together, with one quietly breaking away — a
 * literal reading of "the same signals a merchant trusts can already be
 * pointing somewhere else." Deliberately much quieter than the hero's
 * core: it supports the headline instead of repeating it, and stays
 * behind the text at low opacity so it never competes for attention.
 */
export function RiskDivergence() {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()

  const trusted = isMobile ? MOBILE_TRUSTED : DESKTOP_TRUSTED
  const divergent = isMobile ? MOBILE_DIVERGENT : DESKTOP_DIVERGENT
  const tip = isMobile ? MOBILE_TIP : DESKTOP_TIP
  const viewBox = isMobile ? MOBILE_VIEWBOX : DESKTOP_VIEWBOX

  return (
    <svg
      aria-hidden
      viewBox={viewBox}
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      {trusted.map((d) => (
        <path key={d} d={d} fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.22} />
      ))}
      <path
        d={divergent}
        fill="none"
        stroke="#f0a35f"
        strokeWidth={1.5}
        opacity={0.6}
        strokeDasharray="4 7"
        style={{ animation: reduceMotion ? 'none' : 'signal-flow 6s linear infinite' }}
      />
      <circle cx={tip.cx} cy={tip.cy} r={3} fill="#f0a35f" opacity={0.85} style={{ filter: 'drop-shadow(0 0 6px rgba(240,163,95,0.75))' }} />
    </svg>
  )
}
