import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the title', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /natural language to sql/i })).toBeInTheDocument()
  })
})
