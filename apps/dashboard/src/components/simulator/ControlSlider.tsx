import type { ControlMeta } from '@/api/types'
import { formatPercent } from '@/lib/format'

export function ControlSlider({
  control,
  value,
  onChange,
  highlighted = false,
}: {
  control: ControlMeta
  value: number
  onChange: (value: number) => void
  /** Set when this control was arrived at via an intervention
   * recommendation's "Test in Simulator" link (?control=<id>) — a visual
   * cue only, changes no behavior or bounds. */
  highlighted?: boolean
}) {
  const range = control.max_value - control.min_value
  const baselinePct = range === 0 ? 0 : ((control.baseline_value - control.min_value) / range) * 100
  const step = Math.max(range / 500, 0.0005)
  const isChanged = value !== control.baseline_value
  const descriptionId = `${control.control_id}-description`

  return (
    <div className={`flex flex-col gap-2 ${highlighted ? 'rounded-lg p-2 ring-2 ring-indigo-300' : ''}`}>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={control.control_id} className="text-sm font-medium text-foreground">
          {control.label}
        </label>
        <span className={`text-sm font-semibold tabular-nums ${isChanged ? 'text-indigo-300' : 'text-secondary-foreground'}`}>
          {formatPercent(value)}
        </span>
      </div>

      <div className="relative py-1">
        <input
          id={control.control_id}
          type="range"
          min={control.min_value}
          max={control.max_value}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          aria-describedby={descriptionId}
          className="w-full accent-indigo-600"
        />
        <span
          aria-hidden="true"
          title={`Currently observed value: ${formatPercent(control.baseline_value)}`}
          className="pointer-events-none absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-slate-300"
          style={{ left: `${baselinePct}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{formatPercent(control.min_value)}</span>
        <span>Observed baseline: {formatPercent(control.baseline_value)}</span>
        <span>{formatPercent(control.max_value)}</span>
      </div>

      <p id={descriptionId} className="text-xs text-muted-foreground">
        {control.description}
      </p>
    </div>
  )
}
