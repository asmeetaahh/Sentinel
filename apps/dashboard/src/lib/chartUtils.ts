/**
 * Chart-only display transforms. These operate purely on real observed
 * values already returned by the backend — no new values are fetched,
 * modeled, or invented. A trailing moving average is applied to the
 * naturally sparse/zero-inflated daily chargeback/refund rates purely for
 * chart readability (see docs/research/dataset_validation_report.md on
 * why raw daily rates are noisy for low-volume merchants) and is always
 * labeled as such in the UI.
 */

export function trailingMovingAverage(values: number[], window: number): number[] {
  const result: number[] = []
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= window) sum -= values[i - window]
    const count = Math.min(i + 1, window)
    result.push(sum / count)
  }
  return result
}
