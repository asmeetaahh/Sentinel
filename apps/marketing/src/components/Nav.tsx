import { CtaButton } from '@/components/CtaButton'

const LINKS = ['Overview', 'Research']

/** No routing exists yet in this app, and the eventual destinations
 * (Explore page, Research section) are out of scope for this task — links
 * render as real, styled, inert anchors rather than invented pages. */
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

      <nav aria-label="Primary" className="hidden items-center gap-8 md:flex">
        {LINKS.map((label) => (
          <a
            key={label}
            href="#"
            onClick={(event) => event.preventDefault()}
            className="text-sm text-muted-foreground transition-colors duration-200 hover:text-foreground"
          >
            {label}
          </a>
        ))}
      </nav>

      <CtaButton className="text-xs sm:text-sm">Explore Sentinel</CtaButton>
    </header>
  )
}
