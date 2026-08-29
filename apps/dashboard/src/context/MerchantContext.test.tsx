import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MerchantSelector } from '@/components/common/MerchantSelector'
import * as endpoints from '@/api/endpoints'
import { mockMerchantList } from '@/test/fixtures'

import { MerchantProvider } from './MerchantContext'

const STORAGE_KEY = 'sentinel:selectedMerchantId'

function renderSelector() {
  return render(
    <MerchantProvider>
      <MerchantSelector />
    </MerchantProvider>,
  )
}

describe('MerchantContext — selected-merchant persistence', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue(mockMerchantList)
  })

  it('restores the stored merchant id when it exists in the real fetched merchant list', async () => {
    // mockMerchantList (see @/test/fixtures) contains M0001 and M0002 — pick
    // the one that is NOT first, so a successful restore is distinguishable
    // from the ordinary "default to first merchant" fallback.
    window.localStorage.setItem(STORAGE_KEY, 'M0002')

    renderSelector()

    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('M0002'))
  })

  it('falls back to the first returned merchant when the stored id is not in the real fetched list', async () => {
    window.localStorage.setItem(STORAGE_KEY, 'M9999') // not in mockMerchantList

    renderSelector()

    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('M0001'))
  })

  it('falls back to the first returned merchant when nothing is stored', async () => {
    renderSelector()

    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('M0001'))
  })

  it('never restores a hardcoded id — an empty real merchant list never gets a stored selection applied', async () => {
    window.localStorage.setItem(STORAGE_KEY, 'M0002')
    vi.spyOn(endpoints, 'listMerchants').mockResolvedValue({ count: 0, merchants: [] })

    renderSelector()

    await waitFor(() => expect(screen.getByText(/no merchants available/i)).toBeInTheDocument())
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('persists the new merchant id to localStorage when the user changes the selection', async () => {
    const user = userEvent.setup()
    renderSelector()

    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('M0001'))

    await user.selectOptions(screen.getByRole('combobox'), 'M0002')

    expect(screen.getByRole('combobox')).toHaveValue('M0002')
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('M0002')
  })

  it('preserves the existing loading state while the merchant list request is pending', () => {
    vi.spyOn(endpoints, 'listMerchants').mockReturnValue(new Promise(() => {})) // never resolves

    renderSelector()

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('preserves the existing error state when the merchant list request fails', async () => {
    vi.spyOn(endpoints, 'listMerchants').mockRejectedValue(new Error('backend unreachable'))

    renderSelector()

    await waitFor(() => expect(screen.getByText(/merchant list unavailable/i)).toBeInTheDocument())
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })
})
