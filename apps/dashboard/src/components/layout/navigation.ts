import type { ComponentType, SVGProps } from 'react'

import { EvidenceIcon, ExplainabilityIcon, IncidentIcon, OverviewIcon, RiskIcon, SimulatorIcon } from './icons'

export interface NavItem {
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
  enabled: boolean
  to: string
}

/** Single source of truth for the sidebar's nav items AND the header's
 * current-page title (Header looks up the active route's label here rather
 * than hardcoding a page title — see Header.tsx).
 *
 * There is deliberately no "Settings" entry: no settings/preferences
 * functionality exists anywhere in the backend (no user accounts, no
 * configurable state), so a disabled "Settings — Soon" placeholder would
 * be a dead promise rather than a real product surface. See
 * docs/architecture/frontend.md. */
export const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: OverviewIcon, enabled: true, to: '/' },
  { label: 'Risk', icon: RiskIcon, enabled: true, to: '/risk' },
  { label: 'Explainability', icon: ExplainabilityIcon, enabled: true, to: '/explainability' },
  { label: 'Simulator', icon: SimulatorIcon, enabled: true, to: '/simulator' },
  { label: 'Incident Response', icon: IncidentIcon, enabled: true, to: '/incident-response' },
  { label: 'Evidence', icon: EvidenceIcon, enabled: true, to: '/evidence' },
]
