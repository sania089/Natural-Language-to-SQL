"""Prompt evaluation: run each golden question through the real pipeline and compare result sets.

Usage (needs a live LLM key in .env):  python -m app.evals.run_golden [--min-pass 0.85]
"""

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.errors import AppError, LlmRateLimitError
from app.evals.golden_set import GOLDEN_CASES, GoldenCase
from app.services.executor import QueryResult, execute_query
from app.services.llm.client import LlmClient, build_llm_client
from app.services.pipeline import AskResult, Pipeline

# Free tiers are rate-limited; pause between live calls.
DEFAULT_PAUSE_SECONDS = 4.0
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = 20.0
EXPECTED_ROW_CAP = 10_000


@dataclass(frozen=True)
class CaseOutcome:
    case: GoldenCase
    passed: bool
    detail: str


def _norm_cell(value: Any) -> Any:
    return round(value, 2) if isinstance(value, float) else value


def _norm_rows(rows: list[list[Any]], *, ordered: bool) -> list[tuple[str, ...]]:
    normalized = [tuple(repr(_norm_cell(v)) for v in row) for row in rows]
    return normalized if ordered else sorted(normalized)


def results_match(expected: QueryResult, actual: QueryResult, *, ordered: bool) -> bool:
    """Compare values only: column aliases are free-form, and row order matters only if asked."""
    return _norm_rows(expected.rows, ordered=ordered) == _norm_rows(actual.rows, ordered=ordered)


def _ask_with_backoff(pipeline: Pipeline, question: str, backoff_seconds: float) -> AskResult:
    """Provider throttling says nothing about prompt quality, so wait and retry it."""
    for attempt in range(RATE_LIMIT_RETRIES):
        try:
            return pipeline.ask(question)
        except LlmRateLimitError:
            time.sleep(backoff_seconds * (attempt + 1))
    return pipeline.ask(question)


def evaluate_case(
    pipeline: Pipeline, case: GoldenCase, backoff_seconds: float = RATE_LIMIT_BACKOFF_SECONDS
) -> CaseOutcome:
    expected = execute_query(
        pipeline.db_path,
        case.reference_sql,
        max_rows=EXPECTED_ROW_CAP,
        timeout_seconds=pipeline.timeout_seconds,
    )
    try:
        answer = _ask_with_backoff(pipeline, case.question, backoff_seconds)
    except AppError as err:
        return CaseOutcome(case, False, f"{err.code}: {err.message}")
    ordered = "ORDER BY" in case.reference_sql.upper()
    if results_match(expected, answer.result, ordered=ordered):
        return CaseOutcome(case, True, "")
    return CaseOutcome(case, False, f"wrong result; generated SQL: {answer.sql}")


def run_golden_set(
    llm: LlmClient,
    settings: Settings,
    *,
    pause_seconds: float = 0.0,
    backoff_seconds: float = RATE_LIMIT_BACKOFF_SECONDS,
) -> list[CaseOutcome]:
    pipeline = Pipeline(
        llm=llm,
        db_path=settings.database_path,
        max_rows=settings.max_rows,
        timeout_seconds=settings.query_timeout_seconds,
    )
    outcomes = []
    for i, case in enumerate(GOLDEN_CASES):
        if i and pause_seconds:
            time.sleep(pause_seconds)
        outcomes.append(evaluate_case(pipeline, case, backoff_seconds))
    return outcomes


def pass_rate(outcomes: list[CaseOutcome]) -> float:
    return sum(o.passed for o in outcomes) / len(outcomes) if outcomes else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-pass", type=float, default=0.85)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_SECONDS)
    args = parser.parse_args(argv)

    logging.disable(logging.CRITICAL)
    settings = get_settings()
    if not Path(settings.database_path).exists():
        print(f"Database not found: {settings.database_path} (run `python -m app.db.seed`)")
        return 2
    outcomes = run_golden_set(build_llm_client(settings), settings, pause_seconds=args.pause)
    for o in outcomes:
        print(f"[{'PASS' if o.passed else 'FAIL'}] {o.case.question}")
        if o.detail:
            print(f"        {o.detail}")
    rate = pass_rate(outcomes)
    passed = sum(o.passed for o in outcomes)
    print(f"\nPass rate: {passed}/{len(outcomes)} = {rate:.0%} (target {args.min_pass:.0%})")
    return 0 if rate >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
