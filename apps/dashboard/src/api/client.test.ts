import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, ApiUnavailableError, apiClient } from './client'

describe('apiClient.request', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('builds the URL with query params and returns parsed JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ hello: 'world' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiClient.request<{ hello: string }>('/merchants/M0000/risk', {
      params: { as_of_date: '2024-01-01', horizon_days: 30 },
    })

    expect(result).toEqual({ hello: 'world' })
    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.pathname).toBe('/merchants/M0000/risk')
    expect(calledUrl.searchParams.get('as_of_date')).toBe('2024-01-01')
    expect(calledUrl.searchParams.get('horizon_days')).toBe('30')
  })

  it('omits undefined query params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.request('/merchants', { params: { archetype: undefined } })

    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.searchParams.has('archetype')).toBe(false)
  })

  it('throws ApiError with the backend detail message on a non-ok response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: "Unknown merchant_id: 'X'" }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiClient.request('/merchants/X')).rejects.toMatchObject({
      status: 404,
      detail: "Unknown merchant_id: 'X'",
    })
    await expect(apiClient.request('/merchants/X')).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiUnavailableError when fetch itself rejects (network/CORS failure)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )

    await expect(apiClient.request('/health')).rejects.toBeInstanceOf(ApiUnavailableError)
  })

  it('sends a POST with a JSON body and Content-Type header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) })
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.request('/merchants/M0000/simulation', {
      method: 'POST',
      body: { as_of_date: '2024-01-01', refund_rate_28d: 0.3 },
    })

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(new URL(url).pathname).toBe('/merchants/M0000/simulation')
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' })
    expect(init.body).toBe(JSON.stringify({ as_of_date: '2024-01-01', refund_rate_28d: 0.3 }))
  })

  it('a GET request omits Content-Type and body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.request('/health')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('GET')
    expect(init.body).toBeUndefined()
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })
})
