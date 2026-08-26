/**
 * Formatting helpers. The synthetic benchmark's GMV/exposure/liquidity
 * values are explicitly unitless ("GMV units" — see
 * docs/architecture/data_generation.md), so amounts are never rendered
 * with a currency symbol; that would falsely imply real-world calibration.
 */

const numberFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const percentFormatter = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })
const dateFormatter = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
const shortDateFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' })

export function formatAmount(value: number): string {
  return `${numberFormatter.format(value)} units`
}

export function formatAmountCompact(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value)} units`
  }
  return formatAmount(value)
}

export function formatPercent(value: number): string {
  return percentFormatter.format(value)
}

export function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

export function formatShortDate(isoDate: string): string {
  return shortDateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

export function formatRatio(value: number, digits = 2): string {
  return value.toFixed(digits)
}

/** Purely mechanical formatting (underscores -> spaces, capitalized) — never
 * a reinterpretation or invented meaning of the feature name. */
export function humanizeFeatureName(featureName: string): string {
  const spaced = featureName.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function humanizeGroupName(group: string): string {
  return group
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatSignedPercentPoints(value: number): string {
  const points = value * 100
  const sign = points > 0 ? '+' : ''
  return `${sign}${points.toFixed(1)}pp`
}

/** Relative change formatted as a signed percentage, e.g. "+11.6%". Used
 * for the simulator's comparison table, where current/simulated values are
 * shown in their own native units but "how much did this move" is easiest
 * to read as one consistent normalized column across metrics. */
export function formatSignedRelativePercent(relative: number | null): string {
  if (relative === null) return '—'
  const pct = relative * 100
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(1)}%`
}
