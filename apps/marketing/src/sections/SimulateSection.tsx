import { useEffect, useRef, useState } from 'react'

import { SimulationTrajectory } from '@/components/SimulationTrajectory'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

/**
 * The three real, bounded controls the product's own counterfactual
 * simulator exposes (see backend/simulation/controls.py) — same labels,
 * same trailing-28-day framing. Only the two most legible-as-a-lever
 * controls are surfaced here (refund rate, on-time fulfillment); ranges
 * and defaults below are representative bounds for this narrative demo,
 * not a live merchant's actual data, since this is the marketing site,
 * not the product itself.
 */
const REFUND_RANGE = { min: 1.5, max: 9, baseline: 6.5, best: 1.5 }
const FULFILLMENT_RANGE = { min: 78, max: 97, baseline: 84, best: 97 }

// Illustrative, clearly-bounded readout numbers — framed throughout as a
// "modeled" scenario output, never as a performance claim about Sentinel
// itself (see the disclaimer at the bottom of the panel).
const BASELINE_PROBABILITY = 34
const BEST_PROBABILITY = 11
const BASELINE_EXPOSURE = 100
const BEST_EXPOSURE = 58

export function SimulateSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  const [refundRate, setRefundRate] = useState(REFUND_RANGE.baseline)
  const [fulfillmentRate, setFulfillmentRate] = useState(FULFILLMENT_RANGE.baseline)

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const panel = panelRef.current
    if (!section || !intro || !panel) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set([intro, panel], { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }

      gsap.set([intro, panel], { opacity: 0, y: 22, filter: 'blur(6px)' })

      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 82%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })
      timeline.to(intro, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0).to(panel, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.25)
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  const refundT = clamp01((REFUND_RANGE.baseline - refundRate) / (REFUND_RANGE.baseline - REFUND_RANGE.best))
  const fulfillmentT = clamp01((fulfillmentRate - FULFILLMENT_RANGE.baseline) / (FULFILLMENT_RANGE.best - FULFILLMENT_RANGE.baseline))
  const interventionT = clamp01((refundT + fulfillmentT) / 2)

  const simulatedProbability = Math.round(BASELINE_PROBABILITY - (BASELINE_PROBABILITY - BEST_PROBABILITY) * interventionT)
  const simulatedExposure = Math.round(BASELINE_EXPOSURE - (BASELINE_EXPOSURE - BEST_EXPOSURE) * interventionT)

  return (
    <section ref={sectionRef} className="bg-background relative overflow-hidden px-6 py-28 sm:px-10 sm:py-36">
      {/* Same atmosphere language as 02/04 — radial glow, faint grid —
          kept restrained since the graph itself is the visual focus here. */}
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

      <div ref={introRef} className="relative mx-auto max-w-2xl text-center" style={{ opacity: 0 }}>
        <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Simulate</p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          What changes if you act before the shock?
        </h2>
        <p className="mx-auto mt-6 max-w-lg text-base text-muted-foreground sm:text-lg">
          Sentinel lets a merchant test bounded, real operational changes against the emerging trajectory —
          before the financial impact arrives, not after.
        </p>
      </div>

      <div ref={panelRef} className="relative mx-auto mt-16 max-w-5xl sm:mt-20" style={{ opacity: 0 }}>
        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <span aria-hidden className="h-[2px] w-5 rounded-full" style={{ background: '#6b7086', opacity: 0.8 }} />
            Baseline — if nothing changes
          </span>
          <span className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className="h-[3.5px] w-5 rounded-full"
              style={{ background: 'linear-gradient(to right, #c9befb, #8b7bf7)', boxShadow: '0 0 6px rgba(168,155,251,0.5)' }}
            />
            Simulated — with this scenario
          </span>
        </div>

        <div className="mt-6 aspect-[12/7] w-full">
          <SimulationTrajectory interventionT={interventionT} />
        </div>

        <div className="mx-auto mt-10 grid max-w-3xl gap-8 sm:grid-cols-2">
          <label className="block">
            <span className="flex items-baseline justify-between text-sm">
              <span className="font-medium">Refund rate</span>
              <span className="text-muted-foreground tabular-nums">{refundRate.toFixed(1)}%</span>
            </span>
            <span className="mt-1 block text-xs text-muted-foreground/70">Trailing 28 days</span>
            <input
              type="range"
              min={REFUND_RANGE.min}
              max={REFUND_RANGE.max}
              step={0.1}
              value={refundRate}
              onChange={(event) => setRefundRate(Number(event.target.value))}
              aria-label="Refund rate, trailing 28 days"
              aria-valuetext={`${refundRate.toFixed(1)} percent`}
              className="sentinel-range mt-3 w-full"
            />
          </label>

          <label className="block">
            <span className="flex items-baseline justify-between text-sm">
              <span className="font-medium">On-time fulfillment rate</span>
              <span className="text-muted-foreground tabular-nums">{fulfillmentRate.toFixed(0)}%</span>
            </span>
            <span className="mt-1 block text-xs text-muted-foreground/70">Trailing 28 days</span>
            <input
              type="range"
              min={FULFILLMENT_RANGE.min}
              max={FULFILLMENT_RANGE.max}
              step={1}
              value={fulfillmentRate}
              onChange={(event) => setFulfillmentRate(Number(event.target.value))}
              aria-label="On-time fulfillment rate, trailing 28 days"
              aria-valuetext={`${fulfillmentRate.toFixed(0)} percent`}
              className="sentinel-range mt-3 w-full"
            />
          </label>
        </div>

        <div className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] px-6 py-5 text-center">
            <p className="text-xs font-medium tracking-[0.16em] text-muted-foreground uppercase">Modeled probability (30d)</p>
            <p className="mt-3 text-2xl font-semibold tracking-tight tabular-nums">
              <span className="text-muted-foreground/70 line-through decoration-1">{BASELINE_PROBABILITY}%</span>{' '}
              <span className="bg-gradient-to-r from-accent to-accent-soft bg-clip-text text-transparent">{simulatedProbability}%</span>
            </p>
          </div>
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] px-6 py-5 text-center">
            <p className="text-xs font-medium tracking-[0.16em] text-muted-foreground uppercase">Estimated exposure (relative)</p>
            <p className="mt-3 text-2xl font-semibold tracking-tight tabular-nums">
              <span className="text-muted-foreground/70 line-through decoration-1">{BASELINE_EXPOSURE}%</span>{' '}
              <span className="bg-gradient-to-r from-accent to-accent-soft bg-clip-text text-transparent">{simulatedExposure}%</span>
            </p>
          </div>
        </div>

        <p className="mx-auto mt-8 max-w-xl text-center text-xs text-muted-foreground/60">
          A modeled impact, not a guaranteed or causal outcome — this shows how the trajectory responds when these
          bounded operational metrics are set to a different value, holding everything else fixed.
        </p>
      </div>
    </section>
  )
}
