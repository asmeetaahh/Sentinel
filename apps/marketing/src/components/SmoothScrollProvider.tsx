import type { ReactNode } from 'react'

import { useLenis } from '@/hooks/useLenis'

/** Mount once at the app root. Renders children unchanged — this only
 * wires up the Lenis + GSAP smooth-scroll pairing as a side effect. */
export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  useLenis()
  return children
}
