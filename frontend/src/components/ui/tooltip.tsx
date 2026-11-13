import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import type { ReactNode } from 'react'

export const TooltipProvider = TooltipPrimitive.Provider

export interface TooltipProps {
  content: ReactNode
  children: ReactNode
}

/** Wraps a focusable trigger; shows on hover and keyboard focus. */
export function Tooltip({ content, children }: TooltipProps) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          sideOffset={6}
          className="z-50 animate-(--animate-fade-in) rounded-md bg-fg px-2 py-1 text-xs text-bg shadow-(--shadow-md)"
        >
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}
