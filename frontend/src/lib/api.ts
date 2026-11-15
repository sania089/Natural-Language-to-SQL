const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export type Cell = string | number | boolean | null

export interface HealthResponse {
  status: string
}

export interface AskResponse {
  request_id: string
  question: string
  sql: string
  columns: string[]
  rows: Cell[][]
  row_count: number
  truncated: boolean
  elapsed_ms: number
  warnings: string[]
  repaired: boolean
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
}

export interface ForeignKey {
  column: string
  ref_table: string
  ref_column: string
}

export interface TableInfo {
  name: string
  columns: ColumnInfo[]
  foreign_keys: ForeignKey[]
}

export interface SchemaResponse {
  tables: TableInfo[]
}

/** Shape of the backend's central error body: `{ error: { code, message, ... } }`. */
interface ErrorBody {
  error?: { code?: string; message?: string; request_id?: string; rule?: string }
}

export const NETWORK_ERROR_CODE = 'NETWORK_ERROR'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string = 'UNKNOWN',
    readonly rule?: string,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function parseError(res: Response): Promise<ApiError> {
  const body = (await res.json().catch(() => null)) as ErrorBody | null
  const err = body?.error
  return new ApiError(
    err?.message ?? res.statusText,
    res.status,
    err?.code,
    err?.rule,
    err?.request_id,
  )
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError('Could not reach the server.', 0, NETWORK_ERROR_CODE)
  }
  if (!res.ok) throw await parseError(res)
  return (await res.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  schema: () => request<SchemaResponse>('/api/schema'),
  ask: (question: string) =>
    request<AskResponse>('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
}
