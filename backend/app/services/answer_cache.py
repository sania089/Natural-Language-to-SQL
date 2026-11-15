"""Thread-safe LRU cache of successful answers, so repeat questions skip the LLM entirely."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pipeline imports this module, so import the type only for checkers
    from app.services.pipeline import AskResult


def cache_key(db_path: Path, question: str) -> str:
    """Case/whitespace-insensitive key, scoped to the database file."""
    normalized = re.sub(r"\s+", " ", question).strip().lower()
    return f"{db_path}\x00{normalized}"


class AnswerCache:
    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._items: OrderedDict[str, AskResult] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> AskResult | None:
        with self._lock:
            result = self._items.get(key)
            if result is not None:
                self._items.move_to_end(key)
            return result

    def put(self, key: str, result: AskResult) -> None:
        if self._max_size <= 0:
            return
        with self._lock:
            self._items[key] = result
            self._items.move_to_end(key)
            while len(self._items) > self._max_size:
                self._items.popitem(last=False)
