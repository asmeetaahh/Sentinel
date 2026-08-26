import { useEffect, useRef, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: unknown
}

/**
 * Runs `fetcher` whenever `deps` changes, tracking loading/error/data and
 * ignoring results from requests that were superseded by a newer one
 * (e.g. rapid merchant switching) — never lets a stale response overwrite
 * fresher data.
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: React.DependencyList): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const requestId = useRef(0)

  useEffect(() => {
    const id = ++requestId.current
    setState((prev) => ({ data: prev.data, loading: true, error: null }))

    fetcher()
      .then((data) => {
        if (requestId.current === id) setState({ data, loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (requestId.current === id) setState({ data: null, loading: false, error })
      })
    // `deps` is intentionally caller-supplied and dynamic (this is a
    // generic "refetch when these inputs change" hook) — the linter can't
    // statically verify it's exhaustive, but that's by design here, not an
    // oversight; fetcher() itself is expected to close over the same deps.
  }, deps)

  return state
}
