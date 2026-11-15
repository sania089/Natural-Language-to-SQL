import { TriangleAlert } from 'lucide-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'

interface ErrorBoundaryState {
  failed: boolean
}

/** Last-resort fallback so a render crash shows a recoverable screen, never a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled UI error', error, info.componentStack)
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return (
      <EmptyState
        icon={TriangleAlert}
        title="Something went wrong"
        description="The page hit an unexpected error. Reloading usually fixes it."
        action={
          <Button
            onClick={() => {
              window.location.reload()
            }}
          >
            Reload
          </Button>
        }
      />
    )
  }
}
