# Architecture

A question goes through five small, single-purpose steps. Routes are thin; logic lives in `backend/app/services/`.

```
POST /api/ask
  └─ pipeline.py
       1. answer_cache      identical question? return the cached answer
       2. prompt_builder    system prompt = rules + compact schema + few-shot; question isolated in a delimited block
       3. llm/              Gemini or Groq via OpenAI-compatible endpoints (timeout, retries, typed errors)
       4. llm_output        extract SQL from JSON / fenced block, or a "cannot answer" reply -> 422
       5. sql_validator     AST check (sqlglot) against the schema allow-list
       6. executor          read-only connection, timeout, row cap
       (validation or execution failed? one repair retry with the error fed back to the LLM)
```

## Backend (`backend/app`)

| Module | Job |
|--------|-----|
| `main.py` | App factory; wires settings, cache, rate limiter, security headers, CORS, routers, optional static UI |
| `config.py` | `pydantic-settings`, validated at startup |
| `dependencies.py` | FastAPI `Depends` providers (settings, LLM client, pipeline, rate limit) so tests can swap them |
| `errors.py`, `error_handlers.py` | Typed domain errors mapped to HTTP codes in one place; no raw errors reach clients |
| `security.py` | Security headers middleware |
| `services/sql_validator.py` | Pure function: SQL + schema -> `ValidationResult` |
| `services/schema.py` | Cached schema introspection -> `SchemaInfo` |
| `services/executor.py` | Runs validated SQL on a read-only connection |
| `services/rate_limiter.py`, `answer_cache.py` | In-process sliding window limiter and LRU cache |
| `db/` | Read-only connection helper, schema, deterministic seed |
| `evals/` | 26-question golden set run against the live LLM |

## Frontend (`frontend/src`)

React + TypeScript (strict) + Tailwind. `components/ui/` holds reusable primitives (Button, Card, Alert, Toast, ...);
feature components (`answer-panel`, `question-input`, `schema-dialog`, ...) compose them. Data fetching uses TanStack Query
(`hooks/`), the API client is `lib/api.ts`. The schema dialog and syntax highlighter are lazy-loaded.

## Deployment

The Docker image builds the UI, seeds the SQLite database (deterministic, read-only at runtime) and serves both the API and the UI
from one origin, so no CORS setup is needed. State (rate limiter, answer cache) is in-memory: **run a single instance**.

## Known limits (by design for v1)

SQLite sample data only; in-memory limiter/cache (resets on restart, not shared across instances); no auth.
