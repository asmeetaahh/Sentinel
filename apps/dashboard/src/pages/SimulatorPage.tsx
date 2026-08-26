import { useEffect, useState } from 'react'

import { AssistantPanel } from '@/components/assistant/AssistantPanel'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { ControlsPanel } from '@/components/simulator/ControlsPanel'
import { SimulationResult } from '@/components/simulator/SimulationResult'
import { SimulatorIntro } from '@/components/simulator/SimulatorIntro'
import { useMerchantContext } from '@/context/MerchantContext'
import { useMerchantProfile } from '@/hooks/useMerchantProfile'
import { useSimulation } from '@/hooks/useSimulation'
import { useSimulationControls } from '@/hooks/useSimulationControls'
import { baselineValues, buildSimulationRequestBody, hasChangedControls, simulationRequestFromResult } from '@/lib/simulationRequest'

export function SimulatorPage() {
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

  return <SimulatorContent merchantId={selectedMerchantId} />
}

function SimulatorContent({ merchantId }: { merchantId: string }) {
  const profile = useMerchantProfile(merchantId)
  const asOfDate = profile.data?.latest_observed_snapshot.as_of_date ?? null
  const controls = useSimulationControls(merchantId, asOfDate)
  const simulation = useSimulation(merchantId)

  const [values, setValues] = useState<Record<string, number>>({})

  useEffect(() => {
    if (controls.data) {
      setValues(baselineValues(controls.data.controls))
      simulation.reset()
    }
    // Re-initialize sliders (and clear any prior result) whenever a new
    // controls baseline loads — merchant switch or as-of-date change.
    // Deliberately keyed on controls.data only: simulation.reset is a
    // stable identity from useCallback, and including it would re-run
    // this effect on every simulation state change, which is not the
    // trigger we want.
  }, [controls.data])

  if (profile.loading) return <LoadingState label="Loading merchant profile…" />
  if (profile.error) return <ErrorState error={profile.error} />
  if (!profile.data || !asOfDate) return null

  const hasChanges = controls.data ? hasChangedControls(controls.data.controls, values) : false

  function handleRun() {
    if (!controls.data || !asOfDate) return
    simulation.run(buildSimulationRequestBody(asOfDate, controls.data.controls, values))
  }

  function handleReset() {
    if (!controls.data) return
    setValues(baselineValues(controls.data.controls))
    simulation.reset()
  }

  return (
    <div className="flex flex-col gap-6">
      <SimulatorIntro merchantId={merchantId} asOfDate={asOfDate} />

      {controls.loading && <LoadingState label="Loading simulator controls…" />}
      {controls.error ? <ErrorState error={controls.error} /> : null}

      {controls.data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ControlsPanel
            controls={controls.data.controls}
            values={values}
            onChange={(controlId, value) => setValues((prev) => ({ ...prev, [controlId]: value }))}
            onReset={handleReset}
            onRun={handleRun}
            canRun={hasChanges && !simulation.loading}
            running={simulation.loading}
            hasChanges={hasChanges}
          />

          <div>
            {simulation.loading && <LoadingState label="Running simulation on the saved model…" />}
            {simulation.error ? <ErrorState error={simulation.error} /> : null}
            {!simulation.loading && !simulation.error && !simulation.data && (
              <EmptyState
                title="No simulation run yet"
                detail="Adjust a control on the left, then click Run simulation to see the modeled impact."
              />
            )}
            {simulation.data && <SimulationResult result={simulation.data} />}
          </div>
        </div>
      )}

      <AssistantPanel
        key={merchantId}
        merchantId={merchantId}
        asOfDate={asOfDate}
        simulation={simulation.data ? simulationRequestFromResult(simulation.data) : null}
        suggestedPrompts={
          simulation.data
            ? ['Explain the modeled impact of my simulation.', 'Why is my risk elevated?', 'What does this mean for liquidity?']
            : ['Why is my risk elevated?', 'What does this mean for liquidity?']
        }
      />
    </div>
  )
}
