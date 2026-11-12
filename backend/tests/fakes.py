import json

from app.errors import AppError
from app.services.llm.client import ChatMessage


class FakeLlmClient:
    """Returns scripted replies in order; an AppError instance in the script is raised."""

    def __init__(self, *replies: str | AppError) -> None:
        self._replies = list(replies)
        self.calls: list[list[ChatMessage]] = []

    def complete(self, messages: list[ChatMessage]) -> str:
        self.calls.append(list(messages))
        reply = self._replies.pop(0)
        if isinstance(reply, AppError):
            raise reply
        return reply


def sql_reply(sql: str) -> str:
    return json.dumps({"sql": sql})
