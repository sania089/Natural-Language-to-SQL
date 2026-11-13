import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataTable, formatCell, type Cell } from './data-table'

const COLUMNS = ['name', 'spend']
const ROWS: Cell[][] = [
  ['Bea', 20],
  ['Ann', 1500],
  ['Cy', null],
]

function firstColumn(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[0]?.textContent ?? '')
}

describe('formatCell', () => {
  it('formats nulls and numbers', () => {
    expect(formatCell(null)).toBe('NULL')
    expect(formatCell(1500)).toBe('1,500')
    expect(formatCell('x')).toBe('x')
    expect(formatCell(true)).toBe('true')
  })
})

describe('DataTable', () => {
  it('renders headers and rows with an accessible name', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} caption="Results" />)
    expect(screen.getByRole('region', { name: 'Results' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /name/ })).toBeInTheDocument()
    expect(screen.getByText('1,500')).toBeInTheDocument()
    expect(screen.getByText('NULL')).toBeInTheDocument()
  })

  it('shows the empty state for zero rows', () => {
    render(<DataTable columns={COLUMNS} rows={[]} caption="Results" />)
    expect(screen.getByText('No rows returned')).toBeInTheDocument()
  })

  it('right-aligns numeric columns', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} caption="Results" />)
    expect(screen.getByText('1,500')).toHaveClass('text-right')
    expect(screen.getByText('Ann')).not.toHaveClass('text-right')
  })

  it('cycles sort asc → desc → none, with nulls last and aria-sort', async () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} caption="Results" />)
    const spendHeader = screen.getByRole('columnheader', { name: /spend/ })
    const sortButton = within(spendHeader).getByRole('button')

    await userEvent.click(sortButton)
    expect(spendHeader).toHaveAttribute('aria-sort', 'ascending')
    expect(firstColumn()).toEqual(['Bea', 'Ann', 'Cy'])

    await userEvent.click(sortButton)
    expect(spendHeader).toHaveAttribute('aria-sort', 'descending')
    expect(firstColumn()).toEqual(['Ann', 'Bea', 'Cy'])

    await userEvent.click(sortButton)
    expect(spendHeader).toHaveAttribute('aria-sort', 'none')
    expect(firstColumn()).toEqual(['Bea', 'Ann', 'Cy'])
  })

  it('switches to virtualized rendering above the threshold', () => {
    const many: Cell[][] = Array.from({ length: 50 }, (_, i) => [`row${String(i)}`, i])
    render(<DataTable columns={COLUMNS} rows={many} caption="Big" virtualizeAfter={10} />)
    // jsdom has no layout, so the virtualizer renders far fewer than all rows.
    expect(screen.queryAllByRole('row').length).toBeLessThan(51)
  })
})
