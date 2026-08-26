import type { EvidenceReadiness } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { EVIDENCE_READINESS_STYLE } from '@/lib/provenance'

export function EvidenceChecklist({ evidence }: { evidence: EvidenceReadiness }) {
  const readinessStyle = EVIDENCE_READINESS_STYLE[evidence.readiness_status]
  const requiredItems = evidence.items.filter((item) => item.required)
  const missingLabels = evidence.missing_evidence
    .map((category) => evidence.items.find((item) => item.category === category)?.label ?? category)
    .join(', ')

  return (
    <MetricCard title="Evidence readiness" footer={evidence.disclaimer}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${readinessStyle.badge}`}>
          Evidence readiness: {readinessStyle.label.toUpperCase()}
        </span>
        <span className="text-xs text-slate-400 tabular-nums">
          {evidence.available_count} of {evidence.required_count} required available
        </span>
      </div>

      <ul className="mt-4 divide-y divide-slate-100">
        {requiredItems.map((item) => (
          <li key={item.category} className="flex items-start gap-3 py-2.5">
            <span
              aria-hidden="true"
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                item.available ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'
              }`}
            >
              {item.available ? '✓' : '✗'}
            </span>
            <div>
              <p className={`text-sm font-medium ${item.available ? 'text-slate-800' : 'text-slate-500'}`}>
                {item.label}
                <span className="sr-only">{item.available ? ' — available' : ' — missing'}</span>
              </p>
              <p className="text-xs text-slate-400">{item.available ? item.rationale : `${item.label} is missing. ${item.rationale}`}</p>
            </div>
          </li>
        ))}
      </ul>

      {evidence.missing_evidence.length > 0 && (
        <div className="mt-3 rounded-md bg-slate-50 px-3 py-2">
          <p className="text-xs font-medium text-slate-500">Missing, in priority order:</p>
          <p className="text-xs text-slate-600">{missingLabels}</p>
        </div>
      )}
    </MetricCard>
  )
}
