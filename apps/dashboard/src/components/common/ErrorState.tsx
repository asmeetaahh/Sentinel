import { ApiError, ApiUnavailableError } from '@/api/client'

export function describeError(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiUnavailableError) {
    return {
      title: 'Backend unavailable',
      detail: 'The Sentinel API could not be reached. Confirm it is running and VITE_API_BASE_URL is correct (see .env).',
    }
  }
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return { title: 'Not found', detail: error.detail }
    }
    if (error.status === 400) {
      return { title: 'Request not supported', detail: error.detail }
    }
    if (error.status === 503) {
      return { title: 'Provider unavailable', detail: error.detail }
    }
    if (error.status === 422) {
      return { title: 'Invalid request', detail: error.detail }
    }
    return { title: `Request failed (${error.status})`, detail: error.detail }
  }
  return { title: 'Something went wrong', detail: error instanceof Error ? error.message : String(error) }
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { title, detail } = describeError(error)
  return (
    <div role="alert" className="flex flex-col gap-2 rounded-lg border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm">
      <p className="font-medium text-red-300">{title}</p>
      <p className="text-red-400/90">{detail}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 w-fit rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/20"
        >
          Retry
        </button>
      )}
    </div>
  )
}
