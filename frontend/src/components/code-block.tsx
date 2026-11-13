import { Check, Copy } from 'lucide-react'
import { memo, useEffect, useState } from 'react'
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard'
import { highlightSql } from '@/lib/highlight'
import { cn } from '@/lib/utils'
import { IconButton } from './ui/button'
import { useToast } from './ui/toast'

export interface CodeBlockProps {
  code: string
  /** Accessible name for the code region, e.g. "Generated SQL". */
  label?: string
  className?: string
}

/** SQL block with lazy syntax highlighting and a copy button. Plain text until Shiki loads. */
export const CodeBlock = memo(function CodeBlock({
  code,
  label = 'SQL code',
  className,
}: CodeBlockProps) {
  const [html, setHtml] = useState<string | null>(null)
  const { copied, copy } = useCopyToClipboard()
  const { toast } = useToast()

  useEffect(() => {
    let cancelled = false
    setHtml(null)
    highlightSql(code)
      .then((result) => {
        if (!cancelled) setHtml(result)
      })
      .catch(() => {
        /* highlighting is cosmetic: keep the plain-text fallback */
      })
    return () => {
      cancelled = true
    }
  }, [code])

  const handleCopy = async () => {
    const ok = await copy(code)
    toast(ok ? 'SQL copied to clipboard' : 'Could not copy to clipboard', ok ? 'success' : 'error')
  }

  return (
    <div className={cn('relative rounded-lg border border-border bg-surface-2', className)}>
      <IconButton
        label={copied ? 'Copied' : 'Copy SQL'}
        onClick={() => void handleCopy()}
        className="absolute right-2 top-2 h-8 w-8"
      >
        {copied ? (
          <Check className="h-4 w-4 text-success" aria-hidden="true" />
        ) : (
          <Copy className="h-4 w-4" aria-hidden="true" />
        )}
      </IconButton>
      <div
        role="region"
        aria-label={label}
        tabIndex={0}
        className="overflow-x-auto p-4 pr-12 font-mono text-sm leading-6"
      >
        {html ? (
          <div className="shiki-wrap" dangerouslySetInnerHTML={{ __html: html }} />
        ) : (
          <pre className="whitespace-pre">{code}</pre>
        )}
      </div>
    </div>
  )
})
