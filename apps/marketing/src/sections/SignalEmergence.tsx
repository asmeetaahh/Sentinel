import { useEffect, useRef } from 'react'

import { RiskDivergence } from '@/components/RiskDivergence'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

/**
 * The first narrative beat after the hero. Its background is deliberately
 * opaque (`bg-background`) rather than letting the hero's fixed canvas
 * show through — the hero's core/orbital visual is a fixed full-viewport
 * layer shared by every section, so without an opaque background here it
 * kept reading as "the hero simply continuing underneath." This section
 * gets its own much quieter atmosphere and its own signal-divergence
 * visual (see RiskDivergence) instead.
 *
 * The headline reveals one line at a time on a single non-scrubbed
 * timeline (eyebrow, then three lines in sequence), played once when the
 * section scrolls into view, rather than fading in as one block.
 */
export function SignalEmergence() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const eyebrowRef = useRef<HTMLParagraphElement>(null)
  const line1Ref = useRef<HTMLSpanElement>(null)
  const line2Ref = useRef<HTMLSpanElement>(null)
  const line3Ref = useRef<HTMLSpanElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const content = contentRef.current
    const pieces = [eyebrowRef.current, line1Ref.current, line2Ref.current, line3Ref.current]
    if (!section || !content || pieces.some((piece) => !piece)) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(pieces, { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }

      gsap.set(pieces, { opacity: 0, y: 22, filter: 'blur(6px)' })

      // Triggered off the text block itself (not the section) — the text
      // sits vertically centered in a full-viewport section, so a
      // section-top trigger would fire while it's still far below the
      // fold and finish animating before the user ever sees it move.
      const timeline = gsap.timeline({
        scrollTrigger: {
          trigger: content,
          start: 'top 85%',
          toggleActions: 'play none none reverse',
        },
        defaults: { duration: 0.9, ease: 'power2.out' },
      })

      const delays = [0, 0.15, 0.35, 0.55]
      pieces.forEach((piece, index) => {
        timeline.to(piece, { opacity: 1, y: 0, filter: 'blur(0px)' }, delays[index])
      })
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  return (
    <section
      ref={sectionRef}
      className="bg-background relative flex h-dvh items-center justify-center overflow-hidden px-6 text-center sm:px-10"
    >
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: 'radial-gradient(closest-side, rgba(124,108,246,0.12), rgba(124,108,246,0) 70%)' }}
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
      <RiskDivergence />

      <div ref={contentRef} className="relative max-w-2xl">
        <p ref={eyebrowRef} className="text-xs font-medium tracking-[0.2em] text-amber-200/80 uppercase">
          Risk moves differently
        </p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight sm:text-5xl">
          <span ref={line1Ref} className="block">
            The same signals a merchant
          </span>
          <span ref={line2Ref} className="block">
            trusts can already be
          </span>
          <span ref={line3Ref} className="block">
            pointing somewhere else.
          </span>
        </h2>
      </div>
    </section>
  )
}
