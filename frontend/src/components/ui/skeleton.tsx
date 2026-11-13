import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

/** Decorative loading placeholder; announce loading state on the container instead. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn('animate-(--animate-shimmer) rounded-md bg-surface-2', className)}
      {...props}
    />
  )
}
