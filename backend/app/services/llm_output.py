"""Parse the model's reply into a SQL string. Output is untrusted until validated."""

import json
import re

from app.errors import CannotAnswerError, LlmError

_FENCE = re.compile(r"```(?:sql|json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_SQL_START = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def parse_llm_output(raw: str) -> str:
    """Return candidate SQL, or raise CannotAnswerError / LlmError."""
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    if text.startswith("{"):
        return _from_json(text)
    if _SQL_START.match(text):
        return text
    raise LlmError("The language model returned an unrecognised response.")


def _from_json(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmError("The language model returned malformed JSON.") from exc
    sql = data.get("sql")
    if isinstance(sql, str) and sql.strip():
        return sql.strip()
    reason = data.get("reason")
    raise CannotAnswerError(
        reason if isinstance(reason, str) and reason else "That can't be answered from this data."
    )
