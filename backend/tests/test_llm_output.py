import pytest

from app.errors import CannotAnswerError, LlmError
from app.services.llm_output import parse_llm_output


@pytest.mark.parametrize(
    "raw",
    [
        '{"sql": "SELECT 1"}',
        '```json\n{"sql": "SELECT 1"}\n```',
        "```sql\nSELECT 1\n```",
        "  SELECT 1  ",
        "WITH a AS (SELECT 1) SELECT * FROM a",
    ],
)
def test_extracts_sql(raw: str) -> None:
    assert parse_llm_output(raw).lower().startswith(("select", "with"))


def test_cannot_answer_with_reason() -> None:
    with pytest.raises(CannotAnswerError, match="nope"):
        parse_llm_output('{"error": "cannot_answer", "reason": "nope"}')


def test_cannot_answer_without_reason() -> None:
    with pytest.raises(CannotAnswerError):
        parse_llm_output('{"error": "cannot_answer"}')


@pytest.mark.parametrize("raw", ["hello there", "{not json", "[1, 2]", '"x"'])
def test_garbage_raises_llm_error(raw: str) -> None:
    with pytest.raises(LlmError):
        parse_llm_output(raw)
