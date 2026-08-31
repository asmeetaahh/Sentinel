import { useEffect, useRef, useState } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

interface Step {
  index: string
  eyebrow: string
  title: string
  description: string
}

const STEPS: Step[] = [
  {
    index: '01',
    eyebrow: 'Investigate',
    title: 'Understand what changed.',
    description: 'Identify the signals and drivers behind the emerging trajectory.',
  },
  {
    index: '02',
    eyebrow: 'Prepare',
    title: 'Build the case.',
    description: 'Gather the relevant dispute, transaction, fulfillment, and merchant evidence needed for readiness.',
  },
  {
    index: '03',
    eyebrow: 'Act',
    title: 'Respond with context.',
    description: 'Use the modeled trajectory and exposure view to inform bounded operational decisions.',
  },
]

const TRANSITION = 'opacity 0.55s cubic-bezier(0.4,0,0.2,1), transform 0.55s cubic-bezier(0.4,0,0.2,1)'

/**
 * "07 — Response": the last narrative beat before the site moves toward
 * product/value/credibility content. Answers "so what can I do with
 * this?" through a single sequential card the visitor advances through
 * (investigate → prepare → act) rather than three cards shown at once —
 * "moving through one response path," not comparing unrelated options.
 *
 * All three steps stay mounted, absolutely stacked in one fixed-height
 * frame, each positioned by its offset from `activeIndex` (0 = active,
 * ±1 = off to the side, faded and non-interactive) — a plain CSS
 * opacity+transform cross-fade, deliberately not a translating carousel
 * track: nothing here ever needs to "slide past" a card that isn't
 * adjacent, so there's no reason to build that mechanism.
 *
 * Reuses the same atmosphere as 04/06 (faint grid, sparse particles,
 * restrained glow) and the same non-scrubbed entrance-reveal pattern —
 * only the three-card block itself is new interaction, not a new visual
 * system. Replaces the old orbital Section 07 this project retired
 * (see App.tsx).
 */
export function ResponseSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const stepsRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const steps = stepsRef.current
    if (!section || !intro || !steps) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set([intro, steps], { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }

      gsap.set([intro, steps], { opacity: 0, y: 22, filter: 'blur(6px)' })

      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 82%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })
      timeline.to(intro, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0).to(steps, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.25)
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  const isFirst = activeIndex === 0
  const isLast = activeIndex === STEPS.length - 1
  const goNext = () => setActiveIndex((i) => Math.min(i + 1, STEPS.length - 1))
  const goPrev = () => setActiveIndex((i) => Math.max(i - 1, 0))

  return (
    <section ref={sectionRef} className="bg-background relative overflow-hidden px-6 py-24 sm:px-10 sm:py-28">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: 'radial-gradient(closest-side, rgba(124,108,246,0.08), rgba(124,108,246,0) 70%)' }}
      />
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(244,246,250,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(244,246,250,0.5) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />
      <svg
        aria-hidden
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.1]"
      >
        <path d="M -40,150 C 420,130 900,175 1480,140" fill="none" stroke="#8b7bf7" strokeWidth={1} />
        <path d="M -40,760 C 500,780 950,745 1480,772" fill="none" stroke="#8b7bf7" strokeWidth={1} />
      </svg>
      {[
        { left: '18%', top: '22%' },
        { left: '85%', top: '30%' },
        { left: '10%', top: '78%' },
        { left: '90%', top: '82%' },
      ].map((particle) => (
        <div
          key={particle.left}
          aria-hidden
          className="pointer-events-none absolute h-1 w-1 rounded-full bg-[#c9befb]"
          style={{
            left: particle.left,
            top: particle.top,
            opacity: 0.4,
            animation: reduceMotion ? 'none' : 'glow-breathe 5s ease-in-out infinite',
            filter: 'drop-shadow(0 0 3px rgba(201,190,251,0.6))',
          }}
        />
      ))}

      <div ref={introRef} className="relative mx-auto max-w-2xl text-center" style={{ opacity: 0 }}>
        <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Response</p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          Know what to do before the shock.
        </h2>
        <p className="mx-auto mt-6 max-w-lg text-base text-muted-foreground sm:text-lg">
          Sentinel turns an emerging risk trajectory into a clearer response path — so teams can investigate the
          drivers, prepare evidence, and act before the situation becomes a larger financial event.
        </p>
      </div>

      <div ref={stepsRef} className="relative mx-auto mt-16 max-w-lg sm:mt-20" style={{ opacity: 0 }}>
        <p className="text-center text-xs font-medium tracking-[0.16em] text-muted-foreground/70 tabular-nums">
          {STEPS[activeIndex].index} / {String(STEPS.length).padStart(2, '0')}
        </p>

        <div className="relative mt-4 min-h-[260px] sm:min-h-[220px]" aria-live="polite">
          {STEPS.map((step, index) => {
            const offset = index - activeIndex
            const isActive = offset === 0
            return (
              <div
                key={step.index}
                role={isActive && !isLast ? 'button' : undefined}
                tabIndex={isActive && !isLast ? 0 : -1}
                aria-label={isActive && !isLast ? `Step ${step.index}: ${step.eyebrow}. Activate to continue to the next step.` : undefined}
                aria-hidden={!isActive}
                onClick={isActive && !isLast ? goNext : undefined}
                onKeyDown={
                  isActive && !isLast
                    ? (event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          goNext()
                        }
                      }
                    : undefined
                }
                className={`rounded-2xl border border-white/[0.06] bg-white/[0.02] px-7 py-8 sm:px-9 sm:py-10 ${
                  isActive && !isLast ? 'cursor-pointer hover:border-white/[0.12] hover:bg-white/[0.035]' : ''
                }`}
                style={{
                  position: 'absolute',
                  inset: 0,
                  opacity: reduceMotion ? (isActive ? 1 : 0) : isActive ? 1 : 0,
                  transform: reduceMotion ? 'none' : `translateX(${isActive ? 0 : offset > 0 ? 28 : -28}px) scale(${isActive ? 1 : 0.97})`,
                  transition: reduceMotion ? 'opacity 0.2s linear' : TRANSITION,
                  pointerEvents: isActive ? 'auto' : 'none',
                }}
              >
                <p className="text-3xl font-semibold tracking-tight text-accent-soft/70 tabular-nums">{step.index}</p>
                <p className="mt-3 text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">{step.eyebrow}</p>
                <h3 className="mt-2 text-xl font-semibold tracking-tight text-balance sm:text-2xl">{step.title}</h3>
                <p className="mt-3 max-w-sm text-sm text-muted-foreground sm:text-base">{step.description}</p>

                {isActive && !isLast && (
                  <p className="mt-6 text-xs font-medium tracking-[0.1em] text-muted-foreground/60 uppercase">Click to continue →</p>
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={goPrev}
            disabled={isFirst}
            aria-label="Previous step"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.08] text-muted-foreground transition-colors duration-200 enabled:hover:border-white/20 enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-25"
          >
            ←
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={isLast}
            aria-label="Next step"
            className="flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.08] text-muted-foreground transition-colors duration-200 enabled:hover:border-white/20 enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-25"
          >
            →
          </button>
        </div>
      </div>
    </section>
  )
}
