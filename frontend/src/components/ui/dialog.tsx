import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger

export interface DialogContentProps {
  title: string
  description: string
  children: ReactNode
}

/** Focus-trapped modal; Esc and the close button dismiss it. */
export function DialogContent({ title, description, children }: DialogContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 animate-(--animate-fade-in) bg-black/50" />
      <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 animate-(--animate-fade-in) flex-col rounded-lg border border-border bg-surface shadow-(--shadow-lg)">
        <div className="flex items-start justify-between gap-4 border-b border-border p-4">
          <div>
            <DialogPrimitive.Title className="text-lg font-semibold">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Description className="mt-1 text-sm text-muted">
              {description}
            </DialogPrimitive.Description>
          </div>
          <DialogPrimitive.Close
            aria-label="Close"
            className="rounded-md p-1 text-muted transition-colors duration-(--duration-fast) hover:bg-surface-2 hover:text-fg"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </DialogPrimitive.Close>
        </div>
        <div className="overflow-auto p-4">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
