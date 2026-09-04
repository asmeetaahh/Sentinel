import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

const STAGES = ['Observed', 'Engineered', 'Tested', 'Explained']

const TRANSITION = 'opacity 0.6s cubic-bezier(0.4,0,0.2,1), transform 0.6s cubic-bezier(0.4,0,0.2,1)'

/** Depth-stack placement for a card at `offset` steps from the active
 * one: 0 = front (hero), +1 = the next card peeking in from behind —
 * "anticipation" — everything else fully receded/hidden. Deliberately
 * asymmetric (nothing peeks on the "already seen" side) since there's no
 * reason to keep showing what the visitor already passed.
 *
 * The four cards hold meaningfully different amounts of content (03's
 * evidence grid is much taller than 01/02/04) — a first version gave the
 * stack a single guessed `min-h`, which overflowed under 03 and visibly
 * covered the prev/next buttons. Fixed here without any JS height
 * measurement: only the ACTIVE card is `position: relative` (so it sits
 * in normal flow and its own content naturally sizes the container);
 * every other card is `position: absolute` with `top/left/right` but
 * deliberately NOT `bottom` — per the CSS spec, an absolutely positioned
 * box with `bottom` left unset sizes to its own content (shrink-to-fit)
 * instead of stretching to the containing block's height, so a shorter
 * or taller peek card never gets cropped or force-stretched either. */
function cardStyle(offset: number, reduceMotion: boolean): CSSProperties {
  const isActive = offset === 0
  const isPeek = offset === 1
  const opacity = isActive ? 1 : isPeek ? 0.3 : 0
  const scale = isActive ? 1 : isPeek ? 0.94 : 0.9
  const translateY = isActive ? 0 : isPeek ? 42 : offset < 0 ? -26 : 30
  const translateX = isActive ? 0 : isPeek ? 16 : 0

  return {
    position: isActive ? 'relative' : 'absolute',
    top: isActive ? undefined : 0,
    left: isActive ? undefined : 0,
    right: isActive ? undefined : 0,
    zIndex: isActive ? 3 : isPeek ? 2 : 1,
    opacity: reduceMotion ? (isActive ? 1 : 0) : opacity,
    transform: reduceMotion ? 'none' : `translate(${translateX}px, ${translateY}px) scale(${scale})`,
    transition: reduceMotion ? 'opacity 0.2s linear' : TRANSITION,
    pointerEvents: isActive ? 'auto' : 'none',
  }
}

/**
 * "09 — Technical Credibility," a sequential depth-stacked card system
 * (one active "hero" card, the next card subtly peeking in behind it)
 * instead of four vertically-stacked content blocks. Background is
 * deliberately plain — a radial glow and a faint grid, nothing else. An
 * intermediate revision added a RiskDivergence (02)-style signal-line
 * field behind the cards; that turned out to be a mistaken addition (02's
 * signal-line language belongs to Research Lab, section 10, not here),
 * so this reverts the background to its clean pre-lines state.
 *
 * All four cards stay mounted and absolutely stacked in one fixed-height
 * frame (same interaction model as ResponseSection/07, extended with a
 * depth "peek" for the upcoming card) — content, technical claims, and
 * numbers are all reused verbatim from the previous vertically-stacked
 * version, only the presentation changed.
 */
