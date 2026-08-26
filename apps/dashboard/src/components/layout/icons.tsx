import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function base(children: React.ReactNode, props: IconProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      width={18}
      height={18}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export const OverviewIcon = (props: IconProps) =>
  base(
    <>
      <rect x="3" y="3" width="6" height="6" rx="1" />
      <rect x="11" y="3" width="6" height="6" rx="1" />
      <rect x="3" y="11" width="6" height="6" rx="1" />
      <rect x="11" y="11" width="6" height="6" rx="1" />
    </>,
    props,
  )

export const RiskIcon = (props: IconProps) =>
  base(<path d="M10 2.5l6.5 3v4.2c0 4-2.7 6.9-6.5 7.8-3.8-.9-6.5-3.8-6.5-7.8V5.5l6.5-3z" />, props)

export const ExplainabilityIcon = (props: IconProps) =>
  base(
    <>
      <path d="M10 2.8a4.6 4.6 0 0 0-2.7 8.3c.5.4.7.9.7 1.4v.3h4v-.3c0-.5.2-1 .7-1.4A4.6 4.6 0 0 0 10 2.8z" />
      <path d="M8 15.5h4M8.5 17.2h3" />
    </>,
    props,
  )

export const SimulatorIcon = (props: IconProps) =>
  base(
    <>
      <path d="M4 5h12M4 10h12M4 15h12" />
      <circle cx="7" cy="5" r="1.4" fill="currentColor" />
      <circle cx="13" cy="10" r="1.4" fill="currentColor" />
      <circle cx="8" cy="15" r="1.4" fill="currentColor" />
    </>,
    props,
  )

export const IncidentIcon = (props: IconProps) =>
  base(
    <>
      <path d="M10 3l7.5 13H2.5L10 3z" />
      <path d="M10 8.3v3.4" />
      <circle cx="10" cy="14" r="0.15" fill="currentColor" stroke="none" />
    </>,
    props,
  )

export const EvidenceIcon = (props: IconProps) =>
  base(
    <>
      <path d="M6 2.5h6l3 3V17a.8.8 0 0 1-.8.8H6.8A.8.8 0 0 1 6 17V2.5z" />
      <path d="M8 9h4M8 12h4" />
    </>,
    props,
  )

export const SettingsIcon = (props: IconProps) =>
  base(
    <>
      <circle cx="10" cy="10" r="2.6" />
      <path d="M10 3v1.6M10 15.4V17M17 10h-1.6M4.6 10H3M14.8 5.2l-1.1 1.1M6.3 13.7l-1.1 1.1M14.8 14.8l-1.1-1.1M6.3 6.3 5.2 5.2" />
    </>,
    props,
  )

export const ChevronDownIcon = (props: IconProps) => base(<path d="M5 7.5l5 5 5-5" />, props)
