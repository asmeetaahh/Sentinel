import { useEffect, useRef } from 'react'

import { ProductTrajectory } from '@/components/ProductTrajectory'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

const DRIVERS = ['Rising refund rate', 'Fulfillment delays', 'Shifting customer mix']

/** Same three stages ResponseSection walks the visitor through — echoed
 * here, small, inside the product panel itself, so the connection reads
 * as "this is the system that makes that workflow possible" without
 * saying so directly. All three share one accent color (no orange on
 * "Act"), matching the fix already made to ResponseSection. */
const RESPONSE_STAGES = ['Investigate', 'Prepare', 'Act']

/**
 * "08 — Sentinel / Product": the payoff. Everything from the Hero
 * onward has been narrative; this is the first section that shows an
 * actual product surface — a compact risk-intelligence panel, not
 * another abstract line/circle visual. Explicitly NOT a recreation of
 * Section 03's trajectory (see ProductTrajectory) and explicitly not the
 * old orbital Section 07 this project retired — no rings, no spokes, no
 * giant central mark, just a believable console: a merchant, a
 * trajectory, a few modeled numbers, key drivers, and a response-
 * readiness strip that echoes ResponseSection's own three stages.
 *
 * Compact by design (one section, no scroll-scrubbed epic) — the
 * richness is visual (the panel "coming into focus" on entry, values
 * illuminating in sequence), not scroll depth. Same non-scrubbed
 * entrance-reveal pattern as 05/06/07, same atmosphere primitives
 * (radial glow, faint grid, sparse particles).
 */
