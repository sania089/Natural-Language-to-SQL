import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { memo, useMemo, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { EmptyState } from './ui/empty-state'

export type Cell = string | number | boolean | null

export interface DataTableProps {
  columns: string[]
  rows: Cell[][]
  /** Accessible table name, e.g. "Query results". */
  caption: string
  /** Rows above this count are virtualized. */
  virtualizeAfter?: number
  maxHeight?: number
  className?: string
}

type SortState = { column: number; direction: 'asc' | 'desc' } | null

const ROW_HEIGHT = 40
const DEFAULT_VIRTUALIZE_AFTER = 200

export function formatCell(value: Cell): string {
  if (value === null) return 'NULL'
  return typeof value === 'number' ? value.toLocaleString('en-US') : String(value)
}

function compareCells(a: Cell, b: Cell): number {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

function sortRows(rows: Cell[][], sort: SortState): Cell[][] {
  if (!sort) return rows
  const factor = sort.direction === 'asc' ? 1 : -1
  return [...rows].sort((rowA, rowB) => {
    const a = rowA[sort.column] ?? null
    const b = rowB[sort.column] ?? null
    if (a === b) return 0
    if (a === null) return 1 // nulls always last, in both directions
    if (b === null) return -1
    return factor * compareCells(a, b)
  })
}

/** Numeric columns are detected from the first non-null value and right-aligned. */
function numericColumns(columns: string[], rows: Cell[][]): boolean[] {
  return columns.map((_, index) => {
    const first = rows.find((row) => row[index] != null)?.[index]
    return typeof first === 'number'
  })
}

const TableRow = memo(function TableRow({
  row,
  numeric,
  index,
  style,
}: {
  row: Cell[]
  numeric: boolean[]
  index: number
  style?: React.CSSProperties
}) {
  return (
    <tr
      style={style}
      className={cn('flex w-full', index % 2 === 1 && 'bg-surface-2/60')}
      aria-rowindex={index + 2}
    >
      {row.map((value, col) => (
        <td
          key={col}
          className={cn(
            'min-w-32 flex-1 truncate px-4 py-2 text-sm',
            numeric[col] && 'text-right tabular-nums',
            value === null && 'italic text-muted',
          )}
          title={formatCell(value)}
        >
          {formatCell(value)}
        </td>
      ))}
    </tr>
  )
})

export function DataTable({
  columns,
  rows,
  caption,
  virtualizeAfter = DEFAULT_VIRTUALIZE_AFTER,
  maxHeight = 480,
  className,
}: DataTableProps) {
  const [sort, setSort] = useState<SortState>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const sorted = useMemo(() => sortRows(rows, sort), [rows, sort])
  const numeric = useMemo(() => numericColumns(columns, rows), [columns, rows])
  const virtual = sorted.length > virtualizeAfter

  const virtualizer = useVirtualizer({
    count: sorted.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
    enabled: virtual,
  })

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No rows returned"
        description="The query ran successfully but matched no data."
      />
    )
  }

  const toggleSort = (column: number) => {
    setSort((current) => {
      if (current?.column !== column) return { column, direction: 'asc' }
      return current.direction === 'asc' ? { column, direction: 'desc' } : null
    })
  }

  const ariaSort = (column: number) =>
    sort?.column === column ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'

  return (
    <div
      ref={scrollRef}
      role="region"
      aria-label={caption}
      tabIndex={0}
      style={{ maxHeight }}
      className={cn('overflow-auto rounded-lg border border-border', className)}
    >
      <table className="w-full min-w-max border-collapse" aria-rowcount={sorted.length + 1}>
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 z-10 bg-surface shadow-[0_1px_0_var(--border)]">
          <tr className="flex w-full" aria-rowindex={1}>
            {columns.map((name, col) => {
              const Icon =
                sort?.column === col
                  ? sort.direction === 'asc'
                    ? ArrowUp
                    : ArrowDown
                  : ChevronsUpDown
              return (
                <th
                  key={name}
                  scope="col"
                  aria-sort={ariaSort(col)}
                  className={cn(
                    'min-w-32 flex-1 text-sm font-semibold',
                    numeric[col] && 'text-right',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => {
                      toggleSort(col)
                    }}
                    className={cn(
                      'inline-flex w-full items-center gap-1 px-4 py-2 transition-colors duration-(--duration-fast) hover:bg-surface-2',
                      numeric[col] ? 'justify-end' : 'justify-start',
                    )}
                  >
                    {name}
                    <Icon className="h-3.5 w-3.5 text-muted" aria-hidden="true" />
                  </button>
                </th>
              )
            })}
          </tr>
        </thead>
        {virtual ? (
          <tbody className="relative block" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((item) => (
              <TableRow
                key={item.index}
                row={sorted[item.index] ?? []}
                numeric={numeric}
                index={item.index}
                style={{
                  position: 'absolute',
                  top: 0,
                  height: item.size,
                  transform: `translateY(${String(item.start)}px)`,
                }}
              />
            ))}
          </tbody>
        ) : (
          <tbody>
            {sorted.map((row, index) => (
              <TableRow key={index} row={row} numeric={numeric} index={index} />
            ))}
          </tbody>
        )}
      </table>
    </div>
  )
}
