import { useEffect, useRef } from 'react'

import { RiskTrajectory } from '@/components/RiskTrajectory'
import { useIsMobile } from '@/hooks/useIsMobile'
import { useIsTablet } from '@/hooks/useIsTablet'
import { useParallax } from '@/hooks/useParallax'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap, ScrollTrigger } from '@/lib/gsap'

/**
 * "03 — Trajectory": growth curving into a chargeback spike, then the
 * hold/freeze/cash-crunch drop — "risk discovered too late." Mirrors the
 * text-left/visual-right layout used by Money Moves and Sentinel.
 *
 * Unlike every other section built so far, this one is TALLER than one
 * viewport (`h-[220dvh]`), with its visible content pinned via
 * `position: sticky` rather than `position: fixed` or any scroll-jack —
 * pure CSS, native wheel/trackpad scrolling behaves exactly as normal,
 * but the extra scroll distance gives the trajectory's stroke-reveal
 * (see RiskTrajectory) room to unfold slowly instead of completing
 * within a single viewport-height of scroll. Once the outer section's
 * full height has scrolled past, normal document flow continues into
 * whatever comes next — nothing about this traps or alters scrolling
 * for the rest of the page.
 */
export function TrajectorySection() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const eyebrowRef = useRef<HTMLParagraphElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const supportRef = useRef<HTMLParagraphElement>(null)
  const graphRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const isTablet = useIsTablet()
  const parallaxRef = useParallax({ disabled: reduceMotion || isMobile })

  useEffect(() => {
    const section = sectionRef.current
    const content = contentRef.current
    const graph = graphRef.current
    const pieces = [eyebrowRef.current, headlineRef.current, supportRef.current]
    if (!section || !content || !graph || pieces.some((piece) => !piece)) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(pieces, { opacity: 1, y: 0, filter: 'blur(0px)' })
        graph.style.setProperty('--reveal', '1')
        return
      }

      gsap.set(pieces, { opacity: 0, y: 22, filter: 'blur(6px)' })
      graph.style.setProperty('--reveal', '0')

      // Written directly via `onUpdate` rather than as a GSAP tween
      // target — see ExplainSection for why: GSAP's own CSS-custom-
      // property interpolation didn't reliably advance a variable set
      // this way, so every scroll-driven variable in this codebase is
      // written straight from the ScrollTrigger's own scrub progress.
      ScrollTrigger.create({
        trigger: section,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
        onUpdate: (self) => graph.style.setProperty('--reveal', String(self.progress)),
      })

      // Sequential reveal — eyebrow, then headline, then supporting line
      // — same pattern as every other section.
      const timeline = gsap.timeline({
        scrollTrigger: { trigger: content, start: 'top 85%', toggleActions: 'play none none reverse' },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })
      const delays = [0, 0.18, 0.38]
      pieces.forEach((piece, index) => {
        timeline.to(piece, { opacity: 1, y: 0, filter: 'blur(0px)' }, delays[index])
      })
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  return (
    <section ref={sectionRef} className="relative h-[220dvh]">
      <div className="bg-background sticky top-0 flex h-dvh items-center overflow-hidden px-6 sm:px-10">
        <div
          aria-hidden
          className="absolute"
          style={{
            left: '66%',
            top: '50%',
            width: 900,
            height: 700,
            transform: 'translate(-50%, -50%)',
            background: 'radial-gradient(closest-side, rgba(124,108,246,0.1), rgba(124,108,246,0) 70%)',
          }}
        />

        <div ref={parallaxRef} className="absolute inset-0">
          <div
            ref={graphRef}
            className="absolute"
            style={
              isMobile
                ? { left: '50%', top: '64%', width: '94%', height: '42%', transform: 'translate(-50%, -50%)' }
                : {
                    left: isTablet ? '74%' : '62%',
                    top: '50%',
                    width: isTablet ? '46%' : '62%',
                    height: isTablet ? '52%' : '68%',
                    transform: `translate3d(calc(-50% + var(--parallax-x, 0) * 10px), calc(-50% + var(--parallax-y, 0) * 10px), 0)`,
                  }
            }
          >
            <RiskTrajectory />
          </div>
        </div>

        <div ref={contentRef} className="relative max-w-md lg:max-w-lg">
          <p ref={eyebrowRef} className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
            Trajectory
          </p>
          <h2 ref={headlineRef} className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
            Risk is discovered too late.
          </h2>
          <p ref={supportRef} className="mt-6 max-w-sm text-base text-muted-foreground sm:text-lg">
            By the time chargeback risk shows up, the money is already on hold, limits are hit, and growth is stalled.
          </p>
        </div>
      </div>
    </section>
  )
}
