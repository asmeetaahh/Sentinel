import type { IncidentDetail } from '@/api/types'
import { formatDate, formatShortDate, humanizeGroupName } from '@/lib/format'
import { INCIDENT_STATUS_STYLE, PRIORITY_STYLE } from '@/lib/provenance'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium tracking-wide text-slate-400 uppercase">{label}</p>
      <p className="font-semibold text-slate-700 tabular-nums">{value}</p>
    </div>
  )
}

export function IncidentHeader({ incident }: { incident: IncidentDetail }) {
  const statusStyle = INCIDENT_STATUS_STYLE[incident.status]
  const priorityStyle = PRIORITY_STYLE[incident.priority]

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Incident · {humanizeGroupName(incident.event_type)}</p>
          <h2 className="text-xl font-semibold text-slate-900">{incident.incident_id}</h2>
          <p className="mt-1 text-sm text-slate-600">{incident.reason_code.label}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle.badge}`}>
            {statusStyle.label}
          </span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${priorityStyle.badge}`}>
            {priorityStyle.label}
          </span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-4">
        <Stat label="Window" value={`${formatShortDate(incident.window.start_date)} – ${formatShortDate(incident.window.end_date)}`} />
        <Stat label="Detected" value={formatDate(incident.detected_date)} />
        <Stat label="Reason code" value={incident.reason_code.code} />
        <Stat label="Estimated cases" value={String(incident.case_summary.estimated_case_count)} />
      </div>

      {incident.priority_reasons.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">Why this priority</p>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-xs text-slate-500">
            {incident.priority_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-400">
        {incident.reason_code.description} {incident.reason_code.taxonomy_disclaimer}
      </p>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">{incident.scenario_context.note}</p>
    </section>
  )
}
