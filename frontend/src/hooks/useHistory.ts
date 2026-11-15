import { useCallback, useState } from 'react'
import type { AskResponse } from '@/lib/api'

export const HISTORY_STORAGE_KEY = 'nl-sql:history'
export const MAX_HISTORY = 10
/** Stored rows are trimmed so localStorage stays small; the full answer is kept in memory. */
const MAX_STORED_ROWS = 50

function load(): AskResponse[] {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as AskResponse[]) : []
  } catch {
    return []
  }
}

function save(items: AskResponse[]): void {
  try {
    const trimmed = items.map((a) => ({ ...a, rows: a.rows.slice(0, MAX_STORED_ROWS) }))
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(trimmed))
  } catch {
    /* storage full or unavailable: history is a convenience, not critical */
  }
}

/** Recent answers, newest first, de-duplicated by question and persisted to localStorage. */
export function useHistory() {
  const [items, setItems] = useState<AskResponse[]>(load)

  const add = useCallback((answer: AskResponse) => {
    setItems((current) => {
      const next = [answer, ...current.filter((a) => a.question !== answer.question)].slice(
        0,
        MAX_HISTORY,
      )
      save(next)
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setItems([])
    save([])
  }, [])

  return { items, add, clear }
}
