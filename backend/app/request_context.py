"""Per-request ID, propagated via a contextvar so logs can include it."""

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
