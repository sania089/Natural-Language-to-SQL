import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axe from 'axe-core'
import { afterEach, beforeEach, vi } from 'vitest'
import App from './App'

/**
 * axe-core against the rendered app. jsdom has no layout/paint, so colour-contrast is
 * excluded here and verified separately (Lighthouse / manual) in a real browser.
 */
async function violations(container: HTMLElement): Promise<string[]> {
  const results = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false } },
  })
  return results.violations.map((v) => `${v.id}: ${v.help} (${String(v.nodes.length)} nodes)`)
}

function renderApp() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  )
}

const ANSWER = {
  request_id: 'abc',
  question: 'Top customers',
  sql: 'SELECT name, total FROM customers',
  columns: ['name', 'total'],
  rows: [
    ['Ada', 100],
    ['Bob', 50],
  ],
  row_count: 2,
  truncated: false,
  elapsed_ms: 12.4,
  warnings: [],
  repaired: false,
}

describe('accessibility (axe)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('has no violations in the empty state', async () => {
    const { container } = renderApp()
    expect(await violations(container)).toEqual([])
  })

  it('has no violations with results displayed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(ANSWER))))
    const { container } = renderApp()
    await userEvent.click(screen.getByRole('button', { name: /top 5 customers/i }))
    await screen.findByRole('region', { name: /query results/i })
    expect(await violations(container)).toEqual([])
  })

  it('has no violations in the error state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    const { container } = renderApp()
    await userEvent.type(screen.getByLabelText(/your question/i), 'anything')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))
    await screen.findByText(/can't reach the server/i)
    expect(await violations(container)).toEqual([])
  })
})
