import { Send } from 'lucide-react'
import { useEffect, useId, useRef, type FormEvent, type KeyboardEvent } from 'react'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'

export const MAX_QUESTION_LENGTH = 500

export interface QuestionInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (question: string) => void
  loading?: boolean
  maxLength?: number
}

/** Autosizing textarea. Ctrl/Cmd+Enter submits; Enter alone inserts a newline. */
export function QuestionInput({
  value,
  onChange,
  onSubmit,
  loading = false,
  maxLength = MAX_QUESTION_LENGTH,
}: QuestionInputProps) {
  const id = useId()
  const ref = useRef<HTMLTextAreaElement>(null)
  const trimmed = value.trim()
  const canSubmit = trimmed.length > 0 && !loading

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${String(el.scrollHeight)}px`
  }, [value])

  const submit = () => {
    if (canSubmit) onSubmit(trimmed)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      submit()
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const nearLimit = value.length > maxLength * 0.9

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor={id} className="sr-only">
        Your question
      </label>
      <textarea
        id={id}
        ref={ref}
        rows={2}
        value={value}
        maxLength={maxLength}
        onChange={(e) => {
          onChange(e.target.value)
        }}
        onKeyDown={handleKeyDown}
        placeholder="e.g. Who are our top 5 customers by total spend?"
        className="max-h-60 w-full resize-none rounded-lg border border-border bg-surface p-4 text-base shadow-(--shadow-sm) placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      />
      <div className="flex items-center justify-between gap-4">
        <span
          className={cn('text-xs tabular-nums text-muted', nearLimit && 'text-warning')}
          aria-live="polite"
        >
          {value.length} / {maxLength}
        </span>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-muted sm:inline">Ctrl/⌘ + Enter</span>
          <Button type="submit" loading={loading} disabled={!canSubmit}>
            {!loading && <Send className="h-4 w-4" aria-hidden="true" />}
            {loading ? 'Thinking…' : 'Ask'}
          </Button>
        </div>
      </div>
    </form>
  )
}
