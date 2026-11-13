import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { Alert } from './alert'
import { Badge } from './badge'
import { Button, IconButton } from './button'
import { Dialog, DialogContent, DialogTrigger } from './dialog'
import { EmptyState } from './empty-state'
import { Skeleton } from './skeleton'
import { ToastProvider, useToast } from './toast'

describe('Button', () => {
  it('fires onClick', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Go</Button>)
    await userEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('is disabled and busy while loading', async () => {
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        Go
      </Button>,
    )
    const button = screen.getByRole('button', { name: 'Go' })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
    await userEvent.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('IconButton exposes its label as the accessible name', () => {
    render(<IconButton label="Close">x</IconButton>)
    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
  })
})

describe('Alert', () => {
  it('uses role=alert for errors and role=status otherwise', () => {
    const { rerender } = render(<Alert variant="error" title="Boom" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Boom')
    rerender(<Alert variant="info" title="FYI" />)
    expect(screen.getByRole('status')).toHaveTextContent('FYI')
  })

  it('renders body and action', () => {
    render(
      <Alert variant="error" title="Failed" action={<button>Retry</button>}>
        Try again later
      </Alert>,
    )
    expect(screen.getByText('Try again later')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})

describe('Badge, Skeleton, EmptyState', () => {
  it('Badge renders children', () => {
    render(<Badge variant="success">Validated</Badge>)
    expect(screen.getByText('Validated')).toBeInTheDocument()
  })

  it('Skeleton is hidden from assistive tech', () => {
    const { container } = render(<Skeleton />)
    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true')
  })

  it('EmptyState shows title, description and action', () => {
    render(
      <EmptyState title="Nothing yet" description="Ask something" action={<button>Ask</button>} />,
    )
    expect(screen.getByRole('heading', { name: 'Nothing yet' })).toBeInTheDocument()
    expect(screen.getByText('Ask something')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ask' })).toBeInTheDocument()
  })
})

describe('Dialog', () => {
  it('opens from the trigger and closes with Escape', async () => {
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent title="Schema" description="Tables and columns">
          body
        </DialogContent>
      </Dialog>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Open' }))
    expect(screen.getByRole('dialog', { name: 'Schema' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('Toast', () => {
  function Trigger() {
    const { toast } = useToast()
    return (
      <button
        onClick={() => {
          toast('Saved', 'success')
        }}
      >
        fire
      </button>
    )
  }

  it('shows a message and can be dismissed', async () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'fire' }))
    expect(screen.getByText('Saved')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }))
    expect(screen.queryByText('Saved')).not.toBeInTheDocument()
  })

  it('throws when used outside the provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<Trigger />)).toThrow(/ToastProvider/)
    spy.mockRestore()
  })
})
