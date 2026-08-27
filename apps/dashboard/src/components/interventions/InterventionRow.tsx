import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { InterventionRecommendation } from '@/api/types'
import { InlineLoadingState } from '@/components/common/LoadingState'
import { formatPercent } from '@/lib/format'
import { PRIORITY_STYLE } from '@/lib/provenance'

export function InterventionRow({
  recommendation,
  onAcknowledge,
  acknowledging,
  acknowledged,
}: {
  recommendation: InterventionRecommendation
  onAcknowledge: () => void
  acknowledging: boolean
  acknowledged: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const priorityStyle = PRIORITY_STYLE[recommendation.priority]

  return (
    <li className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${priorityStyle.badge}`}>
              {priorityStyle.label}
            </span>
            {recommendation.shap_corroboration.corroborated && (
              <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-indigo-200">
                Verified SHAP driver
              </span>
            )}
          </div>
          <h4 className="mt-1 text-sm font-semibold text-slate-800">{recommendation.title}</h4>
        </div>
        <span className="text-xs text-slate-400 tabular-nums">
          {formatPercent(recommendation.current_value.value)} · {Math.abs(recommendation.deviation_z.value).toFixed(1)}σ
        </span>
      </div>

      <p className="text-sm text-slate-600">{recommendation.reason}</p>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-fit text-xs font-medium text-slate-400 underline decoration-dotted hover:text-slate-600"
      >
        {expanded ? 'Hide details' : 'Why this matters'}
      </button>
      {expanded && (
        <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
          <p>{recommendation.deviation_z.method}</p>
          <p className="mt-1">{recommendation.shap_corroboration.note}</p>
          <p className="mt-1">{recommendation.modeled_impact_reminder}</p>
        </div>
      )}

      <div className="mt-1 flex flex-wrap items-center gap-2">
        <Link
          to={`/simulator?control=${encodeURIComponent(recommendation.control_id)}`}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-500"
        >
          Test in Simulator
        </Link>
        <button
          type="button"
          onClick={onAcknowledge}
          disabled={acknowledging || acknowledged}
          className="flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {acknowledging ? <InlineLoadingState /> : acknowledged ? 'Acknowledged ✓' : 'Acknowledge'}
        </button>
      </div>
    </li>
  )
}
