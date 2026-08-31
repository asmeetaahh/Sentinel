import { useEffect, useState } from 'react'

const QUERY = '(min-width: 768px) and (max-width: 1099px)'

/** The narrow-desktop/tablet band where the full-size orbital field would
 * crowd the headline — see HeroScene, which scales the field down and
 * shifts it right in this range rather than hiding it like on mobile. */
export function useIsTablet(): boolean {
  const [isTablet, setIsTablet] = useState(() => typeof window !== 'undefined' && window.matchMedia(QUERY).matches)

  useEffect(() => {
    const mql = window.matchMedia(QUERY)
    const onChange = () => setIsTablet(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return isTablet
}
