/**
 * Small typed HTTP client for the Sentinel backend. All requests go
 * through here — components never call `fetch` directly (see
 * docs/architecture/frontend.md).
 */

import type { ApiErrorBody } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** Thrown when the backend cannot be reached at all (network/CORS/offline) — distinct from a valid HTTP error response. */
export class ApiUnavailableError extends Error {
  constructor(cause: unknown) {
    super('The Sentinel backend is unreachable.')
    this.name = 'ApiUnavailableError'
    this.cause = cause
  }
}

async function request<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(path, BASE_URL)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url.toString(), { headers: { Accept: 'application/json' } })
  } catch (cause) {
    throw new ApiUnavailableError(cause)
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as ApiErrorBody
      if (body?.detail) detail = body.detail
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
}

export const apiClient = { request, BASE_URL }
