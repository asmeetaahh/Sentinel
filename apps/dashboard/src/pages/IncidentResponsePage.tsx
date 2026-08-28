import { useEffect, useState } from 'react'

import type { RiskResponse } from '@/api/types'
import { AssistantPanel } from '@/components/assistant/AssistantPanel'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { CaseSummaryCard } from '@/components/incidents/CaseSummaryCard'
import { EvidenceChecklist } from '@/components/incidents/EvidenceChecklist'
import { IncidentHeader } from '@/components/incidents/IncidentHeader'
import { IncidentList } from '@/components/incidents/IncidentList'
import { IncidentModeIntro } from '@/components/incidents/IncidentModeIntro'
import { ResponsePreparation } from '@/components/incidents/ResponsePreparation'
import { ExposureCard } from '@/components/overview/ExposureCard'
import { LiquidityCard } from '@/components/overview/LiquidityCard'
import { RiskDrivers } from '@/components/overview/RiskDrivers'
import { RiskSummary } from '@/components/overview/RiskSummary'
import { useMerchantContext } from '@/context/MerchantContext'
import { useIncident } from '@/hooks/useIncident'
import { useIncidents } from '@/hooks/useIncidents'

export function IncidentResponsePage() {
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

  return <IncidentResponseContent merchantId={selectedMerchantId} />
}

function IncidentResponseContent({ merchantId }: { merchantId: string }) {
  const incidents = useIncidents(merchantId)
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)

  useEffect(() => {
    setSelectedIncidentId(incidents.data && incidents.data.incidents.length > 0 ? incidents.data.incidents[0].incident_id : null)
    // Re-select the merchant's first incident whenever the incident list
    // reloads (merchant switch) — never keep a stale selection from a
    // previous merchant around.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidents.data])

  if (incidents.loading) return <LoadingState label="Loading incidents…" />
  if (incidents.error) return <ErrorState error={incidents.error} />
  if (!incidents.data) return null

  if (incidents.data.count === 0) {
    return (
      <div className="flex flex-col gap-6">
        <IncidentModeIntro merchantId={merchantId} />
        <EmptyState
          title="No incidents detected for this merchant"
          detail="The existing saved model did not flag any of this merchant's synthetic risk episodes as elevated within their own window — a realistic outcome of imperfect recall, not an empty feature. See docs/architecture/incident_response.md."
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <IncidentModeIntro merchantId={merchantId} />
      <IncidentList
        incidents={incidents.data.incidents}
        selectedIncidentId={selectedIncidentId}
        onSelect={setSelectedIncidentId}
      />
      {selectedIncidentId && <IncidentDetailPane incidentId={selectedIncidentId} />}
    </div>
  )
}

function IncidentDetailPane({ incidentId }: { incidentId: string }) {
  const incident = useIncident(incidentId)

  if (incident.loading) return <LoadingState label="Loading incident…" />
  if (incident.error) return <ErrorState error={incident.error} />
  if (!incident.data) return null

  const data = incident.data
  const riskResponseView: RiskResponse = {
    merchant_id: data.merchant_id,
    as_of_date: data.detected_date,
    day_index: data.day_index,
    horizon_days: data.horizon_days,
    model: data.model,
    exposure: data.exposure,
    liquidity: data.liquidity,
  }

  return (
    <div className="flex flex-col gap-6">
      <IncidentHeader incident={data} />
      <RiskSummary risk={riskResponseView} />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ExposureCard exposure={data.exposure} />
        <LiquidityCard liquidity={data.liquidity} />
      </div>
      <RiskDrivers
        positive={data.drivers.top_positive_contributors}
        negative={data.drivers.top_negative_contributors}
        causalityDisclaimer={data.causality_disclaimer}
      />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <CaseSummaryCard caseSummary={data.case_summary} />
        <EvidenceChecklist evidence={data.evidence_readiness} />
      </div>
      <ResponsePreparation incident={data} key={`response-prep-${data.incident_id}`} />

      <AssistantPanel
        key={`assistant-${data.incident_id}`}
        merchantId={data.merchant_id}
        incidentId={data.incident_id}
        suggestedPrompts={[
          'Summarize this incident for review.',
          'What evidence is still missing?',
          'Draft internal preparation notes for this incident.',
        ]}
      />
    </div>
  )
}
