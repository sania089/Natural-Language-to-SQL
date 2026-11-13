import { lazy, Suspense, useSyncExternalStore } from 'react'
import { AppShell } from '@/components/layout/app-shell'
import { Skeleton } from '@/components/ui/skeleton'
import { ToastProvider } from '@/components/ui/toast'
import { TooltipProvider } from '@/components/ui/tooltip'

const ComponentsDemo = lazy(() => import('@/pages/components-demo'))

const DEMO_HASH = '#/components'

function subscribeToHash(callback: () => void): () => void {
  window.addEventListener('hashchange', callback)
  return () => {
    window.removeEventListener('hashchange', callback)
  }
}

function Home() {
  return (
    <div>
      <h1 className="text-3xl font-semibold">Natural Language to SQL</h1>
      <p className="mt-2 text-muted">Ask questions about your data in plain English.</p>
    </div>
  )
}

export default function App() {
  const hash = useSyncExternalStore(subscribeToHash, () => window.location.hash)
  return (
    <TooltipProvider delayDuration={200}>
      <ToastProvider>
        <AppShell>
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
