import { X } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent,
  type ReactNode,
} from 'react'
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
const EXIT_MS = 450
const SWIPE_DISMISS_PX = 80
let nextId = 0

const VARIANT_CLASS: Record<ToastVariant, string> = {
  info: 'border-border',
  success: 'border-success/40',
  error: 'border-danger/40',
}

interface ToastCardProps {
  item: ToastItem
  onRemove: (id: number) => void
}

/** One toast: auto-dismisses, slides out to the right, and can be swiped right to dismiss. */
function ToastCard({ item, onRemove }: ToastCardProps) {
  const [dragX, setDragX] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [leaving, setLeaving] = useState(false)
  const startX = useRef(0)

  const leave = useCallback(() => {
    setLeaving(true)
    setTimeout(() => {
      onRemove(item.id)
    }, EXIT_MS)
  }, [item.id, onRemove])

  useEffect(() => {
    const timer = setTimeout(leave, DISMISS_MS)
    return () => {
      clearTimeout(timer)
    }
  }, [leave])

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest('button')) return
    startX.current = event.clientX
    setDragging(true)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (dragging) setDragX(Math.max(0, event.clientX - startX.current))
  }

  function onPointerUp() {
    if (!dragging) return
    setDragging(false)
    if (dragX > SWIPE_DISMISS_PX) leave()
    else setDragX(0)
  }

  const style = leaving
    ? { transform: 'translateX(120%)', opacity: 0 }
    : { transform: `translateX(${String(dragX)}px)`, opacity: 1 - Math.min(dragX / 240, 0.6) }

  return (
    <div
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      style={{ ...style, touchAction: 'pan-y' }}
      className={cn(
        'flex animate-(--animate-slide-up) cursor-grab items-center justify-between gap-3 rounded-lg border bg-surface p-3 text-sm shadow-(--shadow-md) select-none',
        !dragging && 'transition-[transform,opacity] duration-[450ms] ease-out',
        VARIANT_CLASS[item.variant],
      )}
    >
      <span>{item.message}</span>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={leave}
        className="rounded p-1 text-muted hover:text-fg"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])

  const toast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = nextId++
    setItems((current) => [...current, { id, message, variant }])
  }, [])

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
          <ToastCard key={item.id} item={item} onRemove={dismiss} />
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
