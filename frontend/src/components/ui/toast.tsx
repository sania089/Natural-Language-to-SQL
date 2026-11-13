import { X } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type ToastVariant = 'info' | 'success' | 'error'

interface ToastItem {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastApi {
  toast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastApi | null>(null)
const DISMISS_MS = 4000
let nextId = 0

const VARIANT_CLASS: Record<ToastVariant, string> = {
  info: 'border-border',
  success: 'border-success/40',
  error: 'border-danger/40',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])

  const toast = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = nextId++
      setItems((current) => [...current, { id, message, variant }])
      setTimeout(() => {
        dismiss(id)
      }, DISMISS_MS)
    },
    [dismiss],
  )

  const api = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2"
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              'flex animate-(--animate-slide-up) items-center justify-between gap-3 rounded-lg border bg-surface p-3 text-sm shadow-(--shadow-md)',
              VARIANT_CLASS[item.variant],
            )}
          >
            <span>{item.message}</span>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => {
                dismiss(item.id)
              }}
              className="rounded p-1 text-muted hover:text-fg"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
