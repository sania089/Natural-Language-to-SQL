# Development Plan — Natural Language → SQL

**Goal:** ship a polished, safe, well-tested v1 in **7 working days**, with minimal scope creep.
**Principle:** build the thin vertical slice first (question → validated SQL → results), then harden, then polish.

---

## 0. Engineering Standards (apply every day)

### Code quality
- **Single responsibility**: one module = one job. Routes are thin; logic lives in services.
- **DRY via components/utilities**: before writing something twice, extract it. Rule of three at most.
- **Typed everywhere**: Pydantic models on the backend, strict TypeScript (`"strict": true`, no `any`) on the frontend.
- **Pure functions** for validator, prompt builder, formatters → trivially testable.
- **Dependency injection** (FastAPI `Depends`) for LLM client, DB, settings → mockable, no globals.
- **Fail fast, fail clearly**: typed domain errors (`SqlRejectedError`, `LlmError`, `QueryTimeoutError`) mapped to HTTP codes in one error handler.
- **Config in env**, validated at startup via `pydantic-settings`. No secrets in code or git.
- **No premature optimization, but no waste**: introspect schema once and cache; reuse DB connections; cap rows; memoize the prompt schema block; avoid re-renders (`memo`, stable keys, virtualized tables for large results).
- **Small functions (<30 lines), early returns, meaningful names, no dead code.**

