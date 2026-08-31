import { useEffect, useRef } from 'react'

interface ParallaxOptions {
  disabled?: boolean
}

/**
 * Lightweight mouse-based parallax: writes `--parallax-x`/`--parallax-y`
 * (range roughly -0.5..0.5) onto the returned element on `pointermove`,
 * coalesced to at most one write per animation frame. There is no
 * continuous loop — it does nothing between pointer events, and nothing
 * at all when `disabled` (reduced motion, touch/mobile).
 */
export function useParallax({ disabled = false }: ParallaxOptions = {}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const node = ref.current
    if (!node || disabled) return

    let frame = 0
    const onMove = (event: PointerEvent) => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const rect = node.getBoundingClientRect()
        const x = (event.clientX - rect.left) / rect.width - 0.5
        const y = (event.clientY - rect.top) / rect.height - 0.5
        node.style.setProperty('--parallax-x', x.toFixed(3))
        node.style.setProperty('--parallax-y', y.toFixed(3))
      })
    }

    window.addEventListener('pointermove', onMove)
    return () => {
      window.removeEventListener('pointermove', onMove)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [disabled])

  return ref
}
