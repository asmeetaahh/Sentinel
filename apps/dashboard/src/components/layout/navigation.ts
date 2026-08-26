import type { ComponentType, SVGProps } from 'react'

import {
  EvidenceIcon,
  ExplainabilityIcon,
  IncidentIcon,
  OverviewIcon,
  RiskIcon,
  SettingsIcon,
  SimulatorIcon,
} from './icons'

export interface NavItem {
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
  enabled: boolean
  to: string
}

/** Single source of truth for the sidebar's nav items AND the header's
 * current-page title (Header looks up the active route's label here rather
 * than hardcoding a page title — see Header.tsx). */
export const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', icon: OverviewIcon, enabled: true, to: '/' },
  { label: 'Risk', icon: RiskIcon, enabled: false, to: '/risk' },
  { label: 'Explainability', icon: ExplainabilityIcon, enabled: false, to: '/explainability' },
  { label: 'Simulator', icon: SimulatorIcon, enabled: true, to: '/simulator' },
  { label: 'Incident Response', icon: IncidentIcon, enabled: false, to: '/incident-response' },
  { label: 'Evidence', icon: EvidenceIcon, enabled: false, to: '/evidence' },
  { label: 'Settings', icon: SettingsIcon, enabled: false, to: '/settings' },
]
