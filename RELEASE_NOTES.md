# v1.0.0

First release of **Natural Language → SQL**: ask a question in plain English, get validated read-only SQL and results.

## Highlights
- LLM (Gemini or Groq) → SQL → AST validator (sqlglot) → read-only SQLite execution, with one automatic repair retry
- Defense in depth: prompt rules, parser allow-lists, row limits and timeout, read-only database, rate limiting, security headers (see `docs/GUARDRAILS.md`)
- Accessible, themed (light/dark), responsive UI with loading / empty / error / success states, schema browser and session history
- Toasts slide out and can be swiped away; error boundary and 404 screen
- 26-question golden-set evaluation (96% on the last live run), adversarial validator suite, axe a11y tests, Playwright smoke test
- One-command run with Docker; Render blueprint included

## Known limits
Sample SQLite data only; in-memory rate limiter and cache (single instance); no auth. Dev-only npm audit findings (vite/vitest) need major-version upgrades and do not affect the production bundle.
