import { useState } from 'react'
import { AnswerPanel, AnswerSkeleton } from '@/components/answer-panel'
import { ErrorPanel } from '@/components/error-panel'
import { ExampleChips } from '@/components/example-chips'
import { HistoryList } from '@/components/history-list'
import { QuestionInput } from '@/components/question-input'
import { useAskQuestion } from '@/hooks/useAskQuestion'
import { useHistory } from '@/hooks/useHistory'
import type { AskResponse } from '@/lib/api'

/** The main flow: question in, validated SQL + results out, with every async state handled. */
export default function Home() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AskResponse | null>(null)
  const ask = useAskQuestion()
  const history = useHistory()

  const submit = (text: string) => {
    setQuestion(text)
    setAnswer(null)
    ask.mutate(text, {
      onSuccess: (result) => {
        setAnswer(result)
        history.add(result)
      },
    })
  }

  const openFromHistory = (item: AskResponse) => {
    ask.reset()
    setQuestion(item.question)
    setAnswer(item)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold">Natural Language to SQL</h1>
        <p className="mt-2 text-muted">Ask questions about your data in plain English.</p>
      </div>
      <QuestionInput
        value={question}
        onChange={setQuestion}
        onSubmit={submit}
        loading={ask.isPending}
      />
      <HistoryList items={history.items} onOpen={openFromHistory} onClear={history.clear} />
      {ask.isPending && <AnswerSkeleton />}
      {ask.isError && (
        <ErrorPanel
          error={ask.error}
          onRetry={() => {
            submit(question.trim())
          }}
        />
      )}
      {answer && !ask.isPending && <AnswerPanel answer={answer} />}
      {!answer && !ask.isPending && !ask.isError && <ExampleChips onPick={submit} />}
    </div>
  )
}
