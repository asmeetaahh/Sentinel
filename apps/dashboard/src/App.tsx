import { AppShell } from '@/components/layout/AppShell'
import { MerchantProvider } from '@/context/MerchantContext'
import { OverviewPage } from '@/pages/OverviewPage'

export default function App() {
  return (
    <MerchantProvider>
      <AppShell>
        <OverviewPage />
      </AppShell>
    </MerchantProvider>
  )
}
