import { NavLink } from 'react-router-dom'

import { NAV_ITEMS } from './navigation'

export function Sidebar() {
  return (
    <aside className="flex h-full w-16 flex-col justify-between border-r border-slate-800 bg-slate-950 py-4 md:w-60 md:px-3">
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-2 px-2 md:px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600 text-sm font-semibold text-white">
            S
          </span>
          <div className="hidden flex-col leading-tight md:flex">
            <span className="text-sm font-semibold tracking-wide text-white">Sentinel</span>
            <span className="text-[11px] text-slate-400">Risk Intelligence</span>
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
                  `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? 'bg-slate-800/70 text-white' : 'text-slate-300 hover:bg-slate-900 hover:text-white'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
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
                className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-500"
              >
                <Icon className="shrink-0 text-slate-600" />
                <span className="hidden items-center gap-2 md:flex">
                  {label}
                  <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
                    Soon
                  </span>
                </span>
              </button>
            ),
          )}
        </nav>
      </div>

      <div className="hidden px-2 text-[11px] leading-snug text-slate-500 md:block">
        Synthetic benchmark prototype. No real merchant or Razorpay data.
      </div>
    </aside>
  )
}
