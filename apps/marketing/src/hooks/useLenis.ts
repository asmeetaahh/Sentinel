import Lenis from 'lenis'
import { useEffect } from 'react'

import { gsap, ScrollTrigger } from '@/lib/gsap'

/**
 * Mounts a single Lenis smooth-scroll instance for the app's lifetime and
 * drives it from GSAP's own ticker (rather than a separate
 * requestAnimationFrame loop), so Lenis's scroll position and GSAP/
 * ScrollTrigger-driven animations never drift out of sync — the standard
 * pairing for this stack. Call once, near the root (see
 * SmoothScrollProvider).
 */
export function useLenis() {
  useEffect(() => {
    const lenis = new Lenis()

    lenis.on('scroll', ScrollTrigger.update)

    const tick = (time: number) => {
      lenis.raf(time * 1000)
    }
    gsap.ticker.add(tick)
    gsap.ticker.lagSmoothing(0)

    return () => {
      gsap.ticker.remove(tick)
      lenis.destroy()
    }
  }, [])
}
