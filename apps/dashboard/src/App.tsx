import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/layout/AppShell'
import { MerchantProvider } from '@/context/MerchantContext'
import { OverviewPage } from '@/pages/OverviewPage'
import { SimulatorPage } from '@/pages/SimulatorPage'

export default function App() {
  return (
    <MerchantProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </MerchantProvider>
  )
}
