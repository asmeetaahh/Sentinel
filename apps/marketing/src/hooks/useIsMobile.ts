import { useEffect, useState } from 'react'

const QUERY = '(max-width: 767px)'

/** Matches Tailwind's `md` breakpoint. Used sparingly — only where a 3D
 * scene's camera/composition genuinely can't be fixed with CSS alone
 * (see HeroScene), never as a general layout mechanism. */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia(QUERY).matches)

  useEffect(() => {
    const mql = window.matchMedia(QUERY)
    const onChange = () => setIsMobile(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return isMobile
}
