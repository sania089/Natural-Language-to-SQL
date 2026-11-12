import sqlite3
from pathlib import Path

import pytest

from app.db.connection import connect_readonly
from app.db.seed import seed_database

TABLES = ["categories", "customers", "products", "orders", "order_items"]
TOTAL_SQL = "SELECT SUM(quantity * unit_price) FROM order_items"


@pytest.mark.parametrize("table", TABLES)
def test_tables_populated(seeded_db: Path, table: str) -> None:
    conn = connect_readonly(seeded_db)
    assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0  # noqa: S608


def test_readonly_connection_rejects_writes(seeded_db: Path) -> None:
    conn = connect_readonly(seeded_db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM customers")


def test_readonly_missing_db_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        connect_readonly(tmp_path / "nope.db")


def test_seed_is_deterministic(tmp_path: Path) -> None:
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    seed_database(a)
    seed_database(b)
    total_a = connect_readonly(a).execute(TOTAL_SQL).fetchone()[0]
    total_b = connect_readonly(b).execute(TOTAL_SQL).fetchone()[0]
    assert total_a == total_b


def test_seed_refuses_overwrite_without_force(tmp_path: Path) -> None:
    path = tmp_path / "x.db"
    seed_database(path)
    with pytest.raises(FileExistsError):
        seed_database(path)
    seed_database(path, force=True)
