import { cva, type VariantProps } from 'class-variance-authority'
import { AlertTriangle, CircleCheck, Info, OctagonAlert, type LucideIcon } from 'lucide-react'
import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

const alertVariants = cva('flex gap-3 rounded-lg border p-4 text-sm', {
  variants: {
    variant: {
      info: 'border-accent/30 bg-accent-soft text-fg',
      success: 'border-success/30 bg-success-soft text-fg',
      warning: 'border-warning/30 bg-warning-soft text-fg',
      error: 'border-danger/30 bg-danger-soft text-fg',
    },
  },
  defaultVariants: { variant: 'info' },
})

type Variant = NonNullable<VariantProps<typeof alertVariants>['variant']>

const ICONS: Record<Variant, { icon: LucideIcon; color: string }> = {
  info: { icon: Info, color: 'text-accent' },
  success: { icon: CircleCheck, color: 'text-success' },
  warning: { icon: AlertTriangle, color: 'text-warning' },
  error: { icon: OctagonAlert, color: 'text-danger' },
}

export interface AlertProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  variant?: Variant
  title?: ReactNode
  /** Optional action, e.g. a retry Button. */
  action?: ReactNode
}

export function Alert({
  variant = 'info',
  title,
  action,
  className,
  children,
  ...props
}: AlertProps) {
  const { icon: Icon, color } = ICONS[variant]
  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', color)} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cn(title && 'mt-1', 'text-muted')}>{children}</div>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
