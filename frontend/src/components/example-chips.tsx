import { Sparkles } from 'lucide-react'
import { Button } from './ui/button'
import { EmptyState } from './ui/empty-state'

export const EXAMPLE_QUESTIONS = [
  'Top 5 customers by total spend',
  'Monthly revenue for the last 6 months',
  'Which product categories sell the most?',
  'How many orders were placed per status?',
] as const

export interface ExampleChipsProps {
  onPick: (question: string) => void
  disabled?: boolean
}

/** First-load empty state: one click fills and submits an example. */
export function ExampleChips({ onPick, disabled = false }: ExampleChipsProps) {
  return (
    <EmptyState
      icon={Sparkles}
      title="Ask your data anything"
      description="Type a question in plain English, or try one of these:"
      action={
        <ul className="flex flex-wrap justify-center gap-2">
          {EXAMPLE_QUESTIONS.map((question) => (
            <li key={question}>
              <Button
                variant="secondary"
                size="sm"
                disabled={disabled}
                onClick={() => {
                  onPick(question)
                }}
              >
                {question}
              </Button>
            </li>
          ))}
        </ul>
      }
    />
  )
}
