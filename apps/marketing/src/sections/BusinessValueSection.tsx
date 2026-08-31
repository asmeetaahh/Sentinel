import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

interface ExternalBenchmark {
  display: string
  countTo?: number
  decimals?: number
  prefix?: string
  suffix?: string
  label: string
  detail: string
  source: string
}

/**
 * Real, sourced industry figures — not Sentinel measurements. See the
 * section-level doc comment below for why each number is used and where
 * it comes from.
 */
const EXTERNAL_BENCHMARKS: ExternalBenchmark[] = [
  {
    display: '$128',
    countTo: 128,
    prefix: '$',
    label: 'Average merchant chargeback cost',
    detail: '$82 internal + $46 third-party',
    source: 'Mastercard / Javelin benchmark',
  },
  {
    display: '₹4',
    countTo: 4,
    prefix: '₹',
    label: 'Total cost per ₹1 of fraud loss',
    detail: 'for Indian businesses',
    source: 'Razorpay, citing LexisNexis',
  },
  {
    display: '$9–10',
    label: 'Cost to process one dispute',
    detail: 'for a U.S. financial institution',
    source: 'Mastercard / Datos Insights',
  },
]

interface SyntheticStat {
  display: string
  countTo?: number
  decimals?: number
  suffix?: string
  label: string
  detail: string
}

/**
 * Real numbers computed from this project's own synthetic benchmark —
 * see the doc comment below for exact sources. Not external, not
 * invented.
 */
const SYNTHETIC_STATS: SyntheticStat[] = [
  {
    display: '50 × 180',
    label: 'Benchmark scale',
    detail: 'merchants × days, synthetic dataset',
  },
  {
    display: '7',
    countTo: 7,
    suffix: ' days',
    label: 'Median early-warning lead time',
    detail: 'at a 30-day risk horizon — the project’s signature validated result',
  },
  {
    display: '1.47×',
    label: 'Chargeback intensity in a risk window',
    detail: 'vs. 1.08× in ordinary benign growth',
  },
]

interface ValuePanel {
  eyebrow: string
  points: string[]
}

const PANELS: ValuePanel[] = [
  {
    eyebrow: 'Merchant',
    points: [
      'Investigate drivers before disputes accumulate',
      'Prepare evidence while there’s still time',
      'Apply bounded operational changes before exposure compounds',
      'Fewer surprises in settlement and reserve holds',
    ],
  },
  {
    eyebrow: 'PSP / Platform',
    points: [
      'Prioritize investigation across a portfolio, not just the loudest signals',
      'Lower per-case investigation cost by surfacing risk earlier',
      'Fewer unexpected liquidity and exposure shocks across the portfolio',
      'Earlier context for risk teams, instead of reactive case review',
    ],
  },
]

/** Ties a plain object's tweened value straight into a DOM node's text —
 * the same "write scroll/entrance-driven state directly" convention this
 * codebase already uses for CSS custom properties, applied here to a
 * one-time count-up instead. Reduced-motion callers should just set
 * final text directly and never call this. */
function countUp(el: HTMLElement | null, target: number, format: (n: number) => string) {
  if (!el) return
  const obj = { v: 0 }
  gsap.to(obj, { v: target, duration: 1.1, ease: 'power2.out', onUpdate: () => { el.textContent = format(obj.v) } })
}

/**
 * "08 — Business Value": the economic payoff of the story so far —
 * "why is acting earlier worth money?" Structured as five beats: the
 * cost of waiting (real external benchmarks), what this project's own
 * synthetic benchmark actually shows, one transparent illustrative
 * scenario built from a real rate + a stated assumption, then what that
 * means for a merchant vs. a PSP/platform.
 *
 * Every number here falls into exactly one of three categories, each
 * with a visibly different treatment so the distinction is never
 * ambiguous:
 *   1. EXTERNAL BENCHMARKS (ivory, plain — not "model output" purple):
 *      $128 = Mastercard/Javelin's $82 internal + $46 third-party
 *      average chargeback cost; ₹4 = Razorpay citing LexisNexis on
 *      total cost per ₹1 of fraud loss; $9–10 = Mastercard/Datos
 *      Insights' dispute-processing cost. These are industry figures,
 *      not anything Sentinel measured.
 *   2. SENTINEL SYNTHETIC BENCHMARK (accent-soft purple, solid-bordered
 *      panel, labeled "SYNTHETIC BENCHMARK"): "50 × 180" is the actual
 *      benchmark scale (PROJECT_CONTEXT.md / RESEARCH.md); "7 days" is
 *      the median early-warning lead time at the 30-day horizon —
 *      RESEARCH.md calls this "the project's signature metric," the
 *      one rigorously re-validated after a measurement bug was found
 *      and fixed; "1.47× vs 1.08×" is the risk-window vs. benign-growth
 *      chargeback-intensity ratio from dataset_validation_report.md.
 *      All three are read directly from the repo's own research
 *      documentation, not invented for this page.
 *   3. ILLUSTRATIVE SCENARIO (dashed border, explicitly labeled "not a
 *      benchmark result"): the benchmark's own amount-weighted
 *      chargeback-to-GMV rate (≈0.9%, computed directly from
 *      data/raw/daily_observations.csv: 2,099,605 / 228,959,186) is
 *      real; the ₹50 Cr annual volume it's applied to is a stated
 *      assumption, since the synthetic dataset's GMV is deliberately
 *      unitless (docs/architecture/data_generation.md) and has no real
 *      currency peg. The ₹46L figure is therefore a transparent
 *      illustrative calculation (rate × assumed volume), never
 *      presented as something the benchmark itself produced — and
 *      deliberately NOT a "loss avoided" claim, since this project has
 *      no validated causal estimate of how much exposure a real
 *      intervention would actually prevent.
 *
 * Visual structure otherwise stays restrained on purpose — no new
 * diagram, no line/circle visual, reusing the same atmosphere and card
 * idiom as 06/07. Compact by design: one non-scrubbed entrance
 * timeline, count-up applied only to the handful of clean single-value
 * numbers ($128, ₹4, 7 days, ₹46L), everything else a plain fade.
 */
