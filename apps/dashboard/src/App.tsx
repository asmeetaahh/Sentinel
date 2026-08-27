import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/layout/AppShell'
import { MerchantProvider } from '@/context/MerchantContext'
import { EvidencePage } from '@/pages/EvidencePage'
import { ExplainabilityPage } from '@/pages/ExplainabilityPage'
import { IncidentResponsePage } from '@/pages/IncidentResponsePage'
import { OverviewPage } from '@/pages/OverviewPage'
import { RiskPage } from '@/pages/RiskPage'
import { SimulatorPage } from '@/pages/SimulatorPage'

export default function App() {
  return (
    <MerchantProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/explainability" element={<ExplainabilityPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/incident-response" element={<IncidentResponsePage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </MerchantProvider>
  )
}
