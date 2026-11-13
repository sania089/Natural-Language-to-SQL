import { useCallback, useEffect, useRef, useState } from 'react'

const RESET_MS = 2000

/** Copies text to the clipboard; `copied` is true briefly afterwards. */
export function useCopyToClipboard() {
  const [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>()

  useEffect(
    () => () => {
      clearTimeout(timer.current)
    },
    [],
  )

  const copy = useCallback(async (text: string): Promise<boolean> => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      return false
    }
    setCopied(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      setCopied(false)
    }, RESET_MS)
    return true
  }, [])

  return { copied, copy }
}
