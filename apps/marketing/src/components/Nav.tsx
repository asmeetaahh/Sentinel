import { CtaButton } from '@/components/CtaButton'

const DASHBOARD_URL = 'https://sentinel-dashboard-39tw.onrender.com/'

/** The "Overview"/"Research" nav links (inert placeholders — no routing
 * existed for them anyway) were removed along with the homepage sections
 * they pointed toward. Logo/branding stay as-is; the CTA now links out to
 * the live deployed dashboard instead of being an inert anchor. */
export function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex items-center justify-between px-6 py-5 sm:px-10">
      <div className="flex items-center gap-3">
        <img src="/sentinel-logo.png" alt="" width={32} height={32} className="h-8 w-8 rounded-md" />
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-wide text-accent">Sentinel</span>
          <span className="text-[11px] text-muted-foreground">Risk Intelligence</span>
        </div>
      </div>

      <CtaButton href={DASHBOARD_URL} target="_blank" rel="noopener noreferrer" className="text-xs sm:text-sm">
        Explore Sentinel
      </CtaButton>
    </header>
  )
}
