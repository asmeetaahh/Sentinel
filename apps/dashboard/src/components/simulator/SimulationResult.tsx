import type { Delta, SimulationResponse } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { formatAmountCompact, formatPercent, formatRatio, formatSignedRelativePercent } from '@/lib/format'
import { RISK_STATE_STYLE } from '@/lib/provenance'

function DeltaCell({ delta }: { delta: Delta | null }) {
  if (!delta) {
    return <span className="text-xs text-muted-foreground">Not computed</span>
  }
  if (delta.absolute === 0) {
    return <span className="text-xs font-medium text-muted-foreground">No change</span>
  }
  const color = delta.absolute > 0 ? 'text-red-400' : 'text-teal-400'
  return <span className={`text-xs font-semibold tabular-nums ${color}`}>{formatSignedRelativePercent(delta.relative)}</span>
}

function ComparisonRow({
  label,
  current,
  simulated,
  delta,
}: {
  label: string
  current: React.ReactNode
  simulated: React.ReactNode
  delta: Delta | null
}) {
  return (
    <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr] items-center gap-3 border-b border-border-subtle py-3 last:border-0">
      <span className="text-sm text-secondary-foreground">{label}</span>
      <span className="text-right text-sm font-medium text-secondary-foreground tabular-nums">{current}</span>
      <span className="text-right text-sm font-semibold text-foreground tabular-nums">{simulated}</span>
      <span className="text-right">
        <DeltaCell delta={delta} />
      </span>
    </div>
  )
}

function RiskStateBadge({ state }: { state: 'elevated' | 'normal' }) {
  const style = RISK_STATE_STYLE[state]
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${style.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
      {style.label}
    </span>
  )
}

export function SimulationResult({ result }: { result: SimulationResponse }) {
  return (
    <MetricCard title="Simulation result" footer={result.modeled_impact_disclaimer} emphasized>
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-indigo-600 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-white uppercase">
            Modeled impact
          </span>
          <span className="text-xs text-muted-foreground">
            {result.horizon_days}-day horizon · {result.controls.length} control{result.controls.length === 1 ? '' : 's'} changed
          </span>
        </div>

        <div className="flex items-center gap-3">
          <RiskStateBadge state={result.current.risk_state} />
          <span className="text-slate-300" aria-hidden="true">
            &rarr;
          </span>
          <RiskStateBadge state={result.simulated.risk_state} />
        </div>

        <div>
          <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr] gap-3 border-b border-border pb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            <span>Metric</span>
            <span className="text-right">Current</span>
            <span className="text-right">Simulated</span>
            <span className="text-right">Change</span>
          </div>

          <ComparisonRow
            label="Modeled probability (30d)"
            current={formatPercent(result.current.probability_calibrated)}
            simulated={formatPercent(result.simulated.probability_calibrated)}
            delta={result.probability_delta}
          />
          <ComparisonRow
            label="Estimated exposure"
            current={formatAmountCompact(result.exposure.current.value)}
            simulated={formatAmountCompact(result.exposure.simulated.value)}
            delta={result.exposure.delta}
          />
          <ComparisonRow
            label="Liquidity stress"
            current={result.liquidity_stress.current.value === null ? 'n/a' : formatRatio(result.liquidity_stress.current.value)}
            simulated={
              result.liquidity_stress.simulated.value === null ? 'n/a' : formatRatio(result.liquidity_stress.simulated.value)
            }
            delta={result.liquidity_stress.delta}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">Controls changed</p>
          <ul className="flex flex-col gap-1">
            {result.controls.map((control) => (
              <li key={control.control_id} className="flex items-center justify-between text-sm text-secondary-foreground">
                <span>{control.label}</span>
                <span className="tabular-nums">
                  {formatPercent(control.baseline_value)} <span className="text-slate-300">&rarr;</span>{' '}
                  <span className="font-medium text-indigo-300">{formatPercent(control.simulated_value)}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-muted-foreground">{result.exposure.simulated.method}</p>
      </div>
    </MetricCard>
  )
}
