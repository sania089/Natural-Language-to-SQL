import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, vi } from 'vitest'
import { ToastProvider } from '@/components/ui/toast'
import { describeError } from '@/components/error-panel'
import { ApiError, type AskResponse } from '@/lib/api'
import Home from './home'

const ANSWER: AskResponse = {
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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderHome() {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <Home />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('Home', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows example chips first, and a chip click submits and shows results', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(ANSWER))
    vi.stubGlobal('fetch', fetchMock)
    renderHome()

    await userEvent.click(screen.getByRole('button', { name: /top 5 customers/i }))

    expect(await screen.findByText('Validated · read-only')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /query results/i })).toBeInTheDocument()
    expect(screen.getByText(/query returned 2 rows/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/ask', expect.objectContaining({ method: 'POST' }))
  })

  it('submits with Ctrl+Enter and records the question in history', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(ANSWER)))
    renderHome()

    await userEvent.type(screen.getByLabelText(/your question/i), 'Top customers')
    await userEvent.keyboard('{Control>}{Enter}{/Control}')

    expect(await screen.findByText('Validated · read-only')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /recent questions/i })).toBeInTheDocument()
  })

  it('explains which rule a rejected query hit, with no retry button', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(
            { error: { code: 'SQL_REJECTED', message: 'blocked', rule: 'forbidden_operation' } },
            422,
          ),
        ),
    )
    renderHome()

    await userEvent.type(screen.getByLabelText(/your question/i), 'Delete all orders')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    expect(await screen.findByText(/would change or administer the database/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })

  it('shows a retryable alert when the network is down', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')))
    renderHome()

    await userEvent.type(screen.getByLabelText(/your question/i), 'anything')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    expect(await screen.findByText(/can't reach the server/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('disables Ask for blank input', () => {
    renderHome()
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeDisabled()
  })
})

describe('describeError', () => {
  it('falls back to the server message for unknown rules', () => {
    const view = describeError(new ApiError('custom', 422, 'SQL_REJECTED', 'new_rule'))
    expect(view.message).toBe('custom')
    expect(view.retryable).toBe(false)
  })

  it('treats rate limits and LLM outages as retryable', () => {
    expect(describeError(new ApiError('x', 429, 'LLM_RATE_LIMITED')).retryable).toBe(true)
    expect(describeError(new ApiError('x', 503, 'DAILY_LIMIT_REACHED')).retryable).toBe(false)
    expect(describeError(new ApiError('x', 502, 'LLM_UNAVAILABLE')).retryable).toBe(true)
  })
})
