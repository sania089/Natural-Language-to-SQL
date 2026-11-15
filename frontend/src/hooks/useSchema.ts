import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

/** The schema is static for the process lifetime, so it is fetched once and never goes stale. */
export function useSchema(enabled = true) {
  return useQuery({
    queryKey: ['schema'],
    queryFn: api.schema,
    enabled,
    staleTime: Infinity,
  })
}
