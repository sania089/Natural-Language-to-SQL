import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
export const THEME_STORAGE_KEY = 'nl-sql-theme'

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function readStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function persistTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    /* storage unavailable (private mode): theme still applies for this session */
  }
}

/** System theme by default, user toggle persisted to localStorage. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => readStoredTheme() ?? systemTheme())

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark'
      persistTheme(next)
      return next
    })
  }, [])

  return { theme, toggleTheme }
}
