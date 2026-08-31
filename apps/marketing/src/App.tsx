import { Nav } from '@/components/Nav'
import { SmoothScrollProvider } from '@/components/SmoothScrollProvider'
import { HeroScene } from '@/scenes/HeroScene'
import { BusinessValueSection } from '@/sections/BusinessValueSection'
import { ExplainSection } from '@/sections/ExplainSection'
import { Hero } from '@/sections/Hero'
import { MoneyMovesSection } from '@/sections/MoneyMovesSection'
import { ResponseSection } from '@/sections/ResponseSection'
import { SignalEmergence } from '@/sections/SignalEmergence'
import { SimulateSection } from '@/sections/SimulateSection'
import { StabilizeSection } from '@/sections/StabilizeSection'
import { TrajectorySection } from '@/sections/TrajectorySection'

/**
 * Homepage v1 — hero + the scroll-driven narrative beats built so far.
 * The hero visual is a single fixed background layer shared by every
 * section; each section scrolls its own copy over the top and drives its
 * own GSAP ScrollTrigger independently (see Hero.tsx,
 * MoneyMovesSection.tsx, SignalEmergence.tsx, TrajectorySection.tsx,
 * ExplainSection.tsx, ResponseSection.tsx).
 *
 * Intended narrative order: 00 Hero/Awakening → 01 Money Moves → 02 Risk
 * Moves Differently → 03 Trajectory → 04 Explain → 05 Simulate →
 * 06 Stabilize → 07 Response → 08 Business Value → 09 Technical
 * Credibility → 10 Research Lab → 11 CTA (09–11 not yet built). The old
 * Section 07 ("Sentinel — merchant-level risk intelligence," a
 * radial/orbital visualization) was retired earlier. A later
 * "Sentinel/Product" section (ProductSection, still in
 * src/sections/ProductSection.tsx for reuse) was tried directly after
 * Response but cut from the flow — 00–07 had already established what
 * Sentinel does, so a second full product introduction there read as
 * repetitive. BusinessValueSection now picks up right after Response
 * instead, moving from "what can the merchant do?" to "what does acting
 * earlier change for the business?"
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
        <SimulateSection />
        <StabilizeSection />
        <ResponseSection />
        <BusinessValueSection />
      </div>
    </SmoothScrollProvider>
  )
}

export default App
