import { SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'

export default function NotFound() {
  return (
    <EmptyState
      icon={SearchX}
      title="Page not found"
      description="That page doesn't exist."
      action={
        <Button
          onClick={() => {
            window.location.hash = ''
          }}
        >
          Back to the app
        </Button>
      }
    />
  )
}
