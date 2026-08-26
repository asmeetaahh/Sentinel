import type { IncidentSummary } from '@/api/types'
import { formatShortDate } from '@/lib/format'
import { EVIDENCE_READINESS_STYLE, PRIORITY_STYLE } from '@/lib/provenance'

export function IncidentList({
  incidents,
  selectedIncidentId,
  onSelect,
}: {
  incidents: IncidentSummary[]
  selectedIncidentId: string | null
  onSelect: (incidentId: string) => void
}) {
  return (
    <nav aria-label="Incidents" className="flex flex-col gap-2">
      {incidents.map((incident) => {
        const isSelected = incident.incident_id === selectedIncidentId
        const priorityStyle = PRIORITY_STYLE[incident.priority]
        const readinessStyle = EVIDENCE_READINESS_STYLE[incident.evidence_readiness_status]

        return (
          <button
            key={incident.incident_id}
            type="button"
            onClick={() => onSelect(incident.incident_id)}
            aria-current={isSelected ? 'true' : undefined}
            className={`flex flex-col gap-1.5 rounded-lg border px-4 py-3 text-left transition-colors ${
              isSelected ? 'border-indigo-300 bg-indigo-50/60' : 'border-slate-200 bg-white hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-slate-800">{incident.incident_id}</span>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${priorityStyle.badge}`}>{priorityStyle.label}</span>
            </div>
            <p className="text-xs text-slate-500">{incident.reason_code_label}</p>
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
              <span>
                {formatShortDate(incident.window.start_date)}–{formatShortDate(incident.window.end_date)}
              </span>
              <span className={`rounded-full px-1.5 py-0.5 font-medium ${readinessStyle.badge}`}>{readinessStyle.label}</span>
            </div>
          </button>
        )
      })}
    </nav>
  )
}
