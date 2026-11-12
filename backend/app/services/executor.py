"""Execute validated SQL on a read-only connection with a wall-clock timeout and row cap."""

import sqlite3
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.db.connection import connect_readonly
from app.errors import QueryFailedError, QueryTimeoutError

_PROGRESS_STEPS = 10_000  # SQLite VM instructions between timeout checks


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    elapsed_ms: float


def _cell(value: Any) -> Any:
    return value.hex() if isinstance(value, bytes) else value


def execute_query(db_path: Path, sql: str, *, max_rows: int, timeout_seconds: float) -> QueryResult:
    conn = connect_readonly(db_path)
    start = time.perf_counter()
    deadline = start + timeout_seconds
    conn.set_progress_handler(lambda: 1 if time.perf_counter() > deadline else 0, _PROGRESS_STEPS)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description or ()]
        fetched = cursor.fetchmany(max_rows + 1)
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc).lower():
            raise QueryTimeoutError(
                f"The query took longer than {timeout_seconds:g}s and was stopped."
            ) from exc
        raise _failed(exc) from exc
    except sqlite3.Error as exc:
        raise _failed(exc) from exc
    finally:
        conn.close()
    rows = [[_cell(v) for v in row] for row in fetched[:max_rows]]
    return QueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=len(fetched) > max_rows,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
    )


def _failed(exc: sqlite3.Error) -> QueryFailedError:
    # `detail` feeds the repair prompt only; the HTTP layer never exposes `extra`.
    return QueryFailedError("The query could not be executed.", extra={"detail": str(exc)})
