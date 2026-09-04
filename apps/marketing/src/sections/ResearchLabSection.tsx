import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { gsap } from '@/lib/gsap'

/**
 * The project's own README already establishes this as the canonical
 * research destination — "Research Journey" links to
 * `docs/research/RESEARCH.md` (README.md:9, :354) — combined with the
 * repo's actual git remote (`origin` → github.com/asmeetaahh/Sentinel).
 * Not a guessed or placeholder URL. Unchanged from every previous
 * revision of this section.
 */
const RESEARCH_URL = 'https://github.com/asmeetaahh/Sentinel/blob/main/docs/research/RESEARCH.md'

/**
 * "10 — Research Lab": still deliberately the quietest section on the
 * page — same copy, same link, same minimalist character as every
 * earlier version. This revision removes the orbital-ring "signal
 * instrument" (rings/particles/ticks) entirely and replaces it with
 * RiskDivergence (02)'s own signal-field language instead — several
 * faint static lines plus one active line, matched value-for-value
 * (color, weight, dash, opacity, `signal-flow` animation) rather than
 * approximated, the same treatment just corrected onto section 09. No
 * secondary object competes with the text here; the line field IS the
 * background, not a separate illustration next to it. "The signals were
 * already there" (09) becomes "one signal is now the subject of
 * investigation" (10) — the active line stands in for the research
 * question being followed; the faint lines, the alternative signals and
 * observations around it. Kept subtle on purpose — nothing here is
 * literally labeled.
 */
export function ResearchLabSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const reduceMotion = usePrefersReducedMotion()

  useEffect(() => {
    const section = sectionRef.current
    const content = contentRef.current
    if (!section || !content) return

    const ctx = gsap.context(() => {
      if (reduceMotion) {
        gsap.set(content, { opacity: 1, y: 0, filter: 'blur(0px)' })
        return
      }
      gsap.set(content, { opacity: 0, y: 18, filter: 'blur(6px)' })
      gsap.to(content, {
        opacity: 1,
        y: 0,
        filter: 'blur(0px)',
        duration: 1,
        ease: 'power2.out',
        scrollTrigger: { trigger: content, start: 'top 82%', toggleActions: 'play none none reverse' },
      })
    }, section)

    return () => ctx.revert()
  }, [reduceMotion])

  return (
    <section ref={sectionRef} className="bg-background relative overflow-hidden px-6 py-28 sm:px-10 sm:py-36">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: 'radial-gradient(closest-side, rgba(124,108,246,0.045), rgba(124,108,246,0) 70%)' }}
      />
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(244,246,250,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(244,246,250,0.5) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      {/* RiskDivergence (02)'s own device, matched value-for-value:
          several faint static lines (`#8b7bf7`, width 1, opacity 0.22,
          no animation) plus one active line (`#f0a35f`, width 1.5, dash
          "4 7", opacity 0.6, `signal-flow 6s linear infinite`) — the
          same values used to correct section 09, since both are meant
          to read as the same visual language. No tip marker here (that
          was specific to 02's own "risk pointing somewhere" reading);
          just the line field itself, quieter than 02's own foreground
          role since this is background texture behind centered text.
          02 gets away with full-bleed lines because its text sits to one
          side, clear of them; this section's text is centered with no
          side clearance, so every line here is confined to a band near
          the top or bottom edge (y 20–100 or 600–680 of a 700-tall
          viewBox) — a first version spanned the full height and put the
          gold line directly through the support paragraph. */}
      <svg
        aria-hidden
        viewBox="0 0 1440 700"
        preserveAspectRatio="xMidYMid slice"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-70 sm:opacity-90"
      >
        <path d="M -40,40 C 300,20 600,55 900,35 C 1100,22 1300,45 1480,30" fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.22} />
        <path d="M -40,95 C 300,80 600,110 900,90 C 1100,78 1300,100 1480,86" fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.22} />
        <path d="M -40,635 C 300,650 600,618 900,640 C 1100,652 1300,625 1480,642" fill="none" stroke="#8b7bf7" strokeWidth={1} opacity={0.22} />
        <path
          d="M -40,620 C 260,600 520,650 780,624 C 1000,602 1220,635 1480,610"
          fill="none"
          stroke="#f0a35f"
          strokeWidth={1.5}
          strokeDasharray="4 7"
          opacity={0.6}
          style={{
            animation: reduceMotion ? 'none' : 'signal-flow 6s linear infinite',
            filter: 'drop-shadow(0 0 4px rgba(240,163,95,0.4))',
          }}
        />
      </svg>

      <div ref={contentRef} className="relative mx-auto max-w-xl text-center" style={{ opacity: 0 }}>
        <p className="text-xs font-medium tracking-[0.2em] text-accent-soft uppercase">Research lab</p>
        <h2 className="mt-5 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-5xl">
          Where the questions get deeper.
        </h2>
        <p className="mx-auto mt-6 max-w-md text-base text-muted-foreground sm:text-lg">
          Sentinel&apos;s methodology, benchmark design, feature engineering, temporal validation, stress testing,
          and limitations are documented in our research.
        </p>

        <a
          href={RESEARCH_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="group mt-10 inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-2.5 text-sm font-medium text-foreground transition-colors duration-300 hover:border-accent-soft/40 hover:bg-white/[0.03] hover:text-accent-soft sm:text-base"
        >
          Read the Research
          <span aria-hidden className="transition-transform duration-300 ease-out group-hover:translate-x-1">
            →
          </span>
        </a>
      </div>
    </section>
  )
}
