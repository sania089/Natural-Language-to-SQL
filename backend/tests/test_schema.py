from pathlib import Path

import pytest

from app.db.connection import connect_readonly
from app.services.schema import SchemaInfo, get_schema, introspect_schema


@pytest.fixture
def schema(seeded_db: Path) -> SchemaInfo:
    conn = connect_readonly(seeded_db)
    try:
        return introspect_schema(conn)
    finally:
        conn.close()


def test_lists_all_user_tables(schema: SchemaInfo) -> None:
    assert schema.table_names == {"categories", "customers", "products", "orders", "order_items"}


def test_excludes_sqlite_internal_tables(schema: SchemaInfo) -> None:
    assert not any(name.startswith("sqlite_") for name in schema.table_names)


def test_columns_carry_type_and_primary_key(schema: SchemaInfo) -> None:
    customers = schema.table("customers")
    assert customers is not None
    by_name = {c.name: c for c in customers.columns}
    assert by_name["id"].primary_key
    assert by_name["email"].type == "TEXT"
    assert not by_name["email"].nullable
    assert "country" in customers.column_names


def test_foreign_keys_are_introspected(schema: SchemaInfo) -> None:
    orders = schema.table("orders")
    assert orders is not None
    assert {(fk.column, fk.ref_table, fk.ref_column) for fk in orders.foreign_keys} == {
        ("customer_id", "customers", "id")
    }


def test_table_lookup_is_case_insensitive(schema: SchemaInfo) -> None:
    assert schema.table("CuStOmErS") is not None
    assert schema.table("missing") is None


def test_get_schema_is_cached_per_path(seeded_db: Path) -> None:
    assert get_schema(seeded_db) is get_schema(seeded_db)


def test_get_schema_missing_db_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        get_schema(tmp_path / "nope.db")
