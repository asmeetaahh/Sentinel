import { ArrowRight } from 'lucide-react'
import type { ComponentPropsWithoutRef } from 'react'

interface CtaButtonProps extends ComponentPropsWithoutRef<'a'> {
  variant?: 'primary' | 'ghost'
}

/** The one recurring call-to-action shape used in the nav and the hero —
 * kept as a single component so "Explore Sentinel" looks identical
 * everywhere it appears. Callers pass their own `href` (and `target`/
 * `rel` for external destinations); this component no longer hardcodes
 * an inert `href="#"` now that Nav actually links it to the live
 * dashboard. */
export function CtaButton({ variant = 'primary', className = '', children, ...props }: CtaButtonProps) {
  const base = 'inline-flex items-center gap-2 rounded-full text-sm font-medium transition-colors duration-200'
  const styles =
    variant === 'primary'
      ? 'bg-accent px-5 py-2.5 text-white shadow-[0_0_24px_-6px_rgba(139,123,247,0.6)] hover:bg-accent-soft'
      : 'border border-accent/40 px-5 py-2.5 text-foreground hover:border-accent/70'

  return (
    <a className={`${base} ${styles} ${className}`} {...props}>
      {children}
      <ArrowRight className="h-4 w-4" aria-hidden="true" />
    </a>
  )
}
