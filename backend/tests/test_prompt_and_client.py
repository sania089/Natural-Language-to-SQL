from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.errors import LlmError, LlmRateLimitError, LlmTimeoutError
from app.services.llm.client import ChatMessage, OpenAICompatClient, build_llm_client
from app.services.pipeline import get_schema_block
from app.services.prompt_builder import build_messages, wrap_question

MSGS = [ChatMessage(role="user", content="hi")]


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


def _client(script: list[Any]) -> tuple[OpenAICompatClient, list[httpx.Request], list[float]]:
    """Client wired to a MockTransport that plays `script` (Response or Exception) in order."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        item = script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item  # type: ignore[no-any-return]

    sleeps: list[float] = []
    client = OpenAICompatClient(
        api_key="k",
        base_url="https://llm.test/v1/",
        model="m",
        sleep=sleeps.append,
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return client, seen, sleeps


def _ok(content: str | None = "ok") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_success_first_try_sends_auth_and_model() -> None:
    c, seen, sleeps = _client([_ok()])
    assert c.complete(MSGS) == "ok" and len(seen) == 1 and sleeps == []
    assert str(seen[0].url) == "https://llm.test/v1/chat/completions"
    assert seen[0].headers["Authorization"] == "Bearer k"


def test_retries_with_backoff_then_succeeds() -> None:
    c, seen, sleeps = _client([httpx.ReadTimeout("t"), httpx.Response(503), _ok()])
    assert c.complete(MSGS) == "ok"
    assert len(seen) == 3 and sleeps == [1.0, 2.0]


def test_rate_limit_exhausts_retries() -> None:
    c, seen, _ = _client([httpx.Response(429)] * 3)
    with pytest.raises(LlmRateLimitError):
        c.complete(MSGS)
    assert len(seen) == 3


def test_timeout_typed() -> None:
    c, _, _ = _client([httpx.ReadTimeout("t")] * 3)
    with pytest.raises(LlmTimeoutError):
        c.complete(MSGS)


def test_connection_error_typed() -> None:
    c, _, _ = _client([httpx.ConnectError("down")] * 3)
    with pytest.raises(LlmError):
        c.complete(MSGS)


def test_client_error_not_retried() -> None:
    c, seen, _ = _client([httpx.Response(401)])
    with pytest.raises(LlmError):
        c.complete(MSGS)
    assert len(seen) == 1


@pytest.mark.parametrize(
    "response",
    [_ok(None), _ok(""), httpx.Response(200, text="not json"), httpx.Response(200, json={})],
)
def test_bad_payload_is_error(response: httpx.Response) -> None:
    c, _, _ = _client([response] * 3)
    with pytest.raises(LlmError):
        c.complete(MSGS)


def test_build_client_requires_key() -> None:
    with pytest.raises(LlmError):
        build_llm_client(Settings(gemini_api_key=""))  # type: ignore[arg-type]
    assert build_llm_client(Settings(llm_provider="groq", groq_api_key="x"))  # type: ignore[arg-type]
