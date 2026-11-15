import { Table2 } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogTrigger } from './ui/dialog'
import { Skeleton } from './ui/skeleton'

// Loaded on first open: keeps the schema table/cards out of the initial bundle.
const SchemaBody = lazy(() => import('./schema-body'))

/** Header button + modal. The schema is only fetched once the dialog first opens. */
export function SchemaDialog() {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Table2 className="h-4 w-4" aria-hidden="true" />
          Schema
        </Button>
      </DialogTrigger>
      {open && (
        <DialogContent
          title="Database schema"
          description="Tables and columns you can ask questions about."
        >
          <Suspense fallback={<Skeleton className="h-48 w-full" />}>
            <SchemaBody />
          </Suspense>
        </DialogContent>
      )}
    </Dialog>
  )
}
