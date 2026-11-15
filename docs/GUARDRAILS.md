# Guardrails -> tests

Every rule below is enforced in code and proven by a test. Test names refer to `backend/tests/`.

## SQL validator (`services/sql_validator.py`)

| Rule (`Rule` value) | Blocks | Proven by |
|---------------------|--------|-----------|
| `empty_query` | blank / whitespace input | `test_malicious_queries_rejected` (empty cases) |
| `query_too_long` | oversized queries | `test_malicious_queries_rejected` (huge), `test_max_length_parameter` |
| `illegal_characters` | NUL and control characters | `test_malicious_queries_rejected` |
| `comments_not_allowed` | `--` and `/* */` comment tricks (markers inside string literals are fine) | `test_malicious_queries_rejected`, `test_comment_markers_inside_string_literals_are_fine` |
| `syntax_error` | unparsable SQL | `test_malicious_queries_rejected` |
| `multiple_statements` | stacked queries (`; DROP ...`) | `test_malicious_queries_rejected` |
| `select_only` | anything whose root is not a `SELECT` (DML, DDL, `PRAGMA`, `ATTACH`, `EXPLAIN`) | `test_malicious_queries_rejected` |
| `forbidden_operation` | write/DDL nodes hidden inside CTEs or subqueries | `test_malicious_queries_rejected` |
| `recursive_cte` | `WITH RECURSIVE` (runaway queries) | `test_malicious_queries_rejected` |
| `table_function` | `pragma_*()`, `json_each()` | `test_malicious_queries_rejected` |
| `qualified_table` | `main.x`, `temp.x` | `test_malicious_queries_rejected` |
| `system_table` | `sqlite_master` and other `sqlite_*` | `test_malicious_queries_rejected` |
| `unknown_table` / `unknown_column` | anything outside the introspected schema | `test_malicious_queries_rejected` |
| `function_not_allowed` | functions outside the allow-list | `test_malicious_queries_rejected` |
| Row limit | missing / oversized / non-literal `LIMIT` is added or capped (also on set operations) | `test_limit_added_when_missing`, `test_large_or_nonliteral_limit_is_capped`, `test_limit_added_to_set_operation_not_just_last_branch` |
| No SQL on reject | a rejection never returns usable SQL | `test_rejection_never_returns_sql` |
| Legit queries pass | the allow-list is not over-strict | `test_legit_queries_pass_and_execute` |

## Database and execution

| Rule | Proven by |
|------|-----------|
| Connection is read-only (`mode=ro`): writes fail even if the validator were bypassed | `test_readonly_connection_rejects_writes`, `test_writes_fail_on_readonly_connection` |
| Query timeout | `test_timeout`, `test_query_timeout_path` |
| Row cap, `truncated` flag | `test_row_cap_sets_truncated` |

## LLM pipeline

| Rule | Proven by |
|------|-----------|
| Question cannot break out of its prompt delimiter | `test_question_cannot_break_out_of_delimiter` |
| Malicious LLM output is rejected after one repair attempt | `test_malicious_sql_rejected_after_one_repair` |
| Garbled LLM output -> 502, never executed | `test_garbled_llm_output_is_502` |
| Unexpected errors are sanitised (no stack traces) | `test_unexpected_error_is_sanitised` |

## API hardening (`test_hardening.py`)

| Rule | Proven by |
|------|-----------|
| Rate limit -> `429` + `Retry-After` | `test_ask_is_rate_limited`, `test_limiter_blocks_then_recovers` |
| Input length limits | `test_overlong_question_rejected`, `test_invalid_questions` |
| Security headers (CSP, nosniff, frame deny) | `test_security_headers_present`, `test_static_ui_served_with_app_csp` |
| CORS only for configured origins | `test_cors_only_allows_configured_origin` |

## End to end

`frontend/e2e/smoke.spec.ts` (Playwright): a normal question returns results; a malicious one shows a rejection.
The prompt quality gate is `python -m app.evals.run_golden` (>= 85% required; last live run 96%).
