import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MerchantSelector } from './MerchantSelector'
import * as MerchantContextModule from '@/context/MerchantContext'
import { mockMerchantList } from '@/test/fixtures'

function mockContext(overrides: Partial<ReturnType<typeof MerchantContextModule.useMerchantContext>> = {}) {
  vi.spyOn(MerchantContextModule, 'useMerchantContext').mockReturnValue({
    merchants: mockMerchantList.merchants,
    merchantsLoading: false,
    merchantsError: null,
    selectedMerchantId: 'M0001',
    selectMerchant: vi.fn(),
    ...overrides,
  })
}

describe('MerchantSelector', () => {
  it('lists every real merchant returned by the API', () => {
    mockContext()
    render(<MerchantSelector />)
    expect(screen.getByRole('combobox', { name: /merchant/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /M0001 — SaaS/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /M0002 — Travel/ })).toBeInTheDocument()
  })

  it('calls selectMerchant with the chosen merchant id', async () => {
    const selectMerchant = vi.fn()
    mockContext({ selectMerchant })
    render(<MerchantSelector />)

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /merchant/i }), 'M0002')

    expect(selectMerchant).toHaveBeenCalledWith('M0002')
  })

  it('shows a message when the merchant list fails to load', () => {
    mockContext({ merchantsError: new Error('boom'), merchants: [] })
    render(<MerchantSelector />)
    expect(screen.getByText(/unavailable/i)).toBeInTheDocument()
  })
})
