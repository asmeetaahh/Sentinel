import type { RiskResponse } from '@/api/types'
import { ProvenanceTag } from '@/components/common/ProvenanceTag'
import { formatDate, formatPercent, formatSignedPercentPoints } from '@/lib/format'
import { RISK_STATE_STYLE } from '@/lib/provenance'
import { useRiskTrend } from '@/hooks/useRiskTrend'

export function RiskSummary({ risk }: { risk: RiskResponse }) {
  const style = RISK_STATE_STYLE[risk.model.risk_state]
  const { trend } = useRiskTrend(risk.merchant_id, risk.as_of_date, risk.model.probability_calibrated)

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="flex items-center gap-4">
          <span
            className={`flex h-14 w-14 items-center justify-center rounded-full ${style.badge}`}
            aria-hidden="true"
          >
            <span className={`h-3.5 w-3.5 rounded-full ${style.dot}`} />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Risk state</p>
              <ProvenanceTag provenance={risk.model.provenance} />
            </div>
            <p className={`text-2xl font-semibold ${style.text}`}>{style.label}</p>
            <p className="mt-0.5 text-xs text-slate-400">
              30-day horizon · as of {formatDate(risk.as_of_date)}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1 text-right">
          <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Modeled probability</p>
          <p className="text-xl font-semibold text-slate-700 tabular-nums">
            {formatPercent(risk.model.probability_calibrated)}
          </p>
          {trend && (
            <p
              className={`text-xs font-medium tabular-nums ${trend.deltaProbability > 0 ? 'text-red-600' : trend.deltaProbability < 0 ? 'text-teal-600' : 'text-slate-400'}`}
            >
              {formatSignedPercentPoints(trend.deltaProbability)} vs {trend.windowDays}d ago
            </p>
          )}
          <p className="text-[11px] text-slate-400">
            Flag threshold {formatPercent(risk.model.decision_threshold)}
          </p>
        </div>
      </div>

      <p className="mt-5 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-400">
        {risk.model.disclaimer}
      </p>
    </section>
  )
}