export function TechnicalCredibilitySection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const anchorRef = useRef<HTMLParagraphElement>(null)
  const stackRef = useRef<HTMLDivElement>(null)
  const closingRef = useRef<HTMLParagraphElement>(null)
  const reduceMotion = usePrefersReducedMotion()
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const anchor = anchorRef.current
    const stack = stackRef.current
    const closing = closingRef.current
    if (!section || !intro || !anchor || !stack || !closing) return

    const ctx = gsap.context(() => {
      const all = [intro, anchor, stack, closing]
      if (reduceMotion) {
        gsap.set(all, { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }
      gsap.set(all, { opacity: 0, y: 22, filter: 'blur(6px)' })
      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 80%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })
      timeline
        .to(intro, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0)
        .to(anchor, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.2)
        .to(stack, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.4)
      gsap.to(closing, {
        opacity: 1,
        y: 0,
        filter: 'blur(0px)',
        duration: 0.9,
        ease: 'power2.out',
        scrollTrigger: { trigger: closing, start: 'top 85%', toggleActions: 'play none none reverse' },
      })
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  const isFirst = activeIndex === 0
  const isLast = activeIndex === STAGES.length - 1
  const goNext = () => setActiveIndex((i) => Math.min(i + 1, STAGES.length - 1))
  const goPrev = () => setActiveIndex((i) => Math.max(i - 1, 0))

  return (
    <section ref={sectionRef} className="bg-background relative overflow-hidden px-6 py-24 sm:px-10 sm:py-28">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: 'radial-gradient(closest-side, rgba(124,108,246,0.06), rgba(124,108,246,0) 70%)' }}
      />
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(244,246,250,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(244,246,250,0.5) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      <div className="relative mx-auto max-w-3xl">
        {/* Intro — unchanged copy */}
        <div ref={introRef} className="text-center" style={{ opacity: 0 }}>
          <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Technical credibility</p>
          <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">Built to be questioned.</h2>
          <p className="mx-auto mt-5 max-w-lg text-base text-muted-foreground sm:text-lg">
            Sentinel is designed around observable merchant behavior, leakage-controlled features, interpretable risk
            signals, and bounded scenario modeling.
          </p>
        </div>

        {/* The conceptual anchor — echoes Explain (04)'s own eyebrow on
            purpose: what follows is how those signals were captured,
            engineered, tested, and explained. */}
        <p ref={anchorRef} className="mt-10 text-center text-lg font-medium text-foreground/90 sm:mt-12 sm:text-xl" style={{ opacity: 0 }}>
          The signals were already there.
        </p>

        {/* Stage indicator */}
        <div className="mt-10 flex items-center justify-center gap-2.5 sm:mt-12 sm:gap-3">
          {STAGES.map((stage, index) => (
            <div key={stage} className="flex items-center gap-2.5 sm:gap-3">
              <span
                className={`text-[11px] font-medium tracking-[0.1em] uppercase transition-colors duration-300 ${
                  index === activeIndex ? 'text-foreground' : 'text-muted-foreground/45'
                }`}
              >
                {String(index + 1).padStart(2, '0')} {stage}
              </span>
              {index < STAGES.length - 1 && <span aria-hidden className="h-px w-4 bg-white/10 sm:w-6" />}
            </div>
          ))}
        </div>

        {/* Card stack */}
        <div
          ref={stackRef}
          className="relative mx-auto mt-8 min-h-[200px] max-w-xl sm:mt-10"
          style={{ opacity: 0, perspective: '1400px' }}
          aria-live="polite"
        >
          {/* 01 — Observed */}
          <div
            role={activeIndex === 0 ? 'button' : undefined}
            tabIndex={activeIndex === 0 ? 0 : -1}
            aria-label={activeIndex === 0 ? 'Stage 1: Observed. Activate to continue to the next stage.' : undefined}
            aria-hidden={activeIndex !== 0}
            onClick={activeIndex === 0 ? goNext : undefined}
            onKeyDown={
              activeIndex === 0
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      goNext()
                    }
                  }
                : undefined
            }
            className={`rounded-3xl border px-7 py-8 sm:px-9 sm:py-10 ${activeIndex === 0 ? 'cursor-pointer' : ''}`}
            style={{ ...cardStyle(0 - activeIndex, reduceMotion), background: 'rgba(9,10,16,0.92)', borderColor: 'rgba(255,255,255,0.09)' }}
          >
            <p className="text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">01 — Observed</p>
            <h3 className="mt-3 text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
              The model doesn&apos;t get to see the future.
            </h3>
            <div className="mt-8 flex items-center gap-3 sm:gap-5">
              <TimelinePoint label="Observed" active />
              <TimelineLine />
              <TimelinePoint label="Predict" active />
              <TimelineLine long />
              <TimelinePoint label="Outcome" />
            </div>
            <p className="mt-6 max-w-md text-sm text-muted-foreground sm:text-base">
              Every feature is a trailing window ending at the moment of prediction — verified by testing that
              truncating the dataset early reproduces byte-identical feature values. There&apos;s no code path that
              reaches a later row.
            </p>
            {activeIndex === 0 && <CardHint />}
          </div>

          {/* 02 — Engineered */}
          <div
            role={activeIndex === 1 ? 'button' : undefined}
            tabIndex={activeIndex === 1 ? 0 : -1}
            aria-label={activeIndex === 1 ? 'Stage 2: Engineered. Activate to continue to the next stage.' : undefined}
            aria-hidden={activeIndex !== 1}
            onClick={activeIndex === 1 ? goNext : undefined}
            onKeyDown={
              activeIndex === 1
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      goNext()
                    }
                  }
                : undefined
            }
            className={`rounded-3xl border px-7 py-8 sm:px-9 sm:py-10 ${activeIndex === 1 ? 'cursor-pointer' : ''}`}
            style={{ ...cardStyle(1 - activeIndex, reduceMotion), background: 'rgba(9,10,16,0.92)', borderColor: 'rgba(255,255,255,0.09)' }}
          >
            <p className="text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">02 — Engineered</p>
            <h3 className="mt-3 text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">Raw behavior becomes signal.</h3>
            <div className="mt-6 flex flex-wrap gap-2.5">
              {['Refund velocity', 'Fulfillment behavior', 'Customer mix', 'Chargeback trend', 'Payment concentration'].map((label) => (
                <span key={label} className="rounded-full border border-white/[0.09] px-3.5 py-1.5 text-xs font-medium text-foreground/85">
                  {label}
                </span>
              ))}
            </div>
            <p className="mt-6 max-w-md text-sm text-muted-foreground sm:text-base">
              Risk isn&apos;t represented by one transaction. It emerges through changing merchant-level patterns —
              across 55 engineered signals in the current benchmark.
            </p>
            {activeIndex === 1 && <CardHint />}
          </div>

          {/* 03 — Tested */}
          <div
            role={activeIndex === 2 ? 'button' : undefined}
            tabIndex={activeIndex === 2 ? 0 : -1}
            aria-label={activeIndex === 2 ? 'Stage 3: Tested. Activate to continue to the next stage.' : undefined}
            aria-hidden={activeIndex !== 2}
            onClick={activeIndex === 2 ? goNext : undefined}
            onKeyDown={
              activeIndex === 2
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      goNext()
                    }
                  }
                : undefined
            }
            className={`rounded-3xl border px-7 py-8 sm:px-9 sm:py-10 ${activeIndex === 2 ? 'cursor-pointer' : ''}`}
            style={{ ...cardStyle(2 - activeIndex, reduceMotion), background: 'rgba(9,10,16,0.92)', borderColor: 'rgba(255,255,255,0.09)' }}
          >
            <p className="text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">03 — Tested</p>
            <h3 className="mt-3 text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">We tried to break it.</h3>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 sm:gap-5">
              <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] px-5 py-4 sm:px-6 sm:py-5">
                <p className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Hard negatives</p>
                <p className="mt-2 text-sm text-foreground/90">
                  Growth scenarios built to look risky without being risky — festival spikes, viral campaigns, product
                  launches, payment-method shifts.
                </p>
                <p className="mt-2 text-xs text-muted-foreground/80">
                  One hard-negative type — a viral-campaign spike — still produced a false positive on a small sample.
                </p>
              </div>
              <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] px-5 py-4 sm:px-6 sm:py-5">
                <p className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Stress testing</p>
                <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">0.603 → 0.476</p>
                <p className="mt-1 text-xs text-muted-foreground">Precision-recall AUC, normal test → later unseen time window</p>
              </div>
            </div>
            <p className="mt-6 max-w-md text-sm text-muted-foreground sm:text-base">
              We don&apos;t only ask whether the model works. We ask where it fails.
            </p>
            {activeIndex === 2 && <CardHint />}
          </div>

          {/* 04 — Explained */}
          <div
            role={activeIndex === 3 ? 'button' : undefined}
            tabIndex={activeIndex === 3 ? 0 : -1}
            aria-hidden={activeIndex !== 3}
            className="rounded-3xl border px-7 py-8 sm:px-9 sm:py-10"
            style={{ ...cardStyle(3 - activeIndex, reduceMotion), background: 'rgba(9,10,16,0.92)', borderColor: 'rgba(255,255,255,0.09)' }}
          >
            <p className="text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">04 — Explained</p>
            <h3 className="mt-3 text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">A score isn&apos;t enough.</h3>
            <div className="mt-7 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-5">
              <span className="rounded-full border px-3.5 py-1.5 text-xs font-medium text-accent-soft" style={{ borderColor: 'rgba(168,155,251,0.3)' }}>
                Risk elevated
              </span>
              <span aria-hidden className="hidden text-muted-foreground/40 sm:inline">
                →
              </span>
              <div className="flex flex-wrap gap-2.5">
                {['Chargeback trend ↑', 'Refund velocity ↑', 'Fulfillment shift', 'Concentration ↑'].map((label) => (
                  <span key={label} className="rounded-full border border-white/[0.09] px-3.5 py-1.5 text-xs font-medium text-foreground/85">
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground">Why?</span>
              <span aria-hidden className="h-px w-8 bg-accent-soft/60" />
              <span className="text-sm font-medium text-accent-soft">Verified local explanations</span>
            </div>
            <p className="mt-6 max-w-md text-sm text-muted-foreground sm:text-base">
              Sentinel doesn&apos;t stop at a risk score. It exposes the signals behind the change — the same signals
              from Explain, surfaced by explanations independently verified to reconstruct the model&apos;s own
              output.
            </p>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-center gap-3 sm:mt-10">
          <button
            type="button"
            onClick={goPrev}
            disabled={isFirst}
            aria-label="Previous stage"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.08] text-muted-foreground transition-colors duration-200 enabled:hover:border-white/20 enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-25"
          >
            ←
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={isLast}
            aria-label="Next stage"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.08] text-muted-foreground transition-colors duration-200 enabled:hover:border-white/20 enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-25"
          >
            →
          </button>
        </div>

        <p
          ref={closingRef}
          className="mt-16 text-center text-xl font-medium tracking-tight text-balance sm:mt-20 sm:text-2xl"
          style={{ opacity: 0 }}
        >
          We didn&apos;t just ask whether it works. We asked where it breaks.
        </p>
      </div>
    </section>
  )
}

function CardHint() {
  return <p className="mt-6 text-xs font-medium tracking-[0.1em] text-muted-foreground/60 uppercase">Click to continue →</p>
}

function TimelinePoint({ label, active }: { label: string; active?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <span
        aria-hidden
        className="h-2 w-2 rounded-full"
        style={active ? { background: '#a89bfb', boxShadow: '0 0 6px rgba(168,155,251,0.6)' } : { background: '#5c6478' }}
      />
      <span className={`text-[11px] font-medium tracking-[0.08em] uppercase ${active ? 'text-foreground' : 'text-muted-foreground/60'}`}>{label}</span>
    </div>
  )
}

function TimelineLine({ long }: { long?: boolean }) {
  return <span aria-hidden className={`h-px ${long ? 'w-14 sm:w-24' : 'w-8 sm:w-12'} bg-white/10`} />
}
