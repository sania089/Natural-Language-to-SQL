import { expect, test, type Page } from '@playwright/test'

/**
 * Browser smoke tests. The API is stubbed at the network layer, so they run with no backend or
 * LLM key and are deterministic. Backend guardrails are covered by the pytest adversarial suite.
 */
const ANSWER = {
  request_id: 'e2e',
  question: 'Top 5 customers by total spend',
  sql: 'SELECT first_name, 42 AS spend FROM customers LIMIT 5',
  columns: ['first_name', 'spend'],
  rows: [
    ['Ada', 42],
    ['Grace', 40],
  ],
  row_count: 2,
  truncated: false,
  elapsed_ms: 8.1,
  warnings: [],
  repaired: false,
}

async function stubAsk(page: Page, status: number, body: unknown) {
  await page.route('**/api/ask', (route) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) }),
  )
}

test('ask a question and see SQL + results', async ({ page }) => {
  await stubAsk(page, 200, ANSWER)
  await page.goto('/')
  await page.getByRole('button', { name: /top 5 customers/i }).click()

  await expect(page.getByText('Validated · read-only')).toBeVisible()
  const results = page.getByRole('region', { name: /query results/i })
  await expect(results.getByText('Ada')).toBeVisible()
})

test('a malicious question shows a clear rejection', async ({ page }) => {
  await stubAsk(page, 422, {
    error: { code: 'SQL_REJECTED', message: 'blocked', rule: 'forbidden_operation' },
  })
  await page.goto('/')
  await page.getByLabel(/your question/i).fill('Delete all orders')
  await page.getByRole('button', { name: /^ask$/i }).click()

  await expect(page.getByText(/would change or administer the database/i)).toBeVisible()
  await expect(page.getByRole('button', { name: /retry/i })).toHaveCount(0)
})

test('rate limiting shows a retryable warning', async ({ page }) => {
  await stubAsk(page, 429, { error: { code: 'RATE_LIMITED', message: 'Too many requests.' } })
  await page.goto('/')
  await page.getByLabel(/your question/i).fill('anything')
  await page.getByRole('button', { name: /^ask$/i }).click()

  await expect(page.getByText(/too many requests/i).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
})

for (const width of [360, 768, 1280, 1920]) {
  test(`no horizontal overflow at ${String(width)}px`, async ({ page }) => {
    await stubAsk(page, 200, ANSWER)
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.getByRole('button', { name: /top 5 customers/i }).click()
    await expect(page.getByText('Validated · read-only')).toBeVisible()

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
}
