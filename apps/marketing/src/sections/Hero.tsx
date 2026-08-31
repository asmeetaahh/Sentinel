import { useEffect, useRef } from 'react'

import { gsap, ScrollTrigger } from '@/lib/gsap'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

/**
 * No CTA row here on purpose — "Explore Sentinel" and "Overview/Research"
 * already exist in the nav (see Nav.tsx), so repeating them in the hero
 * content was redundant. The gradient rule beneath the supporting copy
 * keeps the left column reading as intentionally composed rather than
 * trailing off into empty space.
 *
 * Uses `h-dvh`, not `h-screen` (100vh) — every full-viewport section
 * shares this unit so their heights stay exactly seamless. Plain `vh` is
 * fixed to the browser's initial layout viewport, so on mobile browsers
 * whose address bar hides/shows while scrolling, each section's true
 * height silently drifts from what GSAP ScrollTrigger measured at
 * setup, which can make scrolling between sections feel unreliable.
 * `dvh` tracks the actual visible viewport instead.
 */
export function Hero() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const content = contentRef.current
    const section = sectionRef.current
    if (!content || !section) return

    const children = Array.from(content.children)

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(children, { opacity: 1, y: 0 })
      } else {
        gsap.fromTo(
          children,
          { opacity: 0, y: 28 },
          { opacity: 1, y: 0, duration: 1, ease: 'power3.out', stagger: 0.12, delay: 0.15 },
        )
      }

      // Hero copy fades/lifts out over exactly one hero-height of scroll,
      // so it's gone by the time the section itself has scrolled past.
      ScrollTrigger.create({
        trigger: section,
        start: 'top top',
        end: 'bottom top',
        scrub: true,
        onUpdate: (self) => {
          gsap.set(content, {
            opacity: 1 - self.progress,
            y: reduceMotion ? 0 : -self.progress * 50,
          })
        },
      })
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  return (
    <section ref={sectionRef} className="relative flex h-dvh items-center px-6 sm:px-10">
      <div ref={contentRef} className="max-w-xl">
        <p className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
          Early risk intelligence for merchants
        </p>

        <h1 className="mt-5 text-4xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-6xl">
          Know the risk before the{' '}
          <span className="bg-gradient-to-r from-accent to-accent-soft bg-clip-text text-transparent">
            settlement shock
          </span>
          .
        </h1>

        <p className="mt-6 max-w-md text-base text-muted-foreground sm:text-lg">
          Early signals. Financial impact.
          <br />
          Testable decisions. Response ready.
        </p>

        <div className="mt-9 h-px w-24 bg-gradient-to-r from-accent to-transparent" />
      </div>

      <ScrollCue />
    </section>
  )
}

function ScrollCue() {
  return (
    <div className="absolute inset-x-0 bottom-10 flex flex-col items-center gap-2 text-muted-foreground">
      <span className="text-[10px] font-medium tracking-[0.25em] uppercase">Scroll to explore</span>
      <span className="h-8 w-px animate-pulse bg-gradient-to-b from-muted-foreground to-transparent" />
    </div>
  )
}
