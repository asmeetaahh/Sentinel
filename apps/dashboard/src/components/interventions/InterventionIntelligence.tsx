import { useState } from 'react'

import type { InterventionRecommendationsResponse } from '@/api/types'
import { EmptyState } from '@/components/common/EmptyState'
import { MetricCard } from '@/components/common/MetricCard'
import { useRecordIntervention } from '@/hooks/useRecordIntervention'

import { InterventionRow } from './InterventionRow'

export function InterventionIntelligence({
  merchantId,
  interventions,
  onRecorded,
}: {
  merchantId: string
  interventions: InterventionRecommendationsResponse
  onRecorded: () => void
}) {
  const acknowledge = useRecordIntervention(merchantId)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [acknowledgedIds, setAcknowledgedIds] = useState<ReadonlySet<string>>(new Set())

  async function handleAcknowledge(interventionId: string) {
    setPendingId(interventionId)
    const result = await acknowledge.record({ intervention_id: interventionId, action_status: 'acknowledged' })
    setPendingId(null)
    if (result) {
      setAcknowledgedIds((prev) => new Set(prev).add(interventionId))
      onRecorded()
    }
  }

  return (
    <MetricCard title="Recommended interventions" provenance="derived">
      <p className="mb-3 text-xs text-slate-400">
        Deterministic, rule-based candidates — grounded in this merchant's own deviation from its recent baseline
        across the three bounded simulator controls, not an ML prediction or an AI-generated suggestion. Reviewing
        or testing one does not guarantee a change in real-world risk.
      </p>

      {interventions.count === 0 ? (
        <EmptyState title="No intervention currently justified" detail={interventions.empty_state_note ?? undefined} />
      ) : (
        <ul className="divide-y divide-slate-100">
          {interventions.recommendations.map((rec) => (
            <InterventionRow
              key={rec.intervention_id}
              recommendation={rec}
              onAcknowledge={() => handleAcknowledge(rec.intervention_id)}
              acknowledging={pendingId === rec.intervention_id}
              acknowledged={acknowledgedIds.has(rec.intervention_id)}
            />
          ))}
        </ul>
      )}
    </MetricCard>
  )
}
