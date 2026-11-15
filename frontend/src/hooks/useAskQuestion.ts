import { useMutation } from '@tanstack/react-query'
import { api, type AskResponse, type ApiError } from '@/lib/api'

/** Submits a question to /api/ask. `retry: false` — rejections are deterministic, don't repeat them. */
export function useAskQuestion() {
  return useMutation<AskResponse, ApiError, string>({
    mutationFn: (question) => api.ask(question),
    retry: false,
  })
}
