/**
 * The single source of truth for how "observed / modeled / derived" and
 * risk-state colors are represented visually — every component reads from
 * here rather than re-deciding a color scheme locally (see
 * docs/architecture/frontend.md "design system").
 *
 * Every badge below follows the same dark-surface formula — a low-opacity
 * tint background, a bright(-enough) tinted text color, and a matching
 * tinted ring — so status colors read as deliberate "trust metadata," not
 * decorative pills, against Sentinel's dark canvas (--color-background /
 * --color-card in index.css). Semantic meaning is unchanged from before:
 * only the light-surface badge formula (pale bg + dark text) was swapped
 * for its dark-surface equivalent.
 */

import type { DriverDirection, Provenance } from '@/api/types'

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  observed: 'Observed',
  modeled: 'Modeled',
  derived: 'Derived',
  synthetic_prototype: 'Synthetic · Prototype',
}

export const PROVENANCE_STYLE: Record<Provenance, string> = {
  observed: 'bg-slate-400/10 text-slate-300 ring-1 ring-slate-400/30',
  modeled: 'bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-400/30',
  derived: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30',
  // Amber, not one of the other three colors — a prototype construct with no
  // real-data proxy is a distinct kind of thing from observed/modeled/derived
  // data, and should never be visually mistaken for one of them.
  synthetic_prototype: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30',
}

export const RISK_STATE_STYLE = {
  elevated: {
    badge: 'bg-red-500/15 text-red-300 ring-1 ring-red-400/30',
    dot: 'bg-red-500',
    text: 'text-red-400',
    label: 'Elevated',
  },
  normal: {
    badge: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30',
    dot: 'bg-emerald-500',
    text: 'text-emerald-400',
    label: 'Normal',
  },
} as const

export const DRIVER_DIRECTION_STYLE: Record<DriverDirection, { bar: string; text: string; label: string }> = {
  increases_risk: { bar: 'bg-red-500', text: 'text-red-400', label: 'Contributing to modeled risk' },
  decreases_risk: { bar: 'bg-teal-500', text: 'text-teal-400', label: 'Reducing modeled risk' },
  neutral: { bar: 'bg-slate-500', text: 'text-secondary-foreground', label: 'Negligible contribution' },
}

/** Deliberately restrained: only "insufficient" evidence and "elevated" risk
 * state ever use red — priority itself uses amber/slate, not a stoplight of
 * reds, per the incident page's explicit "avoid excessive red / fake
 * urgency" direction. */
export const PRIORITY_STYLE: Record<'high' | 'medium' | 'low', { badge: string; label: string }> = {
  high: { badge: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30', label: 'High priority' },
  medium: { badge: 'bg-slate-400/10 text-slate-300 ring-1 ring-slate-400/30', label: 'Medium priority' },
  low: { badge: 'bg-slate-400/5 text-muted-foreground ring-1 ring-slate-400/20', label: 'Low priority' },
}

/** Confidence/Data Quality V1 never uses red, even for "limited" — this is
 * an honest transparency signal about data sufficiency, not a warning about
 * elevated risk (red stays reserved for that). See
 * docs/architecture/confidence_data_quality.md. */
export const CONFIDENCE_STYLE: Record<'high' | 'medium' | 'limited', { badge: string; label: string }> = {
  high: { badge: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30', label: 'High' },
  medium: { badge: 'bg-slate-400/10 text-slate-300 ring-1 ring-slate-400/30', label: 'Medium' },
  limited: { badge: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30', label: 'Limited' },
}

export const EVIDENCE_READINESS_STYLE: Record<'ready' | 'partial' | 'insufficient', { badge: string; label: string }> = {
  ready: { badge: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30', label: 'Ready' },
  partial: { badge: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/30', label: 'Partial' },
  insufficient: { badge: 'bg-red-500/15 text-red-300 ring-1 ring-red-400/30', label: 'Insufficient' },
}

export const INCIDENT_STATUS_STYLE: Record<'active' | 'resolved', { badge: string; label: string }> = {
  active: { badge: 'bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-400/30', label: 'Active' },
  resolved: { badge: 'bg-slate-400/10 text-slate-300 ring-1 ring-slate-400/30', label: 'Resolved' },
}

export const ACTION_STATUS_STYLE: Record<'reviewed' | 'simulated' | 'acknowledged' | 'dismissed', { badge: string; label: string }> = {
  reviewed: { badge: 'bg-slate-400/10 text-slate-300 ring-1 ring-slate-400/30', label: 'Reviewed' },
  simulated: { badge: 'bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-400/30', label: 'Simulated' },
  acknowledged: { badge: 'bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30', label: 'Acknowledged' },
  dismissed: { badge: 'bg-slate-400/5 text-muted-foreground ring-1 ring-slate-400/20', label: 'Dismissed' },
}

/** "Not observed" is a calm, muted fact of this prototype's design — never
 * styled as a warning/failure. See docs/architecture/intervention_intelligence.md. */
export const OUTCOME_STATUS_STYLE: Record<'not_observed', { badge: string; label: string }> = {
  not_observed: { badge: 'bg-slate-400/5 text-muted-foreground ring-1 ring-slate-400/20', label: 'Not observed' },
}
