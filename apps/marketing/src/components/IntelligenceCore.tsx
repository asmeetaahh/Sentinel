import { useIsMobile } from '@/hooks/useIsMobile'
import { useIsTablet } from '@/hooks/useIsTablet'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

/**
 * The central "Sentinel intelligence core" — a glowing orb rather than
 * the earlier flat hexagon. Depth comes from a radial gradient that goes
 * dark at the center and brightens toward a luminous rim (rather than a
 * conventional "lit sphere" gradient), an off-center soft highlight for
 * an internal light cue, a very faint rotating "latitude" grid for
 * surface detail, and a crisp inset edge ring plus a tightly-bounded
 * outer glow via box-shadow. A sphere's silhouette doesn't change under
 * rotation, so there's no tilt trick here (unlike the old hexagon) —
 * only the faint internal grid spins, and the whole orb gets a slow,
 * small vertical bob instead of any spin of its own.
 *
 * Earlier revisions stacked three large blurred glow layers (an
 * atmospheric halo, a "concentrated" glow, and the box-shadow bloom) on
 * top of each other, which drowned the orb's own silhouette in diffuse
 * purple — "a giant blurry glow" rather than a defined object. This
 * version keeps exactly one small ambient halo plus a tightly-bounded
 * box-shadow, and holds the gradient dark for most of the radius so the
 * bright rim reads as a controlled edge highlight, not a bloom.
 */
export function IntelligenceCore() {
  const reduceMotion = usePrefersReducedMotion()
  const isMobile = useIsMobile()
  const isTablet = useIsTablet()
  const size = isMobile ? 148 : isTablet ? 195 : 270

  return (
    <div
      className="pointer-events-none absolute"
      style={
        isMobile
          ? { left: '50%', top: '78%', transform: 'translate(-50%, -50%)' }
          : { left: isTablet ? '72%' : '65%', top: '46%', transform: 'translate(-50%, -50%)' }
      }
    >
      {/* small ambient halo — this is the ONLY large soft glow behind the
          orb now; earlier revisions stacked two more on top of this plus
          a wide box-shadow bloom, which is what buried the sphere's own
          edge in diffuse purple */}
      <div
        aria-hidden
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          width: size * 1.6,
          height: size * 1.6,
          background: 'radial-gradient(closest-side, rgba(124,108,246,0.12), rgba(124,108,246,0) 72%)',
        }}
      />

      {/* soft contact/rim glow underneath, anchoring the orb in the scene */}
      <div
        aria-hidden
        className="absolute left-1/2 rounded-full"
        style={{
          top: size * 0.94,
          width: size * 1.2,
          height: size * 0.22,
          transform: 'translate(-50%, -50%)',
          background: 'radial-gradient(closest-side, rgba(139,123,247,0.32), rgba(139,123,247,0) 70%)',
          filter: 'blur(5px)',
          animation: reduceMotion ? 'none' : 'glow-breathe 7s ease-in-out infinite',
        }}
      />

      {/* the orb + logo float together with a slow, small vertical bob */}
      <div
        className="relative"
        style={{
          width: size,
          height: size,
          animation: reduceMotion ? 'none' : 'orb-float 9s ease-in-out infinite',
        }}
      >
        {/* the orb body: dark core, crisp defined edge, controlled rim
            glow — gradient stays dark through most of the radius so the
            bright rim reads as a bounded edge highlight, not a bloom */}
        <div
          className="absolute inset-0 overflow-hidden rounded-full"
          style={{
            background:
              'radial-gradient(circle, #020207 0%, #0a0818 50%, #170f36 68%, #40357e 83%, #7c6cf6 93%, #b3a2f5 100%)',
            boxShadow:
              'inset 0 0 0 1.5px rgba(203,190,255,0.65), inset 0 0 22px rgba(0,0,0,0.55), 0 0 18px 1px rgba(139,123,247,0.35)',
          }}
        >
          {/* subtle internal light — an off-center soft highlight rather
              than the base gradient's own (centered) rim glow */}
          <div
            aria-hidden
            className="absolute rounded-full"
            style={{
              top: '20%',
              left: '24%',
              width: size * 0.4,
              height: size * 0.4,
              background: 'radial-gradient(closest-side, rgba(216,205,255,0.3), rgba(216,205,255,0) 75%)',
              filter: 'blur(3px)',
            }}
          />

          {/* very subtle orange warmth on the right, hinting at the
              financial-impact orbit without dominating the orb */}
          <div
            aria-hidden
            className="absolute rounded-full"
            style={{
              top: '30%',
              right: '-12%',
              width: size * 0.5,
              height: size * 0.5,
              background: 'radial-gradient(closest-side, rgba(240,163,95,0.12), rgba(240,163,95,0) 75%)',
              mixBlendMode: 'screen',
            }}
          />

          {/* extremely faint rotating surface detail — a few latitude
              lines, not a literal globe */}
          <svg
            aria-hidden
            viewBox="0 0 100 100"
            className="absolute inset-0"
            style={{ animation: reduceMotion ? 'none' : 'orb-surface-spin 60s linear infinite' }}
          >
            <g stroke="rgba(196,186,255,0.16)" strokeWidth={0.4} fill="none">
              <ellipse cx={50} cy={50} rx={48} ry={16} />
              <ellipse cx={50} cy={50} rx={40} ry={48} />
              <ellipse cx={50} cy={50} rx={48} ry={30} transform="rotate(35 50 50)" />
            </g>
          </svg>
        </div>

        {/* subtle vertical light streak — a directional beam through the
            sphere's interior, not a halo wrapped around the logo shape,
            so it stays even after removing the S's own glow below */}
        <div
          aria-hidden
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{
            width: 3,
            height: size * 0.46,
            background: 'linear-gradient(to bottom, transparent, rgba(200,185,255,0.75), transparent)',
            filter: 'blur(1.5px)',
            animation: reduceMotion ? 'none' : 'glow-breathe 5s ease-in-out infinite',
          }}
        />

        {/* centered Sentinel S — no glow/halo of its own; the earlier
            blurred radial-gradient disc behind it read as an artificial
            aura wrapped around the mark. Crisp and purple on its own
            contrast against the sphere's dark inset face is enough. */}
        <img
          src="/sentinel-logo.png"
          alt="Sentinel"
          width={size * 0.42}
          height={size * 0.42}
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ mixBlendMode: 'screen' }}
        />
      </div>
    </div>
  )
}
