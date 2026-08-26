import {
  EvidenceIcon,
  ExplainabilityIcon,
  IncidentIcon,
  OverviewIcon,
  RiskIcon,
  SettingsIcon,
  SimulatorIcon,
} from './icons'
import type { ComponentType, SVGProps } from 'react'

interface NavItem {
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
  enabled: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: OverviewIcon, enabled: true },
  { label: 'Risk', icon: RiskIcon, enabled: false },
  { label: 'Explainability', icon: ExplainabilityIcon, enabled: false },
  { label: 'Simulator', icon: SimulatorIcon, enabled: false },
  { label: 'Incident Response', icon: IncidentIcon, enabled: false },
  { label: 'Evidence', icon: EvidenceIcon, enabled: false },
  { label: 'Settings', icon: SettingsIcon, enabled: false },
]

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
          {NAV_ITEMS.map(({ label, icon: Icon, enabled }) =>
            enabled ? (
              <button
                key={label}
                type="button"
                aria-current="page"
                className="flex items-center gap-3 rounded-md bg-slate-800/70 px-3 py-2 text-sm font-medium text-white"
                title={label}
              >
                <Icon className="shrink-0 text-indigo-400" />
                <span className="hidden md:inline">{label}</span>
              </button>
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
