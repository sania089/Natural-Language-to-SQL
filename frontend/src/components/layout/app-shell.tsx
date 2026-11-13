import { Database } from 'lucide-react'
import type { ReactNode } from 'react'
import { ThemeToggle } from '@/components/ui/theme-toggle'

export interface AppShellProps {
  children: ReactNode
  /** Slot for header actions, e.g. the schema button (Day 5). */
  actions?: ReactNode
}

export function AppShell({ children, actions }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-fg"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4">
          <div className="flex items-center gap-2 font-semibold">
            <Database className="h-5 w-5 text-accent" aria-hidden="true" />
            <span>NL → SQL</span>
          </div>
          <div className="flex items-center gap-2">
            {actions}
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
      <footer className="border-t border-border py-6 text-center text-sm text-muted">
        Read-only queries · Generated SQL is always shown
      </footer>
    </div>
  )
}