### Git & process
- Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`), small commits, one feature branch per day/task, PR-style self-review.
- `pre-commit`: ruff, ruff-format, mypy, eslint, prettier, secret scan (gitleaks).
- CI (GitHub Actions): lint → typecheck → tests → build on every push.

### Security
- Validator is AST-based (sqlglot), allow-list first; DB opened `mode=ro` as the last line of defense.
- Treat LLM output as **untrusted input**. Treat user question as untrusted prompt input (no secrets in prompt).
- Rate limit, input length limits, CORS restricted to the frontend origin, no raw stack traces/DB errors to clients.
- Structured logging with request IDs; never log API keys.

### UI/UX standards (A+ target)
- **Design tokens** (color, spacing, radius, shadow, type scale) defined once in Tailwind config / CSS variables; no magic numbers.
- 8-pt spacing grid, max 2 typefaces (Inter + JetBrains Mono for SQL), clear type hierarchy.
- **Accessible**: WCAG 2.2 AA contrast, full keyboard navigation, visible focus rings, ARIA labels/live regions for results, `prefers-reduced-motion` honored.
- **Every async view has 4 states**: loading (skeleton), empty, error (actionable message), success.
- Dark + light theme (system default, user toggle, persisted).
- Responsive: mobile-first, tested at 360 / 768 / 1280 / 1920 px.
- Micro-interactions 150–250 ms, subtle; no layout shift; optimistic feedback on submit.
- Lighthouse targets: Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95.

### Reusable component inventory (build once, reuse everywhere)
| Component | Used in |
|-----------|---------|
| `Button`, `IconButton` | submit, copy, retry, theme toggle, example chips |
| `Card` | answer panel, schema panel, error panel |
| `Badge` | validation status, row count, timing |
| `CodeBlock` (syntax highlight + copy) | generated SQL, API examples, error SQL |
| `DataTable` (sticky header, sort, zebra, virtualized) | results, schema browser |
| `Skeleton` | table, SQL, schema loading |
| `Alert` (info/warn/error) | rejections, rate limit, network error |
| `EmptyState` | first load, zero rows |
| `Tooltip`, `Dialog`, `Toast` | hints, schema modal, copy confirmation |
| `ThemeToggle` | header |
| `QuestionInput` (textarea + submit + char count) | main page |
| `ExampleChips` | empty state |
| Hooks: `useAskQuestion`, `useSchema`, `useTheme`, `useCopyToClipboard` | app-wide |

---

## Day-by-Day Plan

### Day 1 — Foundations & Data
**Outcome:** repo scaffolded, tooling green, sample DB ready.
- [ ] Monorepo layout (`backend/`, `frontend/`, `data/`, `docs/`), `.gitignore`, `.editorconfig`, `.env.example`
- [ ] Backend scaffold: FastAPI app factory, `pydantic-settings` config, structured logging, `/api/health`
- [ ] Frontend scaffold: Vite + React + TS strict + Tailwind + shadcn/ui + TanStack Query
- [ ] Tooling: ruff, mypy, pytest, ESLint, Prettier, Vitest, pre-commit
- [ ] CI workflow (lint + typecheck + test + build)
- [ ] Seed script: e-commerce DB (`customers`, `products`, `categories`, `orders`, `order_items`) with ~1–5k realistic rows, deterministic (seeded RNG), with indexes
- [ ] Read-only connection helper (`file:...?mode=ro`, `uri=True`)

**Done when:** `pytest`, `npm test`, CI all pass on an empty-but-wired project; `python -m app.db.seed` creates the DB.

### Day 2 — SQL Validator (core of the project) + tests
**Outcome:** the safety layer, fully tested before any LLM is involved.
- [x] `sql_validator.py` (pure function) using sqlglot AST:
  - exactly one statement, root node must be `SELECT` (allow CTEs/UNION of selects)
  - walk AST: reject any DML/DDL/`PRAGMA`/`ATTACH`/`EXPLAIN`-write nodes
  - table & column **allow-list** from introspected schema; reject `sqlite_*` tables
  - function allow-list (aggregates, date, string, math); reject unknown/dangerous functions
  - strip/reject comments; max length; inject or cap `LIMIT` to `MAX_ROWS`
  - return `ValidationResult(ok, sql_normalized, reason, warnings)`
- [x] Schema introspection service (cached) → `SchemaInfo` model
- [x] **Adversarial test suite** (parametrized): stacked queries (`; DROP`), comment tricks, `UNION` exfiltration of system tables, CTE-wrapped DML, case/whitespace/unicode obfuscation, `PRAGMA`, `ATTACH`, huge queries, empty input
- [x] Target: 100% branch coverage on validator

**Done when:** all malicious samples rejected, all legit samples pass.

### Day 3 — LLM Pipeline & Executor
**Outcome:** `POST /api/ask` works end-to-end via curl.
- [ ] `LlmClient` protocol + `GeminiClient` + `GroqClient` implementations (both via OpenAI-compatible endpoints; free-tier rate-limit aware) (timeout, retries with backoff, typed errors); tests use a `FakeLlmClient`
- [ ] `prompt_builder.py`: system prompt = role + rules + compact schema (DDL-style with column types, FK hints, 2–3 sample values per low-cardinality column) + few-shot examples; user question isolated in a delimited block
- [ ] Output parsing: extract SQL from fenced block / strict JSON; handle "cannot answer" response → friendly 422
- [ ] `executor.py`: read-only conn, `progress_handler` timeout, row cap, returns columns/rows/timing
- [ ] `pipeline.py`: build prompt → LLM → validate → (on reject/exec error: **one** repair retry with the error fed back) → execute
- [ ] Central exception → HTTP mapping; request IDs; `GET /api/schema`
- [ ] Integration tests with `FakeLlmClient` (happy path, rejected path, repair path, timeout path)

**Done when:** curl "top 5 customers by spend" returns valid rows; "delete all customers" returns a clean rejection.

### Day 4 — Frontend Foundation: Design System & Components
**Outcome:** reusable UI kit + app shell, styled and themed.
- [ ] Design tokens (CSS variables + Tailwind theme): palette (neutral + one accent, semantic success/warn/danger), type scale, radii, shadows, motion durations
- [ ] Dark/light theme with `useTheme` (system default, persisted)
- [ ] Build the primitives: `Button`, `Card`, `Badge`, `Alert`, `Skeleton`, `Tooltip`, `Toast`, `Dialog`, `EmptyState`
- [ ] `CodeBlock` (Shiki/Prism highlight, copy button via `useCopyToClipboard`), `DataTable` (sticky header, sortable, numeric right-align, zebra, horizontal scroll, virtualization for >200 rows)
- [ ] App shell: header (logo, schema button, theme toggle), centered content column, footer
- [ ] Component stories/demo page (or Storybook-lite route) to eyeball all states in both themes

**Done when:** every primitive renders correctly in light/dark, keyboard focus visible, unit-tested for basic behavior.

### Day 5 — Main Experience (wiring UI ↔ API)
**Outcome:** fully working app with all states.
- [ ] Typed API client (`lib/api.ts`) + `useAskQuestion` (TanStack mutation) + `useSchema`
- [ ] `QuestionInput`: autosize textarea, `Ctrl/Cmd+Enter` submit, char counter, disabled+spinner while loading
- [ ] `ExampleChips` in the empty state (one click fills & submits)
- [ ] Answer panel: SQL `CodeBlock`, validation `Badge`, row count + elapsed `Badge`s, `DataTable`
- [ ] Error handling UI: `SQL_REJECTED` → friendly explanation of *which rule* was hit; rate-limit, network, LLM-down → `Alert` with retry
- [ ] Schema browser `Dialog` (tables → columns/types) reusing `DataTable`/`Card`
- [ ] Skeleton loaders, zero-rows empty state, `aria-live` announcement of results
- [ ] Session history list (in-memory/localStorage) to re-open past answers

**Done when:** a non-technical user can go from landing to a result in <15 seconds with zero instructions.

### Day 6 — Hardening, Performance, Accessibility
**Outcome:** production-quality behavior.
- [ ] Rate limiting (slowapi), CORS lock-down, input length validation, security headers
- [ ] Caching: schema introspection (startup), optional LRU for identical questions
- [ ] Prompt evaluation: a 20–30 question golden set (question → expected result set); script prints pass rate; iterate prompt/few-shots to reach ≥ 85%
- [ ] Frontend perf: code-split (lazy-load highlighter + schema dialog), memoize table rows, bundle analysis
- [ ] A11y audit (axe, keyboard-only walkthrough, screen reader spot check), contrast verification
- [ ] Responsive pass at 360 / 768 / 1280 / 1920
- [ ] Lighthouse run; fix to hit targets
- [ ] Playwright smoke test: ask → see results; ask malicious → see rejection

**Done when:** test suites + Lighthouse targets + golden-set pass rate are all met.

### Day 7 — Polish, Docs, Release
**Outcome:** project closed and demo-ready.
- [ ] Visual polish: spacing/alignment pass, subtle motion, favicon, meta/OG tags, 404/error boundary
- [ ] Dockerfile(s) + `docker-compose.yml` for one-command run
- [ ] README final pass: screenshots/GIF, architecture diagram, guardrail table verified against the code
- [ ] `docs/ARCHITECTURE.md` (short) and `docs/GUARDRAILS.md` (each rule → test that proves it)
- [ ] Final cleanup: dead code, TODOs, dependency audit (`pip-audit`, `npm audit`)
- [ ] Tag `v1.0.0`, write release notes

**Done when:** a fresh clone runs with `docker compose up` and the demo script (below) works.

---

## Scope Control (to close fast)

**In v1:** single sample DB, single question → answer flow, guardrails, schema viewer, session history, themes.
**Deferred (post-v1):** auth, multiple DBs, CSV export, charts, streaming, query explanations, persistent server-side history.
If a day slips, cut in this order: session history → schema dialog polish → Docker → golden-set size. **Never cut:** validator tests, read-only DB, error/empty/loading states.

## Definition of Done (per task)
1. Typed, linted, formatted, no warnings
2. Unit tests for logic; component test for UI behavior
3. All four UI states handled (loading / empty / error / success)
4. Accessible by keyboard and screen reader
5. No duplicated logic — shared code extracted to a component/util
6. Merged with a Conventional Commit message and green CI

## Demo Script (acceptance check)
1. Click an example chip → results table with SQL shown
2. Ask a custom analytical question (joins + aggregation) → correct result
3. Ask "Delete all orders" → clear rejection, nothing changes
4. Ask "Show me sqlite_master" → rejected by allow-list
5. Toggle theme, resize to mobile → layout remains clean and usable
6. Kill the API key → friendly error with retry, no stack trace

## Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| LLM produces wrong-but-valid SQL | Show SQL transparently; golden-set evals; schema hints + few-shot examples |
| Validator bypass | AST parsing, allow-lists, adversarial tests, **read-only DB connection** as backstop |
| Slow/expensive queries | Timeout via progress handler, row cap, indexes on seed data |
| LLM latency | Skeletons, optimistic UI, request timeout + retry, optional caching |
| Scope creep | Deferred list above; fixed 7-day timebox |
