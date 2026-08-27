/**
 * The single source of truth for how "observed / modeled / derived" and
 * risk-state colors are represented visually — every component reads from
 * here rather than re-deciding a color scheme locally (see
 * docs/architecture/frontend.md "design system").
 */

import type { DriverDirection, Provenance } from '@/api/types'

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  observed: 'Observed',
  modeled: 'Modeled',
  derived: 'Derived',
  synthetic_prototype: 'Synthetic · Prototype',
}

export const PROVENANCE_STYLE: Record<Provenance, string> = {
  observed: 'bg-slate-100 text-slate-700 ring-1 ring-slate-300',
  modeled: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200',
  derived: 'bg-teal-50 text-teal-700 ring-1 ring-teal-200',
  // Amber, not one of the other three colors — a prototype construct with no
  // real-data proxy is a distinct kind of thing from observed/modeled/derived
  // data, and should never be visually mistaken for one of them.
  synthetic_prototype: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200',
}

export const RISK_STATE_STYLE = {
  elevated: {
    badge: 'bg-red-50 text-red-700 ring-1 ring-red-200',
    dot: 'bg-red-600',
    text: 'text-red-700',
    label: 'Elevated',
  },
  normal: {
    badge: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
    dot: 'bg-emerald-600',
    text: 'text-emerald-700',
    label: 'Normal',
  },
} as const

export const DRIVER_DIRECTION_STYLE: Record<DriverDirection, { bar: string; text: string; label: string }> = {
  increases_risk: { bar: 'bg-red-500', text: 'text-red-700', label: 'Contributing to modeled risk' },
  decreases_risk: { bar: 'bg-teal-500', text: 'text-teal-700', label: 'Reducing modeled risk' },
  neutral: { bar: 'bg-slate-300', text: 'text-slate-500', label: 'Negligible contribution' },
}

/** Deliberately restrained: only "insufficient" evidence and "elevated" risk
 * state ever use red — priority itself uses amber/slate, not a stoplight of
 * reds, per the incident page's explicit "avoid excessive red / fake
 * urgency" direction. */
export const PRIORITY_STYLE: Record<'high' | 'medium' | 'low', { badge: string; label: string }> = {
  high: { badge: 'bg-amber-100 text-amber-900 ring-1 ring-amber-300', label: 'High priority' },
  medium: { badge: 'bg-slate-100 text-slate-700 ring-1 ring-slate-300', label: 'Medium priority' },
  low: { badge: 'bg-slate-50 text-slate-500 ring-1 ring-slate-200', label: 'Low priority' },
}

/** Confidence/Data Quality V1 never uses red, even for "limited" — this is
 * an honest transparency signal about data sufficiency, not a warning about
 * elevated risk (red stays reserved for that). See
 * docs/architecture/confidence_data_quality.md. */
export const CONFIDENCE_STYLE: Record<'high' | 'medium' | 'limited', { badge: string; label: string }> = {
  high: { badge: 'bg-teal-50 text-teal-700 ring-1 ring-teal-200', label: 'High' },
  medium: { badge: 'bg-slate-100 text-slate-700 ring-1 ring-slate-300', label: 'Medium' },
  limited: { badge: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200', label: 'Limited' },
}

export const EVIDENCE_READINESS_STYLE: Record<'ready' | 'partial' | 'insufficient', { badge: string; label: string }> = {
  ready: { badge: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200', label: 'Ready' },
  partial: { badge: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200', label: 'Partial' },
  insufficient: { badge: 'bg-red-50 text-red-700 ring-1 ring-red-200', label: 'Insufficient' },
}

export const INCIDENT_STATUS_STYLE: Record<'active' | 'resolved', { badge: string; label: string }> = {
  active: { badge: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200', label: 'Active' },
  resolved: { badge: 'bg-slate-100 text-slate-600 ring-1 ring-slate-300', label: 'Resolved' },
}

export const ACTION_STATUS_STYLE: Record<'reviewed' | 'simulated' | 'acknowledged' | 'dismissed', { badge: string; label: string }> = {
  reviewed: { badge: 'bg-slate-100 text-slate-700 ring-1 ring-slate-300', label: 'Reviewed' },
  simulated: { badge: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200', label: 'Simulated' },
  acknowledged: { badge: 'bg-teal-50 text-teal-700 ring-1 ring-teal-200', label: 'Acknowledged' },
  dismissed: { badge: 'bg-slate-50 text-slate-500 ring-1 ring-slate-200', label: 'Dismissed' },
}

/** "Not observed" is a calm, muted fact of this prototype's design — never
 * styled as a warning/failure. See docs/architecture/intervention_intelligence.md. */
export const OUTCOME_STATUS_STYLE: Record<'not_observed', { badge: string; label: string }> = {
  not_observed: { badge: 'bg-slate-50 text-slate-500 ring-1 ring-slate-200', label: 'Not observed' },
}
