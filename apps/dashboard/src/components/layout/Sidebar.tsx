import { NavLink } from 'react-router-dom'

import { NAV_ITEMS } from './navigation'

export function Sidebar() {
  return (
    <aside className="flex h-full w-16 flex-col justify-between border-r border-border bg-background py-4 md:w-60 md:px-3">
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-2 px-2 md:px-2">
          <img src="/sentinel-logo.png" alt="" width={30} height={30} className="h-[30px] w-[30px] shrink-0 rounded-md" />
          <div className="hidden flex-col leading-tight md:flex">
            <span className="text-sm font-semibold tracking-wide text-indigo-300">Sentinel</span>
            <span className="text-[11px] text-muted-foreground">Risk Intelligence</span>
          </div>
        </div>

        <nav aria-label="Primary" className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ label, icon: Icon, enabled, to }) =>
            enabled ? (
              <NavLink
                key={label}
                to={to}
                end={to === '/'}
                title={label}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md border px-3 py-2 text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'border-indigo-500/30 bg-indigo-500/10 text-foreground shadow-[0_0_16px_-4px_rgba(129,140,248,0.35)]'
                      : 'border-transparent text-secondary-foreground hover:border-indigo-500/15 hover:bg-indigo-500/5 hover:text-foreground'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={`shrink-0 ${isActive ? 'text-indigo-300 drop-shadow-[0_0_4px_rgba(165,180,252,0.55)]' : 'text-muted-foreground'}`}
                    />
                    <span className="hidden md:inline">{label}</span>
                  </>
                )}
              </NavLink>
            ) : (
              <button
                key={label}
                type="button"
                disabled
                aria-disabled="true"
                title={`${label} — coming soon`}
                className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground"
              >
                <Icon className="shrink-0 text-muted-foreground" />
                <span className="hidden items-center gap-2 md:flex">
                  {label}
                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    Soon
                  </span>
                </span>
              </button>
            ),
          )}
        </nav>
      </div>

      <div className="hidden px-2 text-[11px] leading-snug text-muted-foreground md:block">
        Synthetic benchmark prototype. No real merchant or Razorpay data.
      </div>
    </aside>
  )
}
