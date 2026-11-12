"""LLM client abstraction. Gemini and Groq both expose OpenAI-compatible endpoints.

Uses plain httpx (pure Python) rather than the `openai` SDK, which pulls in native
extensions that some locked-down machines refuse to load.
"""

import logging
import time
from collections.abc import Callable
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.errors import LlmError, LlmRateLimitError, LlmTimeoutError

log = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class LlmClient(Protocol):
    def complete(self, messages: list[ChatMessage]) -> str: ...


class _FatalLlmError(LlmError):
    """Non-retryable provider error (e.g. bad API key)."""


class OpenAICompatClient:
    """Chat-completions client with timeout, bounded retries and exponential backoff."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 20.0,
        max_attempts: int = 3,
        backoff_base: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        http: httpx.Client | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._http = http or httpx.Client(timeout=timeout)

    def complete(self, messages: list[ChatMessage]) -> str:
        attempt = 0
        while True:
            try:
                return self._call(messages)
            except _FatalLlmError:
                raise
            except LlmError:
                attempt += 1
                if attempt >= self._max_attempts:
                    raise
                log.warning("llm call failed, retrying", extra={"attempt": attempt})
                self._sleep(self._backoff_base * 2 ** (attempt - 1))

    def _call(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self._model,
            "messages": [m.model_dump() for m in messages],
            "temperature": 0,
        }
        try:
            response = self._http.post(self._url, json=payload, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("The language model timed out.") from exc
        except httpx.TransportError as exc:
            raise LlmError("Could not reach the language model.") from exc
        _raise_for_status(response)
        return _extract_content(response)


def _raise_for_status(response: httpx.Response) -> None:
    status = response.status_code
    if status < 400:
        return
    log.warning("llm http error", extra={"status": status})
    if status == 429:
        raise LlmRateLimitError("The language model is rate limited. Try again soon.")
    if status >= 500:
        raise LlmError("The language model had a server error.")
    raise _FatalLlmError("The language model rejected the request (check the API key and model).")


def _extract_content(response: httpx.Response) -> str:
    try:
        data: Any = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LlmError("The language model returned an unexpected response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmError("The language model returned an empty response.")
    return content


def build_llm_client(settings: Settings) -> LlmClient:
    if settings.llm_provider == "gemini":
        key, url, model = settings.gemini_api_key, GEMINI_BASE_URL, settings.gemini_model
    else:
        key, url, model = settings.groq_api_key, GROQ_BASE_URL, settings.groq_model
    if not key.get_secret_value():
        raise LlmError(f"No API key configured for provider '{settings.llm_provider}'.")
    return OpenAICompatClient(api_key=key.get_secret_value(), base_url=url, model=model)
