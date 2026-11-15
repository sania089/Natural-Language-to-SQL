from pathlib import Path

from app.services.answer_cache import AnswerCache, cache_key
from app.services.executor import QueryResult
from app.services.pipeline import AskResult


def _result(sql: str) -> AskResult:
    qr = QueryResult(columns=[], rows=[], row_count=0, truncated=False, elapsed_ms=0)
    return AskResult(sql=sql, result=qr)


def test_key_ignores_case_and_whitespace_but_not_database() -> None:
    db = Path("a.db")
    assert cache_key(db, "Top  Customers ") == cache_key(db, "top customers")
    assert cache_key(db, "x") != cache_key(Path("b.db"), "x")


def test_evicts_least_recently_used() -> None:
    cache = AnswerCache(2)
    cache.put("a", _result("A"))
    cache.put("b", _result("B"))
    assert cache.get("a") is not None  # touch "a" so "b" is now oldest
    cache.put("c", _result("C"))
    assert cache.get("b") is None
    assert cache.get("a") is not None and cache.get("c") is not None


def test_zero_size_stores_nothing() -> None:
    cache = AnswerCache(0)
    cache.put("a", _result("A"))
    assert cache.get("a") is None
