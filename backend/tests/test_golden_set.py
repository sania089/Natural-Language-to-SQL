"""Validates the eval harness offline: a perfect fake LLM that answers with the reference SQL."""

from pathlib import Path

from app.config import Settings
from app.errors import LlmRateLimitError
from app.evals.golden_set import GOLDEN_CASES
from app.evals.run_golden import evaluate_case, pass_rate, run_golden_set
from app.services.pipeline import Pipeline
from tests.fakes import FakeLlmClient, sql_reply


def test_golden_set_has_enough_unique_cases() -> None:
    questions = [c.question for c in GOLDEN_CASES]
    assert 20 <= len(questions) <= 30
    assert len(set(questions)) == len(questions)


def test_reference_sql_passes_the_pipeline(seeded_db: Path) -> None:
    llm = FakeLlmClient(*[sql_reply(c.reference_sql) for c in GOLDEN_CASES])
    outcomes = run_golden_set(llm, Settings(database_path=seeded_db))
    failures = [(o.case.question, o.detail) for o in outcomes if not o.passed]
    assert not failures
    assert pass_rate(outcomes) == 1.0


def test_wrong_sql_is_a_failure(seeded_db: Path) -> None:
    llm = FakeLlmClient(*[sql_reply("SELECT 1") for _ in GOLDEN_CASES])
    outcomes = run_golden_set(llm, Settings(database_path=seeded_db))
    assert pass_rate(outcomes) < 0.2


def test_rate_limits_are_retried_not_counted_as_failures(seeded_db: Path) -> None:
    case = GOLDEN_CASES[0]
    llm = FakeLlmClient(LlmRateLimitError("slow down"), sql_reply(case.reference_sql))
    pipeline = Pipeline(llm=llm, db_path=seeded_db, max_rows=200, timeout_seconds=5)
    assert evaluate_case(pipeline, case, backoff_seconds=0).passed
