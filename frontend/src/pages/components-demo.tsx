import { Database, SearchX } from 'lucide-react'
import { CodeBlock } from '@/components/code-block'
import { DataTable, type Cell } from '@/components/data-table'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button, IconButton } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { Tooltip } from '@/components/ui/tooltip'

const SAMPLE_SQL = `SELECT c.name, SUM(oi.quantity * oi.unit_price) AS total_spend
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id
ORDER BY total_spend DESC
LIMIT 5;`

const COLUMNS = ['name', 'orders', 'total_spend']
const ROWS: Cell[][] = [
  ['Ava Patel', 12, 4820.5],
  ['Liam Chen', 9, 3911.25],
  ['Noah Garcia', 7, 2204],
  ['Mia Johnson', 5, null],
  ['Zoe Williams', 3, 640.75],
]
const MANY_ROWS: Cell[][] = Array.from({ length: 1000 }, (_, i) => [
  `Customer ${String(i + 1)}`,
  i % 17,
  i * 3.5,
])

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  )
}

/** Storybook-lite page (route: #/components) to eyeball every primitive and state in both themes. */
export default function ComponentsDemo() {
  const { toast } = useToast()
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Component gallery</h1>
        <p className="mt-1 text-muted">
          Every primitive and state. Toggle the theme in the header.
        </p>
      </div>

      <Section title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button loading>Loading</Button>
          <Button disabled>Disabled</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Tooltip content="Icon button with tooltip">
            <IconButton label="Database">
              <Database className="h-5 w-5" aria-hidden="true" />
            </IconButton>
          </Tooltip>
        </div>
      </Section>

      <Section title="Badges">
        <div className="flex flex-wrap gap-2">
          <Badge>Neutral</Badge>
          <Badge variant="accent">Accent</Badge>
          <Badge variant="success">Validated</Badge>
          <Badge variant="warning">Row limit applied</Badge>
          <Badge variant="danger">Rejected</Badge>
        </div>
      </Section>

      <Section title="Alerts">
        <Alert variant="info" title="Info">
          Only SELECT queries are allowed.
        </Alert>
        <Alert variant="success" title="Success">
          Query validated and executed.
        </Alert>
        <Alert variant="warning" title="Warning">
          Results were capped at 500 rows.
        </Alert>
        <Alert
          variant="error"
          title="Error"
          action={
            <Button size="sm" variant="secondary">
              Retry
            </Button>
          }
        >
          The language model is unavailable.
        </Alert>
      </Section>

      <Section title="Toast & Dialog">
        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            onClick={() => {
              toast('Saved', 'success')
            }}
          >
            Success toast
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              toast('Something failed', 'error')
            }}
          >
            Error toast
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="secondary">Open dialog</Button>
            </DialogTrigger>
            <DialogContent title="Dialog" description="Focus is trapped; Esc closes it.">
              <p className="text-sm">Dialog body content.</p>
            </DialogContent>
          </Dialog>
        </div>
      </Section>

      <Section title="Skeleton (loading)">
        <div className="space-y-2" role="status" aria-label="Loading">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </Section>

      <Section title="Empty state">
        <EmptyState
          icon={SearchX}
          title="Ask your first question"
          description="Try an example below or type your own question."
        />
      </Section>

      <Section title="CodeBlock">
        <CodeBlock code={SAMPLE_SQL} label="Generated SQL" />
      </Section>

      <Section title="DataTable">
        <DataTable columns={COLUMNS} rows={ROWS} caption="Top customers by spend" />
        <h3 className="text-sm font-semibold text-muted">Zero rows</h3>
        <DataTable columns={COLUMNS} rows={[]} caption="Empty results" />
        <h3 className="text-sm font-semibold text-muted">1,000 rows (virtualized)</h3>
        <DataTable columns={COLUMNS} rows={MANY_ROWS} caption="Large result set" maxHeight={320} />
      </Section>
    </div>
  )
}
