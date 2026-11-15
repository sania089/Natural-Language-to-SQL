"""question -> prompt -> LLM -> validate -> execute, with a single repair retry."""

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.db.connection import connect_readonly
from app.errors import AppError, QueryFailedError, SqlRejectedError
from app.services.answer_cache import AnswerCache, cache_key
from app.services.daily_budget import DailyBudget
from app.services.executor import QueryResult, execute_query
from app.services.llm.client import ChatMessage, LlmClient
from app.services.llm_output import parse_llm_output
from app.services.prompt_builder import build_messages, build_schema_block, repair_message
from app.services.schema import SchemaInfo, collect_samples, get_schema
from app.services.sql_validator import validate_sql

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # first try + exactly one repair


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000


class AskResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str
    result: QueryResult
    warnings: tuple[str, ...] = ()
    repaired: bool = False


@lru_cache(maxsize=8)
def get_schema_block(db_path: Path) -> str:
    """Prompt schema block, computed once per database file."""
    schema = get_schema(db_path)
    conn = connect_readonly(db_path)
    try:
        return build_schema_block(schema, collect_samples(conn, schema))
    finally:
        conn.close()


@dataclass(frozen=True)
class Pipeline:
    llm: LlmClient
    db_path: Path
    max_rows: int
    timeout_seconds: float
    cache: AnswerCache | None = None
    budget: DailyBudget | None = None

    @property
    def schema(self) -> SchemaInfo:
        return get_schema(self.db_path)

    def ask(self, question: str) -> AskResult:
        key = cache_key(self.db_path, question)
        if self.cache and (hit := self.cache.get(key)) is not None:
            log.info("answer served from cache")
            return hit
        result = self._generate(question)
        if self.cache:
            self.cache.put(key, result)
        return result

    def _generate(self, question: str) -> AskResult:
        messages = build_messages(get_schema_block(self.db_path), question)
        failure: AppError | None = None
        for attempt in range(MAX_ATTEMPTS):
            if self.budget:
                self.budget.consume()
            started = time.perf_counter()
            raw = self.llm.complete(messages)
            log.info("llm call took %.0f ms (attempt %d)", _ms_since(started), attempt + 1)
            candidate = parse_llm_output(raw)
            try:
                return self._validate_and_run(candidate, repaired=attempt > 0)
            except (SqlRejectedError, QueryFailedError) as err:
                failure = err
                log.info("attempt failed", extra={"attempt": attempt + 1, "code": err.code})
                feedback = err.extra.get("detail") or err.message
                messages = [*messages, ChatMessage(role="assistant", content=raw)]
                messages.append(repair_message(feedback))
        raise failure  # type: ignore[misc]

    def _validate_and_run(self, candidate: str, *, repaired: bool) -> AskResult:
        started = time.perf_counter()
        verdict = validate_sql(candidate, self.schema, max_rows=self.max_rows)
        log.info("validation took %.1f ms", _ms_since(started))
        if not verdict.ok or verdict.sql_normalized is None:
            raise SqlRejectedError(
                verdict.reason or "The generated query was rejected.",
                extra={"rule": str(verdict.rule), "sql": candidate},
            )
        result = execute_query(
            self.db_path,
            verdict.sql_normalized,
            max_rows=self.max_rows,
            timeout_seconds=self.timeout_seconds,
        )
        log.info("execution took %.1f ms", result.elapsed_ms)
        return AskResult(
            sql=verdict.sql_normalized, result=result, warnings=verdict.warnings, repaired=repaired
        )
