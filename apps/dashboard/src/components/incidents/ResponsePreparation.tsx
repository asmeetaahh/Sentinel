import { useState } from 'react'

import type { IncidentDetail } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'

const STEPS = ['Review', 'Evidence check', 'Prepare response', 'Merchant confirmation required'] as const

/**
 * A workflow TRACKER, not a submission system. There is no backend call
 * anywhere in this component — "Prepare response" only reveals a local,
 * client-side confirmation message. Sentinel never submits a dispute, never
 * claims one was filed, and never claims access to Razorpay's actual
 * dispute infrastructure. See docs/architecture/incident_response.md.
 */
export function ResponsePreparation({ incident }: { incident: IncidentDetail }) {
  const [prepared, setPrepared] = useState(false)
  const evidenceReady = incident.evidence_readiness.readiness_status === 'ready'
  const currentStepIndex = !evidenceReady ? 1 : prepared ? 3 : 2

  return (
    <MetricCard title="Response preparation">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-xs">
        {STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-1 font-medium ${
                index <= currentStepIndex
                  ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200'
                  : 'bg-slate-50 text-slate-400 ring-1 ring-slate-200'
              }`}
            >
              {step}
            </span>
            {index < STEPS.length - 1 && (
              <span className="text-slate-300" aria-hidden="true">
                &rarr;
              </span>
            )}
          </li>
        ))}
      </ol>

      <div className="mt-4 border-t border-slate-100 pt-4">
        {!evidenceReady ? (
          <p className="text-sm text-slate-500">
            Evidence readiness must reach READY before a response can be prepared for this incident. Resolve the
            missing evidence listed above first.
          </p>
        ) : !prepared ? (
          <button
            type="button"
            onClick={() => setPrepared(true)}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
          >
            Prepare response
          </button>
        ) : (
          <div className="rounded-md border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
            <p className="font-medium">Merchant confirmation required.</p>
            <p className="mt-1 text-indigo-800">
              Sentinel has organized the available evidence for this incident. Nothing has been submitted anywhere —
              this prototype does not file or submit disputes. A merchant would need to explicitly review and confirm
              this response before it could be prepared for submission through Razorpay's actual dispute process,
              which Sentinel does not have access to.
            </p>
          </div>
        )}
      </div>
    </MetricCard>
  )
}
