import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { ScrollTrigger } from '@/lib/gsap'

/**
 * SignalEmergence (02)'s own signal-divergence device — several faint
 * "trusted" lines moving together, one brighter line breaking away —
 * adapted (not reused verbatim) for 04's own viewBox and much taller
 * `h-dvh` composition. A first attempt imported RiskDivergence directly,
 * but its 1100×320 viewBox, `preserveAspectRatio="slice"`-scaled into
 * 04's much taller pane, stretched the divergent line into a full
 * diagonal that cut straight through the centered text — the opposite of
 * "noticeable but not overpowering." Keeping every line confined to a
 * band above the text column (y roughly 60–260 of 900) fixes that while
 * keeping the same visual device and the same orange/violet language.
 */
const TRUSTED_LINES = [
  'M -40,180 C 400,170 900,195 1480,175',
  'M -40,215 C 400,207 900,228 1480,205',
  'M -40,250 C 400,244 900,258 1480,232',
]
const DIVERGENT_LINE = 'M -40,205 C 400,195 800,140 1480,60'

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

/** Fades in over [inStart, inEnd], holds at 1, fades out over
 * [outStart, outEnd] — lets three text "acts" cross-fade in place
 * without layout shift as one continuous scrub drives all of them. */
function bandOpacity(progress: number, inStart: number, inEnd: number, outStart: number, outEnd: number) {
  if (progress <= inStart) return 0
  if (progress < inEnd) return (progress - inStart) / (inEnd - inStart)
  if (progress <= outStart) return 1
  if (progress < outEnd) return 1 - (progress - outStart) / (outEnd - outStart)
  return 0
}

const PARTICLES = [
  { left: '28%', top: '30%', dx: 16, dy: 10 },
  { left: '72%', top: '28%', dx: -14, dy: 12 },
  { left: '24%', top: '72%', dx: 14, dy: -10 },
  { left: '76%', top: '74%', dx: -16, dy: -12 },
]

/**
 * "04 — Explain": the same complete three-act narrative as before —
 * (1) the signals existed but were fragmented, (2) the turn ("when the
 * signals move together, the story changes"), (3) the Sentinel reveal —
 * restored in full after an earlier visual-only redesign accidentally
 * dropped acts 1 and 2. Only the VISUAL treatment changes here: the
 * previous foreground diagram (short signal traces + a converging core)
 * is replaced with SignalEmergence (02)'s own atmosphere — radial glow,
 * faint grid, distant traces, a few quiet particles — kept continuous
 * behind the text across all three acts rather than swapped per-beat.
 *
 * Tall (`h-[260dvh]`) with a `position: sticky` inner pane, one
 * `ScrollTrigger` scrubbing a single `progress` value that every visual
 * (text opacity/position, particle drift, the reveal-phase glow) reads
 * directly — the same non-scroll-jacking, direct-write pattern
 * TrajectorySection established, reused here instead of introducing a
 * second animation mechanism for a three-beat sequence.
 */
