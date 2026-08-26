import type { ControlMeta, SimulationRequestBody } from '@/api/types'

/** Builds the POST body from the current slider values, including ONLY the
 * controls whose value differs from its observed baseline — an untouched
 * slider is not "sent as unchanged", it is simply omitted, exactly matching
 * backend/simulation's "every other feature stays at its observed value"
 * contract. Explicit per-control assignment (not a dynamic dict) keeps this
 * type-safe against SimulationRequestBody's fixed shape. */
export function buildSimulationRequestBody(
  asOfDate: string,
  controls: ControlMeta[],
  values: Record<string, number>,
): SimulationRequestBody {
  const body: SimulationRequestBody = { as_of_date: asOfDate }
  for (const control of controls) {
    const value = values[control.control_id] ?? control.baseline_value
    if (value === control.baseline_value) continue
    switch (control.control_id) {
      case 'refund_rate_28d':
        body.refund_rate_28d = value
        break
      case 'fulfillment_on_time_rate_28d':
        body.fulfillment_on_time_rate_28d = value
        break
      case 'new_customer_rate_28d':
        body.new_customer_rate_28d = value
        break
    }
  }
  return body
}

export function hasChangedControls(controls: ControlMeta[], values: Record<string, number>): boolean {
  // Falls back to baseline for a control missing from `values` (e.g. the
  // brief render before the initializing effect runs) so that state is
  // correctly treated as "unchanged", not spuriously "changed".
  return controls.some((control) => (values[control.control_id] ?? control.baseline_value) !== control.baseline_value)
}

export function baselineValues(controls: ControlMeta[]): Record<string, number> {
  const values: Record<string, number> = {}
  for (const control of controls) values[control.control_id] = control.baseline_value
  return values
}
