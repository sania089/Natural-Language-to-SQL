import { lazy, Suspense, useSyncExternalStore } from 'react'
import { AppShell } from '@/components/layout/app-shell'
import { SchemaDialog } from '@/components/schema-dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { ToastProvider } from '@/components/ui/toast'
import { TooltipProvider } from '@/components/ui/tooltip'

import Home from '@/pages/home'

const ComponentsDemo = lazy(() => import('@/pages/components-demo'))

const DEMO_HASH = '#/components'

function subscribeToHash(callback: () => void): () => void {
  window.addEventListener('hashchange', callback)
  return () => {
    window.removeEventListener('hashchange', callback)
  }
}

export default function App() {
  const hash = useSyncExternalStore(subscribeToHash, () => window.location.hash)
  return (
    <TooltipProvider delayDuration={200}>
      <ToastProvider>
        <AppShell actions={<SchemaDialog />}>
          {hash === DEMO_HASH ? (
            <Suspense fallback={<Skeleton className="h-64 w-full" />}>
              <ComponentsDemo />
            </Suspense>
          ) : (
            <Home />
          )}
        </AppShell>
      </ToastProvider>
    </TooltipProvider>
  )
}