export function ExplainSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const act1Ref = useRef<HTMLDivElement>(null)
  const turnRef = useRef<HTMLDivElement>(null)
  const revealRef = useRef<HTMLDivElement>(null)
  const pulseWrapRef = useRef<HTMLDivElement>(null)
  const particleRefs = useRef<(HTMLDivElement | null)[]>([])
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const act1 = act1Ref.current
    const turn = turnRef.current
    const reveal = revealRef.current
    const pulseWrap = pulseWrapRef.current
    const particles = particleRefs.current.filter((el): el is HTMLDivElement => el !== null)
    if (!section || !act1 || !turn || !reveal || !pulseWrap) return

    const applyProgress = (progress: number) => {
      const act1Opacity = bandOpacity(progress, 0, 0.05, 0.5, 0.6)
      const turnOpacity = bandOpacity(progress, 0.6, 0.68, 0.74, 0.8)
      const revealOpacity = bandOpacity(progress, 0.82, 0.94, 1, 1)

      act1.style.opacity = String(act1Opacity)
      act1.style.transform = `translateY(${(1 - act1Opacity) * 14}px)`
      turn.style.opacity = String(turnOpacity)
      turn.style.transform = `translateY(${(1 - turnOpacity) * 14}px)`
      reveal.style.opacity = String(revealOpacity)
      reveal.style.transform = `translateY(${(1 - revealOpacity) * 14}px)`

      // The reveal-phase pulse behind "Sentinel" — quiet, timed to when
      // the word itself becomes visible, not before.
      const pulseT = clamp01((progress - 0.75) / 0.2)
      pulseWrap.style.opacity = String(pulseT)

      // Particles stay faintly present as ambient atmosphere through
      // acts 1–2, then converge and brighten slightly for the reveal.
      const convergeT = clamp01((progress - 0.75) / 0.2)
      const baseT = clamp01(progress / 0.06)
      particles.forEach((el, index) => {
        const particle = PARTICLES[index]
        const opacity = Math.max(baseT * 0.28, convergeT * 0.55)
        const dx = particle.dx * (1 - convergeT)
        const dy = particle.dy * (1 - convergeT)
        el.style.opacity = String(opacity)
        el.style.transform = `translate(${dx}px, ${dy}px)`
      })
    }

    if (reduceMotion) {
      applyProgress(1)
      return
    }

    applyProgress(0)
    const trigger = ScrollTrigger.create({
      trigger: section,
      start: 'top top',
      end: 'bottom bottom',
      scrub: true,
      onUpdate: (self) => applyProgress(clamp01(self.progress)),
    })

    return () => trigger.kill()
  }, [reduceMotion])

  return (
    <section ref={sectionRef} className="relative h-[260dvh]">
      <div className="bg-background sticky top-0 flex h-dvh items-center justify-center overflow-hidden px-6 text-center sm:px-10">
        {/* Atmosphere — SignalEmergence (02)'s own visual language, kept
            continuous across all three acts rather than swapped per-beat. */}
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background: 'radial-gradient(closest-side, rgba(124,108,246,0.1), rgba(124,108,246,0) 70%)',
            animation: reduceMotion ? 'none' : 'atmosphere-drift 16s ease-in-out infinite',
          }}
        />
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(244,246,250,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(244,246,250,0.5) 1px, transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
        {/* The same signal treatment SignalEmergence (02) established:
            several faint "trusted" lines moving together, and one
            brighter, slowly animated orange line breaking away — the
            emerging signal against the surrounding noise. Confined to a
            band above the text (see TRUSTED_LINES/DIVERGENT_LINE above)
            so it stays "noticeable but not overpowering." */}
        <svg
          aria-hidden
          viewBox="0 0 1440 900"
          preserveAspectRatio="xMidYMid slice"
          className="pointer-events-none absolute inset-0 h-full w-full"
        >
          {TRUSTED_LINES.map((d) => (
            <path key={d} d={d} fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.18} />
          ))}
          <path
            d={DIVERGENT_LINE}
            fill="none"
            stroke="#f0a35f"
            strokeWidth={1.5}
            opacity={0.55}
            strokeDasharray="4 7"
            style={{ animation: reduceMotion ? 'none' : 'signal-flow 6s linear infinite', filter: 'drop-shadow(0 0 4px rgba(240,163,95,0.5))' }}
          />
        </svg>

        {PARTICLES.map((particle, index) => (
          <div
            key={particle.left}
            ref={(el) => {
              particleRefs.current[index] = el
            }}
            aria-hidden
            className="pointer-events-none absolute h-1.5 w-1.5 rounded-full bg-[#c9befb]"
            style={{
              left: particle.left,
              top: particle.top,
              opacity: 0,
              filter: 'drop-shadow(0 0 4px rgba(201,190,251,0.6))',
            }}
          />
        ))}

        {/* Reveal-phase glow — outer wrapper carries the scrub-driven
            opacity, inner element carries the infinite breathing loop
            (kept on separate elements: a running `animation` that
            declares `opacity` in its own keyframes continuously
            overrides a competing static opacity on the SAME element). */}
        <div ref={pulseWrapRef} aria-hidden className="pointer-events-none absolute" style={{ opacity: 0 }}>
          <div
            className="h-[380px] w-[380px] rounded-full sm:h-[560px] sm:w-[560px]"
            style={{
              background: 'radial-gradient(closest-side, rgba(124,108,246,0.16), rgba(124,108,246,0) 72%)',
              animation: reduceMotion ? 'none' : 'glow-breathe 7s ease-in-out infinite',
            }}
          />
        </div>

        <div className="relative mx-auto min-h-[520px] w-full max-w-2xl sm:min-h-[420px]">
          {/* ACT 1 — the signals existed, but were fragmented */}
          <div ref={act1Ref} className="absolute inset-x-0 top-0" style={{ opacity: 0 }}>
            <p className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
              The signals were already there
            </p>
            <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
              The clues appear before the shock.
            </h2>
            <div className="mt-6 space-y-1 text-sm text-muted-foreground/90 sm:text-base">
              <p>A change in transaction behavior.</p>
              <p>A rise in disputes.</p>
              <p>A shift in payment velocity.</p>
              <p>Increasing concentration.</p>
            </div>
            <p className="mt-5 text-sm text-muted-foreground/70 sm:text-base">None of these signals alone tells the whole story.</p>
            <p className="mx-auto mt-5 max-w-sm text-base text-muted-foreground sm:text-lg">
              The problem is not a lack of data.
              <br />
              It&apos;s knowing when the pattern is changing.
            </p>
          </div>

          {/* THE TURN — a single transitional line */}
          <div ref={turnRef} className="absolute inset-x-0 top-0" style={{ opacity: 0 }}>
            <p className="mx-auto max-w-lg text-2xl leading-snug font-medium tracking-tight text-balance sm:text-4xl">
              But when the signals move together, the story changes.
            </p>
          </div>

          {/* THE REVEAL — Sentinel */}
          <div ref={revealRef} className="absolute inset-x-0 top-0" style={{ opacity: 0 }}>
            <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Sentinel</p>
            <h2 className="mt-5 text-4xl leading-tight font-semibold tracking-tight text-balance sm:text-6xl">
              That&apos;s why we built{' '}
              <span className="bg-gradient-to-r from-accent to-accent-soft bg-clip-text text-transparent">Sentinel</span>.
            </h2>
            <p className="mx-auto mt-6 max-w-lg text-base text-muted-foreground sm:text-lg">
              Sentinel connects merchant-level signals, detects emerging changes in risk, and turns them into a
              trajectory you can test before the financial shock arrives.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
