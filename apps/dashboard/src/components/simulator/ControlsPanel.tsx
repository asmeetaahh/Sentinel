import type { ControlMeta } from '@/api/types'
import { MetricCard } from '@/components/common/MetricCard'
import { InlineLoadingState } from '@/components/common/LoadingState'

import { ControlSlider } from './ControlSlider'

export function ControlsPanel({
  controls,
  values,
  onChange,
  onReset,
  onRun,
  canRun,
  running,
  hasChanges,
  highlightedControlId,
}: {
  controls: ControlMeta[]
  values: Record<string, number>
  onChange: (controlId: string, value: number) => void
  onReset: () => void
  onRun: () => void
  canRun: boolean
  running: boolean
  hasChanges: boolean
  highlightedControlId?: string | null
}) {
  return (
    <MetricCard title="Bounded operational controls">
      <div className="flex flex-col gap-6">
        {controls.map((control) => (
          <ControlSlider
            key={control.control_id}
            control={control}
            value={values[control.control_id] ?? control.baseline_value}
            onChange={(value) => onChange(control.control_id, value)}
            highlighted={control.control_id === highlightedControlId}
          />
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3 border-t border-border-subtle pt-4">
        <button
          type="button"
          onClick={onRun}
          disabled={!canRun}
          className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {running ? <InlineLoadingState /> : 'Run simulation'}
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={!hasChanges || running}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-secondary-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset to observed values
        </button>
      </div>
      {!hasChanges && (
        <p className="mt-2 text-xs text-muted-foreground">Adjust at least one control above to run a simulation.</p>
      )}
    </MetricCard>
  )
}
