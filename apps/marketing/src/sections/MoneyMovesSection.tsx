import { useEffect, useRef } from 'react'

import { MoneyFlowField } from '@/components/MoneyFlowField'
import { useIsMobile } from '@/hooks/useIsMobile'
import { useParallax } from '@/hooks/useParallax'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

/**
 * "01 — Money Moves," the first narrative beat after the hero. Mirrors
 * the hero's own layout (text left, visual right/full-bleed) rather than
 * SignalEmergence's centered treatment — this is meant to read as the
 * hero's world continuing forward, not a new page.
 *
 * The section's own background fades from transparent at its very top
 * edge to fully opaque by ~34% down. While that edge is still
 * transparent, the hero's fixed background canvas shows through right at
 * the seam as the user scrolls past the boundary — a soft crossfade
 * between "the hero" and "this scene" without needing to blend the two
 * visuals' actual DOM content together. The flow field's own opacity
 * ramps in over roughly the same scroll span, so the paths visibly
 * arrive rather than popping in once the background clears.
 *
 * Uses `h-dvh`, not `h-screen` (100vh) — see Hero.tsx for why: every
 * full-viewport section shares this unit so GSAP ScrollTrigger's cached
 * per-section boundaries stay accurate even as a mobile browser's
 * address bar shows/hides mid-scroll.
 */
export function MoneyMovesSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const eyebrowRef = useRef<HTMLParagraphElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const supportRef = useRef<HTMLParagraphElement>(null)
  const fieldRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const parallaxRef = useParallax({ disabled: reduceMotion || isMobile })

  useEffect(() => {
    const section = sectionRef.current
    const content = contentRef.current
    const field = fieldRef.current
    const pieces = [eyebrowRef.current, headlineRef.current, supportRef.current]
    if (!section || !content || !field || pieces.some((piece) => !piece)) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(pieces, { opacity: 1, y: 0, filter: 'blur(0px)' })
        gsap.set(field, { opacity: 1 })
        return
      }

      gsap.set(pieces, { opacity: 0, y: 22, filter: 'blur(6px)' })
      gsap.set(field, { opacity: 0 })

      gsap.to(field, {
        opacity: 1,
        ease: 'none',
        scrollTrigger: { trigger: section, start: 'top bottom', end: 'top 55%', scrub: true },
      })

      // Sequential reveal — eyebrow, then headline, then supporting line
      // — triggered off the text block itself (not the section) so it
      // fires as the copy actually enters view rather than while it's
      // still far below the fold. Same pattern as SignalEmergence.
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
    <section
      ref={sectionRef}
      className="relative flex h-dvh items-center overflow-hidden px-6 sm:px-10"
      style={{ background: 'linear-gradient(to bottom, transparent, transparent 4%, var(--color-background) 34%)' }}
    >
      <div
        aria-hidden
        className="absolute"
        style={{
          left: '64%',
          top: '50%',
          width: 900,
          height: 650,
          transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(closest-side, rgba(124,108,246,0.12), rgba(124,108,246,0) 70%)',
        }}
      />
      <div
        aria-hidden
        className="absolute hidden opacity-[0.035] sm:block"
        style={{
          left: '60%',
          top: '50%',
          width: 1100,
          height: 800,
          transform: 'translate(-50%, -50%)',
          backgroundImage:
            'linear-gradient(to right, rgba(196,188,255,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(196,188,255,0.5) 1px, transparent 1px)',
          backgroundSize: '56px 56px',
          maskImage: 'radial-gradient(closest-side, black, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(closest-side, black, transparent 75%)',
        }}
      />

      <div ref={parallaxRef} className="absolute inset-0">
        <div ref={fieldRef} className="absolute inset-0">
          <MoneyFlowField />
        </div>
      </div>

      <div ref={contentRef} className="relative max-w-md lg:max-w-lg">
        <p ref={eyebrowRef} className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
          Money moves
        </p>
        <h2 ref={headlineRef} className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          Payments move money.
        </h2>
        <p ref={supportRef} className="mt-6 max-w-sm text-base text-muted-foreground sm:text-lg">
          Every transaction leaves a signal.
        </p>
      </div>
    </section>
  )
}
