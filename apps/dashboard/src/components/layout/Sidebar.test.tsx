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
        <Route path="/risk" element={<div>Risk screen</div>} />
        <Route path="/explainability" element={<div>Explainability screen</div>} />
        <Route path="/simulator" element={<div>Simulator screen</div>} />
        <Route path="/incident-response" element={<div>Incident Response screen</div>} />
        <Route path="/evidence" element={<div>Evidence screen</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

const ALL_LABELS = ['Overview', 'Risk', 'Explainability', 'Simulator', 'Incident Response', 'Evidence']

describe('Sidebar navigation', () => {
  it('every nav item is a real, clickable, enabled link — none are disabled placeholders', () => {
    renderSidebarAt('/')
    for (const label of ALL_LABELS) {
      const link = screen.getByRole('link', { name: label })
      expect(link).not.toHaveAttribute('aria-disabled')
    }
    expect(screen.queryByText('Soon')).not.toBeInTheDocument()
  })

  it('there is no Settings nav item — removed rather than left as a dead placeholder', () => {
    renderSidebarAt('/')
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })

  it('clicking Risk navigates to the risk route', async () => {
    renderSidebarAt('/')
    await userEvent.click(screen.getByRole('link', { name: 'Risk' }))
    expect(await screen.findByText('Risk screen')).toBeInTheDocument()
  })

  it('clicking Explainability navigates to the explainability route', async () => {
    renderSidebarAt('/')
    await userEvent.click(screen.getByRole('link', { name: 'Explainability' }))
    expect(await screen.findByText('Explainability screen')).toBeInTheDocument()
  })

  it('clicking Evidence navigates to the evidence route', async () => {
    renderSidebarAt('/')
    await userEvent.click(screen.getByRole('link', { name: 'Evidence' }))
    expect(await screen.findByText('Evidence screen')).toBeInTheDocument()
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
