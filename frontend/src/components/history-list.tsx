import { History, Trash2 } from 'lucide-react'
import type { AskResponse } from '@/lib/api'
import { Button } from './ui/button'

export interface HistoryListProps {
  items: AskResponse[]
  onOpen: (answer: AskResponse) => void
  onClear: () => void
}

export function HistoryList({ items, onOpen, onClear }: HistoryListProps) {
  if (items.length === 0) return null
  return (
    <section aria-labelledby="history-heading" className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 id="history-heading" className="flex items-center gap-2 text-sm font-semibold">
          <History className="h-4 w-4" aria-hidden="true" />
          Recent questions
        </h2>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <Trash2 className="h-4 w-4" aria-hidden="true" />
          Clear
        </Button>
      </div>
      <ul className="flex flex-wrap gap-2">
        {items.map((item) => (
          <li key={item.question}>
            <Button
              variant="secondary"
              size="sm"
              className="max-w-xs"
              onClick={() => {
                onOpen(item)
              }}
            >
              <span className="truncate">{item.question}</span>
            </Button>
          </li>
        ))}
      </ul>
    </section>
  )
}