export function BusinessValueSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const costRowRef = useRef<HTMLDivElement>(null)
  const syntheticPanelRef = useRef<HTMLDivElement>(null)
  const illustrativeRef = useRef<HTMLDivElement>(null)
  const panelRefs = useRef<(HTMLDivElement | null)[]>([])
  const closingRef = useRef<HTMLParagraphElement>(null)
  const countRefs = useRef<Record<string, HTMLSpanElement | null>>({})
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const costRow = costRowRef.current
    const syntheticPanel = syntheticPanelRef.current
    const illustrative = illustrativeRef.current
    const panels = panelRefs.current.filter((el): el is HTMLDivElement => el !== null)
    const closing = closingRef.current
    if (!section || !intro || !costRow || !syntheticPanel || !illustrative || !closing || panels.length === 0) return

    const beats = [intro, costRow, syntheticPanel, illustrative, ...panels, closing]

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(beats, { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }

      gsap.set(beats, { opacity: 0, y: 22, filter: 'blur(6px)' })

      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 80%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.85, ease: 'power2.out' },
      })
      timeline
        .to(intro, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0)
        .to(costRow, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.25)
        .call(() => {
          countUp(countRefs.current.cost0, EXTERNAL_BENCHMARKS[0].countTo!, (n) => `$${Math.round(n)}`)
          countUp(countRefs.current.cost1, EXTERNAL_BENCHMARKS[1].countTo!, (n) => `₹${Math.round(n)}`)
        }, [], 0.35)
        .to(syntheticPanel, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.55)
        .call(() => countUp(countRefs.current.lead, SYNTHETIC_STATS[1].countTo!, (n) => `${Math.round(n)} days`), [], 0.65)
        .to(illustrative, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.85)
        .call(() => countUp(countRefs.current.illustrative, 46, (n) => `₹${Math.round(n)}L`), [], 0.95)
        .to(panels, { opacity: 1, y: 0, filter: 'blur(0px)', stagger: 0.15 }, 1.05)
        .to(closing, { opacity: 1, y: 0, filter: 'blur(0px)' }, 1.4)
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

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

      <div className="relative mx-auto max-w-3xl">
        {/* Intro */}
        <div ref={introRef} className="text-center" style={{ opacity: 0 }}>
          <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Business value</p>
          <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
            Earlier intelligence leaves more room to act.
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-base text-muted-foreground sm:text-lg">
            Risk becomes expensive when discovered late.
          </p>
        </div>

        {/* The cost of waiting — external, sourced benchmarks */}
        <div ref={costRowRef} className="mt-16 sm:mt-20" style={{ opacity: 0 }}>
          <p className="text-center text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase">The cost of waiting</p>
          <div className="mt-6 grid gap-4 sm:grid-cols-3 sm:gap-5">
            {EXTERNAL_BENCHMARKS.map((benchmark, index) => (
              <div key={benchmark.label} className="rounded-2xl border border-white/[0.06] bg-white/[0.015] px-5 py-6 text-center">
                <p className="text-3xl font-semibold tracking-tight tabular-nums sm:text-4xl">
                  {benchmark.countTo !== undefined ? (
                    <span
                      ref={(el) => {
                        countRefs.current[`cost${index}`] = el
                      }}
                    >
                      {reduceMotion ? benchmark.display : `${benchmark.prefix}0`}
                    </span>
                  ) : (
                    benchmark.display
                  )}
                </p>
                <p className="mt-2 text-sm font-medium text-foreground/90">{benchmark.label}</p>
                <p className="mt-1 text-xs text-muted-foreground">{benchmark.detail}</p>
                <p className="mt-3 text-[10px] tracking-[0.06em] text-muted-foreground/50 uppercase">{benchmark.source}</p>
              </div>
            ))}
          </div>
        </div>

        {/* What earlier action changes — Sentinel's own synthetic benchmark */}
        <div ref={syntheticPanelRef} className="mt-14 sm:mt-16" style={{ opacity: 0 }}>
          <p className="text-center text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase">What earlier detection changes</p>
          <div className="mt-6 rounded-3xl border border-white/[0.09] bg-white/[0.025] px-6 py-7 sm:px-8 sm:py-8">
            <span className="inline-flex items-center gap-2 rounded-full border border-accent-soft/25 px-3 py-1 text-[10px] font-medium tracking-[0.12em] text-accent-soft uppercase">
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-accent-soft" />
              Synthetic benchmark · Sentinel research dataset
            </span>
            <div className="mt-6 grid gap-6 sm:grid-cols-3">
              {SYNTHETIC_STATS.map((stat) => (
                <div key={stat.label}>
                  <p className="text-2xl font-semibold tracking-tight text-accent-soft tabular-nums sm:text-3xl">
                    {stat.countTo !== undefined ? (
                      <span
                        ref={(el) => {
                          countRefs.current.lead = el
                        }}
                      >
                        {reduceMotion ? `${stat.display}${stat.suffix ?? ''}` : '0 days'}
                      </span>
                    ) : (
                      stat.display
                    )}
                  </p>
                  <p className="mt-1.5 text-sm font-medium text-foreground/90">{stat.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{stat.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Illustrative scenario — real rate, stated assumption, transparent math */}
        <div ref={illustrativeRef} className="mt-6" style={{ opacity: 0 }}>
          <div className="rounded-2xl border border-dashed border-white/[0.14] bg-white/[0.012] px-6 py-6 sm:px-8 sm:py-7">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-[10px] font-medium tracking-[0.12em] text-muted-foreground uppercase">
              Illustrative scenario · not a benchmark result
            </span>
            <div className="mt-5 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-md text-sm text-muted-foreground sm:text-base">
                At the benchmark&apos;s own <span className="text-foreground">≈0.9%</span> chargeback-to-volume rate, a merchant
                assumed to process <span className="text-foreground">₹50 Cr a year</span> — an illustrative assumption, not a
                measured figure — carries roughly:
              </p>
              <p className="text-4xl font-semibold tracking-tight tabular-nums sm:text-5xl" style={{ color: '#f2b988' }}>
                <span
                  ref={(el) => {
                    countRefs.current.illustrative = el
                  }}
                >
                  {reduceMotion ? '₹46L' : '₹0L'}
                </span>
              </p>
            </div>
            <p className="mt-4 text-xs text-muted-foreground/70">
              Modeled annual chargeback exposure — not a loss-avoided claim. The 7-day lead time above is the room to act
              before that trends toward the 1.47× risk-window level.
            </p>
          </div>
        </div>

        {/* At scale — merchant vs. PSP */}
        <div className="mt-14 sm:mt-16">
          <p className="text-center text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase">At scale</p>
          <div className="mt-6 grid gap-5 md:grid-cols-2 md:gap-6">
            {PANELS.map((panel, index) => (
              <div
                key={panel.eyebrow}
                ref={(el) => {
                  panelRefs.current[index] = el
                }}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.02] px-7 py-8 transition-colors duration-300 hover:border-white/[0.14] hover:bg-white/[0.035] sm:px-8 sm:py-9"
                style={{ opacity: 0 }}
              >
                <p className="text-xs font-medium tracking-[0.16em] text-accent-soft uppercase">{panel.eyebrow}</p>
                <ul className="mt-5 space-y-4">
                  {panel.points.map((point) => (
                    <li key={point} className="flex items-start gap-3 text-sm text-foreground/90 sm:text-base">
                      <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#a89bfb]" style={{ boxShadow: '0 0 6px rgba(168,155,251,0.5)' }} />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="mx-auto mt-6 max-w-lg text-center text-sm text-muted-foreground">
            At payment-platform scale, even small reductions in unexpected exposure or operational burden become
            economically meaningful.
          </p>
        </div>

        <p ref={closingRef} className="mt-12 text-center text-xl font-medium tracking-tight text-balance sm:text-2xl" style={{ opacity: 0 }}>
          More decision time. Less unexpected shock.
        </p>

        <p className="mx-auto mt-8 max-w-xl text-center text-xs text-muted-foreground/45">
          External benchmarks are third-party industry figures, not Sentinel measurements. Synthetic-benchmark figures
          come from this project&apos;s own 50-merchant research dataset, not live merchant or Razorpay data.
        </p>
      </div>
    </section>
  )
}