export function ProductSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const statRefs = useRef<(HTMLDivElement | null)[]>([])
  const stageRefs = useRef<(HTMLDivElement | null)[]>([])
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const panel = panelRef.current
    const stats = statRefs.current.filter((el): el is HTMLDivElement => el !== null)
    const stages = stageRefs.current.filter((el): el is HTMLDivElement => el !== null)
    if (!section || !intro || !panel) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set([intro, panel, ...stats, ...stages], { opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' })
        return
      }

      gsap.set(intro, { opacity: 0, y: 22, filter: 'blur(6px)' })
      gsap.set(panel, { opacity: 0, y: 26, scale: 0.97, filter: 'blur(10px)' })
      gsap.set(stats, { opacity: 0, y: 10 })
      gsap.set(stages, { opacity: 0, scale: 0.85 })

      // "The system is coming into focus": intro resolves first, then
      // the panel itself fades/sharpens/settles into place, then the
      // supporting numbers and the response-readiness dots illuminate
      // in sequence — never all at once.
      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 80%', toggleActions: 'play none none reverse' },
        defaults: { ease: 'power2.out' },
      })
      timeline
        .to(intro, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9 }, 0)
        .to(panel, { opacity: 1, y: 0, scale: 1, filter: 'blur(0px)', duration: 1.1 }, 0.35)
        .to(stats, { opacity: 1, y: 0, duration: 0.6, stagger: 0.1 }, 0.85)
        .to(stages, { opacity: 1, scale: 1, duration: 0.5, stagger: 0.12 }, 1.05)
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  return (
    <section ref={sectionRef} className="bg-background relative overflow-hidden px-6 py-24 sm:px-10 sm:py-28">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: 'radial-gradient(closest-side, rgba(124,108,246,0.09), rgba(124,108,246,0) 70%)' }}
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
      {[
        { left: '12%', top: '18%' },
        { left: '92%', top: '24%' },
        { left: '6%', top: '85%' },
      ].map((particle) => (
        <div
          key={particle.left}
          aria-hidden
          className="pointer-events-none absolute h-1 w-1 rounded-full bg-[#c9befb]"
          style={{
            left: particle.left,
            top: particle.top,
            opacity: 0.35,
            animation: reduceMotion ? 'none' : 'glow-breathe 6s ease-in-out infinite',
            filter: 'drop-shadow(0 0 3px rgba(201,190,251,0.6))',
          }}
        />
      ))}

      <div ref={introRef} className="relative mx-auto max-w-2xl text-center" style={{ opacity: 0 }}>
        <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Sentinel</p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          See the risk before it becomes the shock.
        </h2>
        <p className="mx-auto mt-6 max-w-lg text-base text-muted-foreground sm:text-lg">
          Sentinel connects merchant-level signals, explains emerging risk, models where the trajectory could lead,
          and helps teams decide what to do next.
        </p>
      </div>

      {/* The product panel — a believable console, not a decoration:
          merchant + risk status, the trajectory, a few modeled numbers,
          key drivers, and a response-readiness strip. */}
      <div ref={panelRef} className="relative mx-auto mt-14 max-w-4xl sm:mt-16" style={{ opacity: 0 }}>
        <div className="rounded-3xl border border-white/[0.08] bg-white/[0.025] px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] pb-5">
            <div>
              <p className="text-[10px] font-medium tracking-[0.16em] text-muted-foreground uppercase">Merchant</p>
              <p className="mt-1 text-sm font-medium">Demo Merchant · MER-2291</p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] px-3 py-1.5 text-xs font-medium text-accent-soft">
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-[#a89bfb]" style={{ boxShadow: '0 0 6px rgba(168,155,251,0.7)' }} />
              Emerging risk
            </span>
          </div>

          <div className="mt-6 grid gap-8 lg:grid-cols-[1.3fr_1fr] lg:gap-10">
            <div>
              <p className="text-[10px] font-medium tracking-[0.16em] text-muted-foreground uppercase">Risk trajectory</p>
              <div className="mt-3 aspect-[600/300] w-full">
                <ProductTrajectory />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-1 lg:gap-5">
              <div ref={(el) => { statRefs.current[0] = el }} className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5">
                <p className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Modeled probability (30d)</p>
                <p className="mt-1.5 text-xl font-semibold tracking-tight tabular-nums">27%</p>
              </div>
              <div ref={(el) => { statRefs.current[1] = el }} className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5">
                <p className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Estimated exposure (relative)</p>
                <p className="mt-1.5 text-xl font-semibold tracking-tight tabular-nums">71%</p>
              </div>
              <div ref={(el) => { statRefs.current[2] = el }} className="col-span-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5 lg:col-span-1">
                <p className="text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">Key drivers</p>
                <ul className="mt-2 space-y-1.5">
                  {DRIVERS.map((driver) => (
                    <li key={driver} className="flex items-center gap-2 text-sm text-foreground/90">
                      <span aria-hidden className="h-1 w-1 shrink-0 rounded-full bg-[#a89bfb]" />
                      {driver}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-6 border-t border-white/[0.06] pt-5">
            <p className="text-[10px] font-medium tracking-[0.16em] text-muted-foreground uppercase">Response readiness</p>
            <div className="mt-3 flex items-center gap-3">
              {RESPONSE_STAGES.map((stage, index) => (
                <div key={stage} className="flex items-center gap-3">
                  <div ref={(el) => { stageRefs.current[index] = el }} className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className="h-2 w-2 rounded-full"
                      style={{
                        background: index === 0 ? '#a89bfb' : '#5c6478',
                        boxShadow: index === 0 ? '0 0 7px rgba(168,155,251,0.8)' : 'none',
                        animation: index === 0 && !reduceMotion ? 'glow-breathe 3.5s ease-in-out infinite' : 'none',
                      }}
                    />
                    <span className={`text-xs font-medium ${index === 0 ? 'text-foreground' : 'text-muted-foreground/60'}`}>{stage}</span>
                  </div>
                  {index < RESPONSE_STAGES.length - 1 && <span aria-hidden className="h-px w-6 bg-white/10" />}
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground/50">Illustrative product view — modeled values, not guaranteed outcomes.</p>
      </div>
    </section>
  )
}
