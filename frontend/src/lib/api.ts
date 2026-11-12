const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export interface HealthResponse {
  status: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) throw new ApiError(res.statusText, res.status)
  return (await res.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
}
