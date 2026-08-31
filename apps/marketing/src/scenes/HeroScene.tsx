import { IntelligenceCore } from '@/components/IntelligenceCore'
import { OrbitalField } from '@/components/OrbitalField'
import { SignalMarkers } from '@/components/SignalMarkers'
import { useIsMobile } from '@/hooks/useIsMobile'
import { useIsTablet } from '@/hooks/useIsTablet'
import { useParallax } from '@/hooks/useParallax'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

/**
 * Sentinel's hero visual: a layered 2.5D CSS/SVG composition (atmosphere,
 * an orbital ring field, labeled signal markers, and a central
 * "intelligence core") — no canvas, no 3D engine, no meshes. Depth comes
 * from gradients, drop shadows and a bounded CSS tilt; "rotation" comes
 * from independent, very slow `@keyframes` animations (see index.css)
 * rather than a per-frame render loop.
 *
 * OrbitalField, SignalMarkers, and IntelligenceCore all anchor at the
 * exact same `fieldLeft`/`fieldTop` point with no origin-shifting
 * transform beyond centering — so the rings' geometric center exactly
 * coincides with the sphere's own center (Saturn's-rings-around-a-planet,
 * not lines floating some distance below it), and a marker's connector
 * line can be computed to land exactly on a ring's boundary (see
 * lib/orbitalGeometry).
 */
export function HeroScene() {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const isTablet = useIsTablet()
  const parallaxRef = useParallax({ disabled: reduceMotion || isMobile })

  // Must match IntelligenceCore's own anchor exactly (see below) so the
  // ring field's center coincides with the sphere's center.
  const fieldLeft = isTablet ? '72%' : '65%'
  const fieldTop = '46%'
  const fieldScale = isTablet ? 0.68 : 1

  return (
    <div ref={parallaxRef} className="absolute inset-0">
      <BackdropGlow reduceMotion={reduceMotion} />
      <FaintTerrain left={fieldLeft} top={fieldTop} />
      <DistantParticles />

      {!isMobile && (
        <>
          <ParallaxLayer strength={10}>
            <div
              className="absolute"
              style={{ left: fieldLeft, top: fieldTop, transform: `scale(${fieldScale})`, transformOrigin: '0 0' }}
            >
              <OrbitalField />
            </div>
          </ParallaxLayer>

          <ParallaxLayer strength={22}>
            <div
              className="absolute"
              style={{ left: fieldLeft, top: fieldTop, transform: `scale(${fieldScale})`, transformOrigin: '0 0' }}
            >
              <SignalMarkers />
            </div>
          </ParallaxLayer>
        </>
      )}

      <ParallaxLayer strength={16}>
        <IntelligenceCore />
      </ParallaxLayer>
    </div>
  )
}

function ParallaxLayer({ strength, children }: { strength: number; children: React.ReactNode }) {
  return (
    <div
      className="absolute inset-0"
      style={{
        transform: `translate3d(calc(var(--parallax-x, 0) * ${strength}px), calc(var(--parallax-y, 0) * ${strength}px), 0)`,
      }}
    >
      {children}
    </div>
  )
}

function BackdropGlow({ reduceMotion }: { reduceMotion: boolean }) {
  return (
    <div
      aria-hidden
      className="absolute"
      style={{
        left: '58%',
        top: '48%',
        width: 900,
        height: 700,
        transform: 'translate(-50%, -50%)',
        background: 'radial-gradient(closest-side, rgba(124,108,246,0.14), rgba(124,108,246,0) 70%)',
        filter: 'blur(10px)',
        animation: reduceMotion ? 'none' : 'atmosphere-drift 42s ease-in-out infinite',
      }}
    />
  )
}

/** A very faint grid confined to the orbital field's neighborhood, fading
 * out radially — reads as "network/terrain" without becoming a texture
 * of its own. Desktop/tablet only; too small a canvas on mobile to be
 * worth the extra layer. */
function FaintTerrain({ left, top }: { left: string; top: string }) {
  return (
    <div
      aria-hidden
      className="absolute hidden md:block"
      style={{
        left,
        top,
        width: 900,
        height: 560,
        transform: 'translate(-450px, -280px)',
        backgroundImage:
          'linear-gradient(to right, rgba(196,188,255,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(196,188,255,0.5) 1px, transparent 1px)',
        backgroundSize: '46px 46px',
        maskImage: 'radial-gradient(closest-side, black, transparent 75%)',
        WebkitMaskImage: 'radial-gradient(closest-side, black, transparent 75%)',
        opacity: 0.05,
      }}
    />
  )
}

const DISTANT_POINTS = [
  { left: '20%', top: '22%', size: 2, opacity: 0.25 },
  { left: '78%', top: '78%', size: 1.5, opacity: 0.2 },
  { left: '88%', top: '18%', size: 1.5, opacity: 0.22 },
  { left: '10%', top: '68%', size: 1.5, opacity: 0.18 },
  { left: '48%', top: '85%', size: 2, opacity: 0.2 },
  { left: '92%', top: '52%', size: 1.5, opacity: 0.22 },
]

/** A handful of sparse, dim points across the whole hero — not a star
 * field, just enough to keep the far background from reading as flat. */
function DistantParticles() {
  return (
    <div aria-hidden className="absolute inset-0">
      {DISTANT_POINTS.map((point) => (
        <span
          key={`${point.left}-${point.top}`}
          className="absolute rounded-full bg-[#c9befb]"
          style={{ left: point.left, top: point.top, width: point.size, height: point.size, opacity: point.opacity }}
        />
      ))}
    </div>
  )
}
