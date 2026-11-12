"""LLM client abstraction. Gemini and Groq both expose OpenAI-compatible endpoints."""

import logging
import time
from collections.abc import Callable
from typing import Literal, Protocol

import openai
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.errors import LlmError, LlmRateLimitError, LlmTimeoutError

log = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
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
        client: openai.OpenAI | None = None,
    ) -> None:
        self._model = model
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._client = client or openai.OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0
        )

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
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[m.model_dump() for m in messages],  # type: ignore[misc]
                temperature=0,
            )
        except openai.APITimeoutError as exc:
            raise LlmTimeoutError("The language model timed out.") from exc
        except openai.RateLimitError as exc:
            raise LlmRateLimitError("The language model is rate limited. Try again soon.") from exc
        except openai.APIConnectionError as exc:
            raise LlmError("Could not reach the language model.") from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LlmError("The language model had a server error.") from exc
            raise _FatalLlmError("The language model rejected the request.") from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
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
