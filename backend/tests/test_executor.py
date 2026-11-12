from pathlib import Path

import pytest

from app.errors import QueryFailedError, QueryTimeoutError
from app.services.executor import execute_query


def test_returns_columns_rows_timing(seeded_db: Path) -> None:
    r = execute_query(seeded_db, "SELECT id, name FROM categories", max_rows=100, timeout_seconds=5)
    assert r.columns == ["id", "name"] and r.row_count == len(r.rows) > 0
    assert not r.truncated and r.elapsed_ms >= 0


def test_row_cap_sets_truncated(seeded_db: Path) -> None:
    r = execute_query(seeded_db, "SELECT id FROM customers", max_rows=3, timeout_seconds=5)
    assert r.row_count == 3 and r.truncated


def test_timeout(seeded_db: Path) -> None:
    sql = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(QueryTimeoutError):
        execute_query(seeded_db, sql, max_rows=10, timeout_seconds=0.2)


def test_runtime_error_is_query_failed(seeded_db: Path) -> None:
    with pytest.raises(QueryFailedError) as info:
        execute_query(seeded_db, "SELECT nope FROM customers", max_rows=10, timeout_seconds=5)
    assert "nope" in info.value.extra["detail"]


def test_writes_fail_on_readonly_connection(seeded_db: Path) -> None:
    with pytest.raises(QueryFailedError):
        execute_query(seeded_db, "DELETE FROM customers", max_rows=10, timeout_seconds=5)


def test_blob_is_hex_encoded(seeded_db: Path) -> None:
    r = execute_query(seeded_db, "SELECT x'ff' AS b", max_rows=1, timeout_seconds=5)
    assert r.rows == [["ff"]]
