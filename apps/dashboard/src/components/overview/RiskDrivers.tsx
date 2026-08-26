import type { Driver } from '@/api/types'
import { humanizeFeatureName, humanizeGroupName } from '@/lib/format'
import { DRIVER_DIRECTION_STYLE } from '@/lib/provenance'

function DriverRow({ driver, maxAbsShap }: { driver: Driver; maxAbsShap: number }) {
  const style = DRIVER_DIRECTION_STYLE[driver.direction]
  const widthPct = maxAbsShap > 0 ? (Math.abs(driver.shap_value) / maxAbsShap) * 100 : 0

  return (
    <li className="flex flex-col gap-1 py-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-slate-800">{humanizeFeatureName(driver.feature)}</span>
        <span className="text-xs text-slate-400 tabular-nums">value {driver.value.toFixed(3)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${style.bar}`} style={{ width: `${widthPct}%` }} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5">
        <span className={`text-xs font-medium ${style.text}`}>{style.label}</span>
        <span className="text-[11px] tracking-wide text-slate-400 uppercase">{humanizeGroupName(driver.group)}</span>
      </div>
      <p className="text-xs leading-snug text-slate-400">{driver.definition}</p>
    </li>
  )
}

export function RiskDrivers({
  positive,
  negative,
  causalityDisclaimer,
}: {
  positive: Driver[]
  negative: Driver[]
  causalityDisclaimer: string
}) {
  const maxAbsShap = Math.max(0, ...[...positive, ...negative].map((d) => Math.abs(d.shap_value)))

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-500">Verified model drivers</h3>
        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-indigo-200">
          SHAP · Modeled
        </span>
      </header>

      {positive.length === 0 && negative.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-400">No driver data available for this prediction date.</p>
      ) : (
        <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold tracking-wide text-red-700 uppercase">Pushing risk higher</h4>
            <ul className="divide-y divide-slate-100">
              {positive.map((driver) => (
                <DriverRow key={driver.feature} driver={driver} maxAbsShap={maxAbsShap} />
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-wide text-teal-700 uppercase">Pushing risk lower</h4>
            <ul className="divide-y divide-slate-100">
              {negative.map((driver) => (
                <DriverRow key={driver.feature} driver={driver} maxAbsShap={maxAbsShap} />
              ))}
            </ul>
          </div>
        </div>
      )}

      <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-400">{causalityDisclaimer}</p>
    </section>
  )
}
