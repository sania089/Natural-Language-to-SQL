import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { CodeBlock } from './code-block'
import { ToastProvider } from './ui/toast'

vi.mock('@/lib/highlight', () => ({
  highlightSql: vi.fn().mockResolvedValue('<pre class="shiki"><code>HIGHLIGHTED</code></pre>'),
}))

function renderBlock(code = 'SELECT 1') {
  return render(
    <ToastProvider>
      <CodeBlock code={code} label="Generated SQL" />
    </ToastProvider>,
  )
}

describe('CodeBlock', () => {
  it('shows plain code first, then the highlighted markup', async () => {
    renderBlock()
    expect(screen.getByRole('region', { name: 'Generated SQL' })).toHaveTextContent('SELECT 1')
    await waitFor(() => {
      expect(screen.getByText('HIGHLIGHTED')).toBeInTheDocument()
    })
  })

  it('copies the SQL and confirms with a toast', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    renderBlock('SELECT 42')
    await userEvent.click(screen.getByRole('button', { name: 'Copy SQL' }))
    expect(writeText).toHaveBeenCalledWith('SELECT 42')
    expect(await screen.findByText('SQL copied to clipboard')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })
})
