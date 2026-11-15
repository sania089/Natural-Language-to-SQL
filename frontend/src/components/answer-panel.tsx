import type { AskResponse } from '@/lib/api'
import { CodeBlock } from './code-block'
import { DataTable } from './data-table'
import { Alert } from './ui/alert'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Skeleton } from './ui/skeleton'

/** Loading state: mirrors the answer layout so nothing shifts when results arrive. */
export function AnswerSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Generating answer">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

export function resultSummary(answer: AskResponse): string {
  const rows = `${String(answer.row_count)} ${answer.row_count === 1 ? 'row' : 'rows'}`
  return `Query returned ${rows} in ${String(Math.round(answer.elapsed_ms))} milliseconds.`
}

export function AnswerPanel({ answer }: { answer: AskResponse }) {
  return (
    <div className="space-y-4">
      {/* Always mounted per answer so screen readers announce each new result. */}
      <p className="sr-only" role="status" aria-live="polite">
        {resultSummary(answer)}
      </p>
      <Card>
        <CardHeader>
          <CardTitle>Generated SQL</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success">Validated · read-only</Badge>
            {answer.repaired && <Badge variant="warning">Auto-repaired</Badge>}
          </div>
        </CardHeader>
        <CardContent>
          <CodeBlock code={answer.sql} label="Generated SQL" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="accent">
              {answer.row_count.toLocaleString('en-US')} {answer.row_count === 1 ? 'row' : 'rows'}
            </Badge>
            <Badge>{Math.round(answer.elapsed_ms)} ms</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {answer.truncated && (
            <Alert variant="warning">Results were capped; only the first rows are shown.</Alert>
          )}
          {answer.warnings.map((warning) => (
            <Alert key={warning} variant="info">
              {warning}
            </Alert>
          ))}
          <DataTable columns={answer.columns} rows={answer.rows} caption="Query results" />
        </CardContent>
      </Card>
    </div>
  )
}
