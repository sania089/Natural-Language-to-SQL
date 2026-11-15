"""Global per-day cap on LLM calls, so a shared link cannot drain a free-tier key."""

import threading
from collections.abc import Callable
from datetime import UTC, date, datetime

from app.errors import DailyLimitReachedError


def _today_utc() -> date:
    return datetime.now(UTC).date()


class DailyBudget:
    """In-memory counter that resets at UTC midnight. `limit <= 0` disables the cap."""

    def __init__(self, limit: int, today: Callable[[], date] = _today_utc) -> None:
        self._limit = limit
        self._today = today
        self._day = today()
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> None:
        """Reserve one LLM call or raise `DailyLimitReachedError`."""
        if self._limit <= 0:
            return
        with self._lock:
            today = self._today()
            if today != self._day:
                self._day, self._used = today, 0
            if self._used >= self._limit:
                raise DailyLimitReachedError(
                    "The daily question limit has been reached. Please try again tomorrow."
                )
            self._used += 1
