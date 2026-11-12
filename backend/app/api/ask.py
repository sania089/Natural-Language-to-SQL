"""POST /api/ask: natural-language question -> validated SQL + rows."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import PipelineDep, SettingsDep
from app.errors import InvalidQuestionError
from app.request_context import request_id_var

router = APIRouter(tags=["ask"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    request_id: str
    question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    elapsed_ms: float
    warnings: list[str]
    repaired: bool


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, pipeline: PipelineDep, settings: SettingsDep) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise InvalidQuestionError("Please enter a question.")
    if len(question) > settings.max_question_length:
        raise InvalidQuestionError(
            f"Question is too long (max {settings.max_question_length} characters)."
        )
    answer = pipeline.ask(question)
    return AskResponse(
        request_id=request_id_var.get(),
        question=question,
        sql=answer.sql,
        columns=answer.result.columns,
        rows=answer.result.rows,
        row_count=answer.result.row_count,
        truncated=answer.result.truncated,
        elapsed_ms=answer.result.elapsed_ms,
        warnings=list(answer.warnings),
        repaired=answer.repaired,
    )
