import { useEffect, useState } from 'react'

import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { CaseSummaryCard } from '@/components/incidents/CaseSummaryCard'
import { EvidenceChecklist } from '@/components/incidents/EvidenceChecklist'
import { IncidentHeader } from '@/components/incidents/IncidentHeader'
import { IncidentList } from '@/components/incidents/IncidentList'
import { useMerchantContext } from '@/context/MerchantContext'
import { useIncident } from '@/hooks/useIncident'
import { useIncidents } from '@/hooks/useIncidents'

export function EvidencePage() {
  const { merchantsLoading, merchantsError, selectedMerchantId } = useMerchantContext()

  if (merchantsLoading && !selectedMerchantId) {
    return <LoadingState label="Loading merchants…" />
  }
  if (merchantsError) {
    return <ErrorState error={merchantsError} />
  }
  if (!selectedMerchantId) {
    return <EmptyState title="No merchants available" detail="The benchmark returned no merchants to display." />
  }

  return <EvidenceContent merchantId={selectedMerchantId} />
}

function EvidenceContent({ merchantId }: { merchantId: string }) {
  const incidents = useIncidents(merchantId)
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)

  useEffect(() => {
    setSelectedIncidentId(incidents.data && incidents.data.incidents.length > 0 ? incidents.data.incidents[0].incident_id : null)
    // Re-select the merchant's first incident whenever the incident list
    // reloads (merchant switch) — never keep a stale selection from a
    // previous merchant around.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidents.data])

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-xl border border-border bg-card p-5 shadow-sm shadow-black/20">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Evidence Readiness</p>
        <p className="mt-2 max-w-3xl text-sm text-secondary-foreground">
          Reason-code-specific evidence readiness for <span className="font-medium">{merchantId}</span>'s detected
          incidents — the same evidence-readiness logic shown on Incident Response, focused here on what's available
          versus missing. Sentinel never fabricates a document, transaction record, tracking number, invoice ID, or
          piece of dispute evidence: a category is either verifiably available from observed benchmark data (or a
          disclosed prototype assumption) or reported as missing. See docs/architecture/incident_response.md.
        </p>
      </section>

      {incidents.loading && <LoadingState label="Loading incidents…" />}
      {incidents.error ? <ErrorState error={incidents.error} /> : null}

      {incidents.data && incidents.data.count === 0 && (
        <EmptyState
          title="No incidents detected for this merchant"
          detail="The existing saved model did not flag any of this merchant's synthetic risk episodes as elevated within their own window — a realistic outcome of imperfect recall, not an empty feature. See docs/architecture/incident_response.md."
        />
      )}

      {incidents.data && incidents.data.count > 0 && (
        <>
          <IncidentList
            incidents={incidents.data.incidents}
            selectedIncidentId={selectedIncidentId}
            onSelect={setSelectedIncidentId}
          />
          {selectedIncidentId && <EvidenceDetailPane incidentId={selectedIncidentId} />}
        </>
      )}
    </div>
  )
}

function EvidenceDetailPane({ incidentId }: { incidentId: string }) {
  const incident = useIncident(incidentId)

  if (incident.loading) return <LoadingState label="Loading incident evidence…" />
  if (incident.error) return <ErrorState error={incident.error} />
  if (!incident.data) return null

  return (
    <div className="flex flex-col gap-6">
      <IncidentHeader incident={incident.data} />
      <CaseSummaryCard caseSummary={incident.data.case_summary} />
      <EvidenceChecklist evidence={incident.data.evidence_readiness} />
    </div>
  )
}
