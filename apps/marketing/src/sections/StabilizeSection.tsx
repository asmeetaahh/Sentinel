import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

interface FlowNode {
  label: string
  accent?: boolean
}

/**
 * Real terminology, not invented: "exposure" and "liquidity stress" are
 * the actual output fields the simulator returns (see
 * backend/api/schemas/simulation.py — SimulationExposureSection,
 * SimulationLiquidityStressSection). "Merchant stability" is the
 * narrative outcome the other two lead to, not a metric name.
 */
const FLOW: FlowNode[] = [{ label: 'Risk exposure' }, { label: 'Liquidity stress', accent: true }, { label: 'Merchant stability' }]

/**
 * "06 — Stabilize": the bridge between Simulate ("what if you act now?")
 * and Response ("what can you do?"). Deliberately calmer and much more
 * compact than 03 or 05 — no scroll-scrubbed graph, no interactive
 * controls, just a short entrance reveal (same non-scrubbed timeline
 * pattern as every other section's text) over a minimal three-node
 * "exposure → liquidity stress → stability" connector, reusing the
 * established atmosphere (radial glow, faint grid) rather than
 * introducing a new visual system.
 */
export function StabilizeSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const introRef = useRef<HTMLDivElement>(null)
  const flowRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const intro = introRef.current
    const flow = flowRef.current
    if (!section || !intro || !flow) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set([intro, flow], { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }

      gsap.set([intro, flow], { opacity: 0, y: 22, filter: 'blur(6px)' })

      const timeline = gsap.timeline({
        scrollTrigger: { trigger: intro, start: 'top 82%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })
      timeline.to(intro, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0).to(flow, { opacity: 1, y: 0, filter: 'blur(0px)' }, 0.25)
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

      <div ref={introRef} className="relative mx-auto max-w-2xl text-center" style={{ opacity: 0 }}>
        <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Stabilize</p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          See the exposure before it becomes a shock.
        </h2>
        <p className="mx-auto mt-6 max-w-lg text-base text-muted-foreground sm:text-lg">
          An emerging trajectory becomes a clearer picture of potential exposure — where liquidity stress could
          build, and how much room there is to respond before it compounds.
        </p>
      </div>

      <div ref={flowRef} className="relative mx-auto mt-16 flex h-[320px] max-w-xs flex-col items-center justify-between sm:mt-20" style={{ opacity: 0 }}>
        <div aria-hidden className="pointer-events-none absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-white/15 to-transparent">
          {!reduceMotion && (
            <div
              aria-hidden
              className="absolute left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full"
              style={{
                background: '#f0a35f',
                animation: 'flow-descend 4s ease-in-out infinite',
                filter: 'drop-shadow(0 0 5px rgba(240,163,95,0.7))',
              }}
            />
          )}
        </div>

        {FLOW.map((node) => (
          <div key={node.label} className="relative flex flex-col items-center gap-3">
            <span
              aria-hidden
              className="h-2.5 w-2.5 rounded-full"
              style={{
                background: node.accent ? '#f0a35f' : '#a89bfb',
                boxShadow: node.accent ? '0 0 8px rgba(240,163,95,0.6)' : '0 0 8px rgba(168,155,251,0.5)',
              }}
            />
            <p className={`text-sm font-medium tracking-wide ${node.accent ? 'text-[#f2b988]' : 'text-foreground'}`}>{node.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
