# Natural Language → SQL

Ask questions about a sample database in plain English. An LLM generates **read-only SQL**, a **validator** checks it against strict guardrails, and only then is it executed. Results are shown in a clean, accessible UI together with the SQL that produced them.

> Showcases: **guardrails · SQL safety · schema-aware prompting**

---

## Features

- **Plain-English questions** → SQL → results table (and optional chart)
- **Schema-aware prompting**: the model only sees the tables/columns it is allowed to query
- **Multi-layer SQL safety** (see below) — nothing reaches the database unvalidated
- **Transparent**: every answer shows the generated SQL, the validation verdict, and execution time
- **Self-repair**: if validation or execution fails, the error is fed back to the model once for a corrected query
- **Polished UI**: responsive, dark/light themes, keyboard accessible, loading/empty/error states
- **Example questions** to get started in one click

## How it works

```
Question ──► Prompt builder (schema + rules) ──► LLM ──► SQL
                                                          │
                                         ┌────────────────▼───────────────┐
                                         │ Validator (AST-based, sqlglot) │
                                         └────────────────┬───────────────┘
                                      rejected ◄──────────┤──────────► approved
                               (reason shown / 1 retry)                  │
                                                          ┌──────────────▼─────────────┐
                                                          │ Read-only DB connection,   │
                                                          │ timeout, row limit         │
                                                          └──────────────┬─────────────┘
                                                                         ▼
                                                             Results + SQL + metadata
```

## SQL safety guardrails (defense in depth)

| Layer | Protection |
|-------|-----------|
| Prompt | Model told: SELECT only, use only listed tables/columns, always `LIMIT` |
| Parser | SQL parsed to an AST (not regex); must be exactly **one** `SELECT` statement |
| Allow-list | Only whitelisted tables/columns; no `PRAGMA`, `ATTACH`, `sqlite_master`, system functions |
| Block-list | `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/REPLACE/TRUNCATE`, multi-statements, comments |
| Limits | Auto-injected/capped `LIMIT`, max query length, execution timeout |
| Database | Connection opened **read-only** (`mode=ro`) — last line of defense even if the validator is bypassed |
| API | Input length limits, rate limiting, no raw DB errors leaked to the client |

## Tech stack

| Area | Choice | Why |
|------|--------|-----|
| Backend | Python 3.11+, FastAPI, Pydantic v2 | Typed, fast, auto-generated OpenAPI docs |
| SQL validation | `sqlglot` | Real SQL parser → AST checks, not string matching |
| Database | SQLite (sample e-commerce dataset) | Zero setup, supports read-only mode |
| LLM | Google Gemini (primary) + Groq (fallback), free tiers, behind an interface | Free, strong SQL generation; swappable |
| Frontend | React + TypeScript + Vite | Fast dev loop, type safety |
| Styling | Tailwind CSS + shadcn/ui (Radix) | Accessible primitives, consistent design tokens |
| Data fetching | TanStack Query | Caching, loading/error states |
| Tests | pytest, Vitest + Testing Library, Playwright (smoke) | |
| Tooling | ruff, mypy, ESLint, Prettier, pre-commit, GitHub Actions | |

## Project structure

```
Natural-Language-to-SQL/
├── backend/
│   ├── app/
│   │   ├── api/            # routes (thin controllers)
│   │   ├── core/           # config, logging, errors
│   │   ├── services/       # llm, prompt_builder, sql_validator, executor, pipeline
│   │   ├── db/             # connection, schema introspection, seed
│   │   └── schemas/        # Pydantic request/response models
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/     # ui/ (primitives) + feature components
│       ├── hooks/          # useAskQuestion, useTheme, ...
│       ├── lib/            # api client, utils
│       └── pages/
├── data/                   # sample SQLite DB + seed script
├── docs/
├── DEVELOPMENT_PLAN.md
└── README.md
```

## Getting started

### Prerequisites
- Python 3.11+, Node 20+
- A free Gemini API key (and optionally a Groq key)

### Setup

```bash
# 1. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                               # add GEMINI_API_KEY (and GROQ_API_KEY)
python -m app.db.seed                              # builds the sample database
uvicorn app.main:app --reload                      # http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Required (primary provider) |
| `GROQ_API_KEY` | — | Optional fallback provider |
| `LLM_PROVIDER` | `gemini` | `gemini` or `groq` |
| `GEMINI_MODEL` / `GROQ_MODEL` | see `.env.example` | Models used for SQL generation |
| `DB_PATH` | `data/sample.db` | SQLite file (opened read-only) |
| `MAX_ROWS` | `500` | Hard cap on returned rows |
| `QUERY_TIMEOUT_SEC` | `5` | Execution timeout |
| `RATE_LIMIT_PER_MIN` | `20` | Per-client request limit |

## API

`POST /api/ask`
```json
{ "question": "Top 5 customers by total spend in 2024" }
```
Response:
```json
{
  "sql": "SELECT ... LIMIT 5",
  "validation": { "ok": true, "warnings": [] },
  "columns": ["customer", "total_spend"],
  "rows": [["Ada", 1234.5]],
  "row_count": 5,
  "elapsed_ms": 42
}
```
Rejected queries return `422` with `{ "error": { "code": "SQL_REJECTED", "reason": "Only SELECT statements are allowed" } }`.

`GET /api/schema` — tables/columns exposed to the model · `GET /api/health`

## Testing

```bash
cd backend && pytest -q          # includes an adversarial SQL-injection suite
cd frontend && npm test
```

## Example questions

- "How many orders were placed each month in 2024?"
- "Which product categories generate the most revenue?"
- "List customers who have never placed an order"
- Try the guardrails: "Delete all customers" → rejected with an explanation

## Roadmap

Query history · CSV export · multiple databases · query explanation · streaming responses

## License

MIT
