import { useState } from 'react'

import type { SimulationRequestBody } from '@/api/types'
import { InlineLoadingState } from '@/components/common/LoadingState'
import { useRecordIntervention } from '@/hooks/useRecordIntervention'

/**
 * The "optionally record the supported action/simulation state" step of the
 * product loop: only rendered when the just-run simulation touched exactly
 * the one control an active intervention recommendation names. Recording
 * re-sends these exact controls to the backend, which re-runs the real
 * simulator itself (backend/memory/risk_memory_service.py) — this
 * component never computes or asserts a modeled-impact number itself.
 */
export function RecordSimulationInMemory({
  merchantId,
  interventionId,
  simulationRequest,
  onRecorded,
}: {
  merchantId: string
  interventionId: string
  simulationRequest: SimulationRequestBody
  onRecorded: () => void
}) {
  const record = useRecordIntervention(merchantId)
  const [done, setDone] = useState(false)

  async function handleClick() {
    const result = await record.record({ intervention_id: interventionId, action_status: 'simulated', simulation: simulationRequest })
    if (result) {
      setDone(true)
      onRecorded()
    }
  }

  if (done) {
    return <p className="text-xs font-medium text-teal-700">✓ Recorded in Risk Memory</p>
  }

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={record.loading}
        className="flex w-fit items-center gap-2 rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {record.loading ? <InlineLoadingState /> : 'Record this modeled impact in Risk Memory'}
      </button>
      {record.error ? <p className="text-xs text-red-600">Could not record this action. Try again.</p> : null}
    </div>
  )
}
