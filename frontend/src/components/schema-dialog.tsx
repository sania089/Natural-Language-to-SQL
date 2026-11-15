import { Table2 } from 'lucide-react'
import { useState } from 'react'
import { useSchema } from '@/hooks/useSchema'
import type { TableInfo } from '@/lib/api'
import { DataTable } from './data-table'
import { Button } from './ui/button'
import { Alert } from './ui/alert'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Dialog, DialogContent, DialogTrigger } from './ui/dialog'
import { Skeleton } from './ui/skeleton'

const COLUMNS = ['Column', 'Type', 'Key']

function tableRows(table: TableInfo) {
  return table.columns.map((col) => {
    const fk = table.foreign_keys.find((f) => f.column === col.name)
    const key = col.primary_key ? 'PK' : fk ? `FK → ${fk.ref_table}.${fk.ref_column}` : ''
    return [col.name, col.type || '—', key]
  })
}

function SchemaBody() {
  const { data, isPending, isError, refetch } = useSchema()

  if (isPending) return <Skeleton className="h-48 w-full" />
  if (isError) {
    return (
      <Alert
        variant="error"
        title="Could not load the schema"
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void refetch()
            }}
          >
            Retry
          </Button>
        }
      />
    )
  }
  return (
    <div className="space-y-4">
      {data.tables.map((table) => (
        <Card key={table.name}>
          <CardHeader>
            <CardTitle className="font-mono">{table.name}</CardTitle>
            <Badge>{table.columns.length} columns</Badge>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={COLUMNS}
              rows={tableRows(table)}
              caption={`Columns of ${table.name}`}
              maxHeight={280}
            />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

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
          <SchemaBody />
        </DialogContent>
      )}
    </Dialog>
  )
}
