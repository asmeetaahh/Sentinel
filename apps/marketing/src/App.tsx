import { Nav } from '@/components/Nav'
import { SmoothScrollProvider } from '@/components/SmoothScrollProvider'
import { HeroScene } from '@/scenes/HeroScene'
import { ExplainSection } from '@/sections/ExplainSection'
import { Hero } from '@/sections/Hero'
import { MoneyMovesSection } from '@/sections/MoneyMovesSection'
import { SignalEmergence } from '@/sections/SignalEmergence'
import { TrajectorySection } from '@/sections/TrajectorySection'

/**
 * Homepage — hero + the scroll-driven narrative beats 00–04, ending
 * immediately after Section 04 (Explain, "That's why we built
 * Sentinel."). The hero visual is a single fixed background layer shared
 * by every section; each section scrolls its own copy over the top and
 * drives its own GSAP ScrollTrigger independently (see Hero.tsx,
 * MoneyMovesSection.tsx, SignalEmergence.tsx, TrajectorySection.tsx,
 * ExplainSection.tsx).
 *
 * Everything that previously followed Section 04 — Simulate, Stabilize,
 * Response, Business Value, Technical Credibility, Research Lab — was
 * deliberately cut from the homepage. Their component files are left on
 * disk (src/sections/*.tsx) rather than deleted, since they represent
 * completed, previously-approved work that may be reused or reinstated
 * later; they are simply no longer imported or rendered here.
 */
function App() {
  return (
    <SmoothScrollProvider>
      <Nav />

      <div className="pointer-events-none fixed inset-0 -z-10">
        <HeroScene />
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-background to-transparent" />
      </div>

      <div className="relative">
        <Hero />
        <MoneyMovesSection />
        <SignalEmergence />
        <TrajectorySection />
        <ExplainSection />
      </div>
    </SmoothScrollProvider>
  )
}

export default App
