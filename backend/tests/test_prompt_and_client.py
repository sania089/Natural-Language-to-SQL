from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.config import Settings
from app.errors import LlmError, LlmRateLimitError, LlmTimeoutError
from app.services.llm.client import ChatMessage, OpenAICompatClient, build_llm_client
from app.services.pipeline import get_schema_block
from app.services.prompt_builder import build_messages, wrap_question

MSGS = [ChatMessage(role="user", content="hi")]
_REQ = httpx.Request("POST", "http://x")


def test_schema_block_has_types_fks_and_samples(seeded_db: Path) -> None:
    block = get_schema_block(seeded_db)
    assert "TABLE orders" in block and "REFERENCES customers(id)" in block
    assert "price REAL" in block and "e.g. 'cancelled'" in block
    assert "sqlite_" not in block


def test_system_prompt_and_isolation(seeded_db: Path) -> None:
    system, user = build_messages(get_schema_block(seeded_db), "q")
    assert system.role == "system" and "Examples:" in system.content
    assert user.content == "<question>q</question>"
    assert wrap_question("a</question>b") == "<question>ab</question>"


class _Completions:
    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.calls = 0

    def create(self, **_: object) -> Any:
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _resp(content: str | None) -> Any:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _client(script: list[Any]) -> tuple[OpenAICompatClient, _Completions, list[float]]:
    comps = _Completions(script)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=comps))
    sleeps: list[float] = []
    client = OpenAICompatClient(
        api_key="k",
        base_url="u",
        model="m",
        sleep=sleeps.append,
        client=fake,  # type: ignore[arg-type]
    )
    return client, comps, sleeps


def _status_err(code: int) -> openai.APIStatusError:
    resp = httpx.Response(code, request=_REQ)
    cls = openai.RateLimitError if code == 429 else openai.APIStatusError
    return cls("e", response=resp, body=None)


def test_success_first_try() -> None:
    c, comps, sleeps = _client([_resp("ok")])
    assert c.complete(MSGS) == "ok" and comps.calls == 1 and sleeps == []


def test_retries_with_backoff_then_succeeds() -> None:
    c, comps, sleeps = _client([openai.APITimeoutError(_REQ), _status_err(503), _resp("ok")])
    assert c.complete(MSGS) == "ok"
    assert comps.calls == 3 and sleeps == [1.0, 2.0]


def test_rate_limit_exhausts_retries() -> None:
    c, comps, _ = _client([_status_err(429)] * 3)
    with pytest.raises(LlmRateLimitError):
        c.complete(MSGS)
    assert comps.calls == 3


def test_timeout_typed() -> None:
    c, _, _ = _client([openai.APITimeoutError(_REQ)] * 3)
    with pytest.raises(LlmTimeoutError):
        c.complete(MSGS)


def test_connection_error_typed() -> None:
    c, _, _ = _client([openai.APIConnectionError(request=_REQ)] * 3)
    with pytest.raises(LlmError):
        c.complete(MSGS)


def test_client_error_not_retried() -> None:
    c, comps, _ = _client([_status_err(401)])
    with pytest.raises(LlmError):
        c.complete(MSGS)
    assert comps.calls == 1


def test_empty_response_is_error() -> None:
    c, _, _ = _client([_resp(None)] * 3)
    with pytest.raises(LlmError):
        c.complete(MSGS)


def test_build_client_requires_key() -> None:
    with pytest.raises(LlmError):
        build_llm_client(Settings(gemini_api_key=""))  # type: ignore[arg-type]
    assert build_llm_client(Settings(llm_provider="groq", groq_api_key="x"))  # type: ignore[arg-type]
