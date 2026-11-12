"""Schema introspection: reads the live SQLite catalog into typed, immutable models."""

import sqlite3
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.db.connection import connect_readonly


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ForeignKey(_Frozen):
    column: str
    ref_table: str
    ref_column: str


class ColumnInfo(_Frozen):
    name: str
    type: str
    nullable: bool
    primary_key: bool


class TableInfo(_Frozen):
    name: str
    columns: tuple[ColumnInfo, ...]
    foreign_keys: tuple[ForeignKey, ...] = ()

    @property
    def column_names(self) -> frozenset[str]:
        return frozenset(c.name.lower() for c in self.columns)


class SchemaInfo(_Frozen):
    tables: tuple[TableInfo, ...]

    def table(self, name: str) -> TableInfo | None:
        """Case-insensitive lookup (SQLite identifiers are case-insensitive)."""
        lowered = name.lower()
        return next((t for t in self.tables if t.name.lower() == lowered), None)

    @property
    def table_names(self) -> frozenset[str]:
        return frozenset(t.name.lower() for t in self.tables)


def introspect_schema(conn: sqlite3.Connection) -> SchemaInfo:
    """Read user tables (never `sqlite_*` internals) with columns and foreign keys."""
    names = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND substr(name, 1, 7) != 'sqlite_' ORDER BY name"
        )
    ]
    return SchemaInfo(tables=tuple(_introspect_table(conn, n) for n in names))


def _introspect_table(conn: sqlite3.Connection, name: str) -> TableInfo:
    quoted = '"' + name.replace('"', '""') + '"'
    columns = tuple(
        ColumnInfo(name=r[1], type=r[2] or "", nullable=not (r[3] or r[5]), primary_key=bool(r[5]))
        for r in conn.execute(f"PRAGMA table_info({quoted})")  # noqa: S608
    )
    fks = tuple(
        ForeignKey(column=r[3], ref_table=r[2], ref_column=r[4])
        for r in conn.execute(f"PRAGMA foreign_key_list({quoted})")  # noqa: S608
    )
    return TableInfo(name=name, columns=columns, foreign_keys=fks)


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def collect_samples(
    conn: sqlite3.Connection,
    schema: SchemaInfo,
    *,
    max_distinct: int = 10,
    per_column: int = 3,
) -> dict[tuple[str, str], tuple[str, ...]]:
    """Sample values for low-cardinality TEXT columns, to help the LLM match real values."""
    samples: dict[tuple[str, str], tuple[str, ...]] = {}
    for table in schema.tables:
        for col in table.columns:
            if col.type.upper() != "TEXT" or col.primary_key:
                continue
            t, c = _quote(table.name), _quote(col.name)
            query = (
                f"SELECT DISTINCT {c} FROM {t} WHERE {c} IS NOT NULL "  # noqa: S608
                f"ORDER BY {c} LIMIT {max_distinct + 1}"
            )
            rows = conn.execute(query).fetchall()
            if 0 < len(rows) <= max_distinct:
                samples[(table.name, col.name)] = tuple(str(r[0]) for r in rows[:per_column])
    return samples


@lru_cache(maxsize=8)
def get_schema(db_path: Path) -> SchemaInfo:
    """Introspect once per database file and cache for the process lifetime."""
    conn = connect_readonly(db_path)
    try:
        return introspect_schema(conn)
    finally:
        conn.close()
