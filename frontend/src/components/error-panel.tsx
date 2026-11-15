import { RotateCw } from 'lucide-react'
import { ApiError, NETWORK_ERROR_CODE } from '@/lib/api'
import { Alert } from './ui/alert'
import { Button } from './ui/button'

/** Plain-language explanation of each validator rule (mirrors backend `Rule`). */
export const RULE_EXPLANATIONS: Record<string, string> = {
  select_only: 'Only read-only SELECT queries are allowed.',
  forbidden_operation: 'That would change or administer the database, which is blocked.',
  multiple_statements: 'Only one SQL statement can run at a time.',
  system_table: 'Internal database tables (like sqlite_master) are off-limits.',
  unknown_table: 'The query referred to a table that does not exist.',
  unknown_column: 'The query referred to a column that does not exist.',
  qualified_table: 'Schema-qualified table names (e.g. main.table) are not allowed.',
  table_function: 'Table-valued functions are not allowed.',
  recursive_cte: 'Recursive queries are blocked to prevent runaway execution.',
  function_not_allowed: 'The query used a function that is not on the allow-list.',
  comments_not_allowed: 'SQL comments are not allowed.',
  illegal_characters: 'The query contained characters that are not allowed.',
  query_too_long: 'The generated query was too long.',
  syntax_error: 'The generated query was not valid SQL.',
  empty_query: 'No query was generated.',
}

export interface ErrorView {
  variant: 'error' | 'warning'
  title: string
  message: string
  retryable: boolean
}

/** Maps any thrown error to what the user should see. Pure, so it is easy to test. */
export function describeError(error: Error): ErrorView {
  if (!(error instanceof ApiError)) {
    return {
      variant: 'error',
      title: 'Something went wrong',
      message: error.message,
      retryable: true,
    }
  }
  switch (error.code) {
    case 'SQL_REJECTED':
      return {
        variant: 'warning',
        title: 'That query was blocked',
        message: (error.rule && RULE_EXPLANATIONS[error.rule]) || error.message,
        retryable: false,
      }
    case 'CANNOT_ANSWER':
      return {
        variant: 'warning',
        title: "I can't answer that from this data",
        message: error.message,
        retryable: false,
      }
    case 'INVALID_QUESTION':
      return {
        variant: 'warning',
        title: 'Check your question',
        message: error.message,
        retryable: false,
      }
    case 'RATE_LIMITED':
    case 'LLM_RATE_LIMITED':
      return {
        variant: 'warning',
        title: 'Too many requests',
        message: 'The AI service is rate-limited right now. Wait a few seconds and try again.',
        retryable: true,
      }
    case 'LLM_UNAVAILABLE':
    case 'LLM_TIMEOUT':
      return {
        variant: 'error',
        title: 'The AI service is unavailable',
        message: 'We could not generate SQL right now. Please try again shortly.',
        retryable: true,
      }
    case 'QUERY_TIMEOUT':
      return {
        variant: 'error',
        title: 'The query took too long',
        message: 'Try narrowing the question, e.g. a shorter time range.',
        retryable: true,
      }
    case NETWORK_ERROR_CODE:
      return {
        variant: 'error',
        title: "Can't reach the server",
        message: 'Check your connection and that the API is running.',
        retryable: true,
      }
    default:
      return {
        variant: 'error',
        title: 'Something went wrong',
        message: error.message,
        retryable: true,
      }
  }
}

export interface ErrorPanelProps {
  error: Error
  onRetry: () => void
}

export function ErrorPanel({ error, onRetry }: ErrorPanelProps) {
  const view = describeError(error)
  return (
    <Alert
      variant={view.variant}
      title={view.title}
      action={
        view.retryable ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        ) : undefined
      }
    >
      {view.message}
      {error instanceof ApiError && error.requestId && (
        <span className="mt-1 block text-xs">Reference: {error.requestId}</span>
      )}
    </Alert>
  )
}
