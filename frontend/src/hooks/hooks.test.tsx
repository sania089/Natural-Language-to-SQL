import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import { THEME_STORAGE_KEY, useTheme } from './useTheme'
import { useCopyToClipboard } from './useCopyToClipboard'

function mockSystemDark(dark: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi
      .fn()
      .mockReturnValue({ matches: dark, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
  )
}

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.theme
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('defaults to the system theme and applies it to <html>', () => {
    mockSystemDark(true)
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('prefers a stored theme over the system theme', () => {
    mockSystemDark(true)
    localStorage.setItem(THEME_STORAGE_KEY, 'light')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
  })

  it('toggles and persists the choice', () => {
    mockSystemDark(false)
    const { result } = renderHook(() => useTheme())
    act(() => {
      result.current.toggleTheme()
    })
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })
})

describe('useCopyToClipboard', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('copies text, flags copied, then resets', async () => {
    vi.useFakeTimers()
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const { result } = renderHook(() => useCopyToClipboard())

    let ok = false
    await act(async () => {
      ok = await result.current.copy('SELECT 1')
    })
    expect(ok).toBe(true)
    expect(writeText).toHaveBeenCalledWith('SELECT 1')
    expect(result.current.copied).toBe(true)

    act(() => {
      vi.advanceTimersByTime(2100)
    })
    expect(result.current.copied).toBe(false)
  })

  it('returns false when the clipboard is unavailable', async () => {
    vi.stubGlobal('navigator', {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    const { result } = renderHook(() => useCopyToClipboard())
    let ok = true
    await act(async () => {
      ok = await result.current.copy('x')
    })
    expect(ok).toBe(false)
    expect(result.current.copied).toBe(false)
  })
})
