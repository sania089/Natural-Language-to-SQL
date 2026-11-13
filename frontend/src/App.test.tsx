import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from './App'

describe('App', () => {
  beforeEach(() => {
    window.location.hash = ''
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    )
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the title inside the app shell', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /natural language to sql/i })).toBeInTheDocument()
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
  })

  it('offers a skip link and a theme toggle', async () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /skip to content/i })).toHaveAttribute('href', '#main')
    await userEvent.click(screen.getByRole('button', { name: /switch to dark theme/i }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('button', { name: /switch to light theme/i })).toBeInTheDocument()
  })

  it('shows the component gallery at #/components', async () => {
    window.location.hash = '#/components'
    render(<App />)
    expect(await screen.findByRole('heading', { name: /component gallery/i })).toBeInTheDocument()
  })
})
