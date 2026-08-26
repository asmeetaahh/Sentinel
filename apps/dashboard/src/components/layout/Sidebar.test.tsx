import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { Sidebar } from './Sidebar'

function renderSidebarAt(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar />
      <Routes>
        <Route path="/" element={<div>Overview screen</div>} />
        <Route path="/simulator" element={<div>Simulator screen</div>} />
        <Route path="/incident-response" element={<div>Incident Response screen</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Sidebar navigation', () => {
  it('Overview, Simulator, and Incident Response are real, clickable links', () => {
    renderSidebarAt('/')
    for (const label of ['Overview', 'Simulator', 'Incident Response']) {
      const link = screen.getByRole('link', { name: label })
      expect(link).not.toHaveAttribute('aria-disabled')
    }
  })

  it('Risk, Explainability, Evidence, and Settings remain disabled placeholders', () => {
    renderSidebarAt('/')
    for (const label of ['Risk', 'Explainability', 'Evidence', 'Settings']) {
      const button = screen.getByTitle(`${label} — coming soon`)
      expect(button.tagName).toBe('BUTTON')
      expect(button).toBeDisabled()
      expect(button).toHaveAttribute('aria-disabled', 'true')
      expect(button).toHaveTextContent('Soon')
    }
  })

  it('clicking Incident Response navigates to the incident-response route', async () => {
    renderSidebarAt('/')
    await userEvent.click(screen.getByRole('link', { name: 'Incident Response' }))
    expect(await screen.findByText('Incident Response screen')).toBeInTheDocument()
  })

  it('marks the current route as active via aria-current', () => {
    renderSidebarAt('/incident-response')
    expect(screen.getByRole('link', { name: 'Incident Response' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Overview' })).not.toHaveAttribute('aria-current')
  })
})
