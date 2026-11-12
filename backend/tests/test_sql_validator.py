"""Validator tests: every legit sample passes (and executes), every malicious sample is rejected."""

from pathlib import Path

import pytest

from app.db.connection import connect_readonly
from app.services.schema import SchemaInfo, get_schema
from app.services.sql_validator import Rule, ValidationResult, validate_sql

MAX_ROWS = 200

LEGIT_QUERIES = [
    "SELECT * FROM customers",
    "SELECT first_name, last_name FROM customers WHERE country = 'Germany'",
    "select FIRST_NAME from CUSTOMERS",
    "SELECT c.first_name, o.status FROM customers c JOIN orders o ON o.customer_id = c.id",
    "SELECT c.id, SUM(oi.quantity * oi.unit_price) AS spend FROM customers c "
    "JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
    "GROUP BY c.id ORDER BY spend DESC LIMIT 5",
    "SELECT country, COUNT(*) AS n FROM customers GROUP BY country HAVING COUNT(*) > 1",
    "SELECT COUNT(DISTINCT customer_id) FROM orders",
    "SELECT AVG(price), MIN(price), MAX(price), SUM(stock), TOTAL(stock) FROM products",
    "SELECT MAX(price, stock), MIN(price, stock) FROM products",
    "SELECT ROUND(price, 1), ABS(price), CEIL(price), FLOOR(price) FROM products",
    "SELECT UPPER(first_name), LOWER(last_name), LENGTH(email), TRIM(city) FROM customers",
    "SELECT SUBSTR(email, 1, 3), REPLACE(city, 'a', 'b'), INSTR(email, '@') FROM customers",
    "SELECT first_name || ' ' || last_name AS full_name FROM customers",
    "SELECT COALESCE(city, 'n/a'), IFNULL(city, 'n/a'), NULLIF(city, ''), IIF(id > 1, 1, 0) "
    "FROM customers",
    "SELECT CASE WHEN price > 100 THEN 'high' ELSE 'low' END AS tier FROM products",
    "SELECT CAST(price AS INTEGER), TYPEOF(price) FROM products",
    "SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) FROM orders GROUP BY month",
    "SELECT date(order_date), datetime(order_date), time(order_date), julianday(order_date) "
    "FROM orders",
    "SELECT date('now'), date('now', '-30 days'), CURRENT_DATE, CURRENT_TIMESTAMP",
    "SELECT * FROM orders WHERE order_date >= date('now', 'start of month')",
    "SELECT GROUP_CONCAT(name) FROM categories",
    "SELECT * FROM products WHERE price BETWEEN 10 AND 50 AND name LIKE '%a%'",
    "SELECT * FROM products WHERE category_id IN (SELECT id FROM categories WHERE name = 'x')",
    "SELECT * FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)",
    "SELECT * FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)",
    "SELECT s.country FROM (SELECT country, COUNT(*) AS n FROM customers GROUP BY country) AS s "
    "WHERE s.n > 3",
    "WITH t AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) "
    "SELECT * FROM t ORDER BY n DESC",
    "WITH t(cid, n) AS (SELECT customer_id, COUNT(*) FROM orders GROUP BY 1) SELECT cid, n FROM t",
    "WITH a AS (SELECT id FROM customers), b AS (SELECT id FROM a) SELECT id FROM b",
    "SELECT country FROM customers UNION SELECT city FROM customers",
    "SELECT id FROM customers UNION ALL SELECT id FROM orders",
    "SELECT id FROM customers EXCEPT SELECT customer_id FROM orders",
    "SELECT id FROM customers INTERSECT SELECT customer_id FROM orders",
    "(SELECT id FROM customers)",
    "SELECT id FROM customers;",
    "SELECT * FROM customers ORDER BY created_at DESC LIMIT 10 OFFSET 5",
    "SELECT id, ROW_NUMBER() OVER (PARTITION BY country ORDER BY created_at) FROM customers",
    "SELECT id, RANK() OVER (ORDER BY created_at), LAG(id) OVER (ORDER BY id) FROM customers",
    "SELECT * FROM orders WHERE status = 'shipped' AND order_date > '2024-01-01' OR id = 1",
    "SELECT * FROM orders WHERE NOT (status = 'shipped' OR status = 'pending')",
    "SELECT 1",
    "SELECT 'it''s -- not a comment /* really */'",
    'SELECT "first_name" FROM "customers"',
    "SELECT c.* FROM customers c",
    "SELECT COUNT(*) FROM customers a CROSS JOIN customers b LIMIT 1",
]

# (id, sql, expected rule)
MALICIOUS: list[tuple[str, str, Rule]] = [
    # empty / size / characters
    ("empty", "", Rule.EMPTY),
    ("whitespace", "   \n\t ", Rule.EMPTY),
    ("only-semicolon", ";", Rule.EMPTY),
    ("huge", "SELECT 1 FROM customers WHERE id IN (" + ",".join(["1"] * 2000) + ")", Rule.TOO_LONG),
    ("nul-byte", "SELECT 1\x00; DROP TABLE customers", Rule.ILLEGAL_CHARS),
    ("control-char", "SELECT\x0b1", Rule.ILLEGAL_CHARS),
    ("unterminated-string", "SELECT 'abc", Rule.SYNTAX),
    ("garbage", "SELECT FROM WHERE", Rule.SYNTAX),
    ("prose", "please show me all customers", Rule.SYNTAX),
    # stacked queries
    ("stacked-drop", "SELECT 1; DROP TABLE customers", Rule.MULTIPLE_STATEMENTS),
    ("stacked-select", "SELECT 1; SELECT 2", Rule.MULTIPLE_STATEMENTS),
    ("stacked-delete", "SELECT * FROM customers; DELETE FROM customers", Rule.MULTIPLE_STATEMENTS),
    ("drop-first", "DROP TABLE customers; SELECT 1", Rule.MULTIPLE_STATEMENTS),
    # comments
    ("line-comment", "SELECT 1 -- trailing", Rule.COMMENTS),
    ("block-comment", "SELECT /* x */ 1", Rule.COMMENTS),
    ("comment-hides-stack", "SELECT 1 /*; DROP TABLE customers; */", Rule.COMMENTS),
    ("comment-splits-keyword", "SELECT * FROM customers WHERE 1=1 -- AND id=1", Rule.COMMENTS),
    ("hash-style-comment-select", "SELECT/**/1", Rule.COMMENTS),
    # non-select roots
    ("delete", "DELETE FROM customers", Rule.NOT_SELECT),
    ("delete-where", "DELETE FROM customers WHERE id = 1", Rule.NOT_SELECT),
    ("update", "UPDATE customers SET email = 'x'", Rule.NOT_SELECT),
    ("insert", "INSERT INTO categories (name) VALUES ('x')", Rule.NOT_SELECT),
    ("insert-select", "INSERT INTO categories SELECT * FROM categories", Rule.NOT_SELECT),
    ("replace", "REPLACE INTO categories VALUES (1, 'x')", Rule.NOT_SELECT),
    ("drop", "DROP TABLE customers", Rule.NOT_SELECT),
    ("create", "CREATE TABLE x (a INT)", Rule.NOT_SELECT),
    ("create-as", "CREATE TABLE x AS SELECT * FROM customers", Rule.NOT_SELECT),
    ("alter", "ALTER TABLE customers ADD COLUMN x INT", Rule.NOT_SELECT),
    ("truncate", "TRUNCATE TABLE customers", Rule.NOT_SELECT),
    ("pragma", "PRAGMA table_info(customers)", Rule.NOT_SELECT),
    ("pragma-write", "PRAGMA writable_schema = 1", Rule.NOT_SELECT),
    ("attach", "ATTACH DATABASE 'evil.db' AS evil", Rule.NOT_SELECT),
    ("detach", "DETACH DATABASE main", Rule.NOT_SELECT),
    ("vacuum", "VACUUM", Rule.NOT_SELECT),
    ("vacuum-into", "VACUUM INTO 'copy.db'", Rule.NOT_SELECT),
    ("explain", "EXPLAIN SELECT * FROM customers", Rule.NOT_SELECT),
    ("explain-plan", "EXPLAIN QUERY PLAN SELECT * FROM customers", Rule.NOT_SELECT),
    ("begin", "BEGIN", Rule.NOT_SELECT),
    ("commit", "COMMIT", Rule.NOT_SELECT),
    ("reindex", "REINDEX", Rule.NOT_SELECT),
    ("analyze", "ANALYZE", Rule.NOT_SELECT),
    ("with-delete", "WITH x AS (SELECT 1) DELETE FROM customers", Rule.NOT_SELECT),
    (
        "with-insert",
        "WITH x AS (SELECT 1) INSERT INTO categories SELECT * FROM categories",
        Rule.NOT_SELECT,
    ),
    ("with-update", "WITH x AS (SELECT 1) UPDATE customers SET email = 'x'", Rule.NOT_SELECT),
    # case / whitespace / unicode obfuscation
    ("mixed-case-drop", "dRoP tAbLe customers", Rule.NOT_SELECT),
    ("newline-drop", "DROP\nTABLE\ncustomers", Rule.NOT_SELECT),
    ("tab-delete", "DELETE\tFROM\tcustomers", Rule.NOT_SELECT),
    ("leading-space-delete", "   \n  DELETE FROM customers", Rule.NOT_SELECT),
    ("fullwidth-select", "ＳＥＬＥＣＴ 1", Rule.SYNTAX),
    ("zero-width-space", "SEL​ECT * FROM customers", Rule.SYNTAX),
    ("nbsp-drop", "DROP TABLE customers", Rule.NOT_SELECT),
    ("homoglyph-table", "SELECT * FROM custοmers", Rule.UNKNOWN_TABLE),
    # system tables & schema qualification
    ("sqlite-master", "SELECT * FROM sqlite_master", Rule.SYSTEM_TABLE),
    ("sqlite-master-upper", "SELECT * FROM SQLITE_MASTER", Rule.SYSTEM_TABLE),
    ("sqlite-schema", "SELECT sql FROM sqlite_schema", Rule.SYSTEM_TABLE),
    ("sqlite-sequence", "SELECT * FROM sqlite_sequence", Rule.SYSTEM_TABLE),
    ("sqlite-stat1", "SELECT * FROM sqlite_stat1", Rule.SYSTEM_TABLE),
    ("quoted-sqlite-master", 'SELECT * FROM "sqlite_master"', Rule.SYSTEM_TABLE),
    ("main-qualified", "SELECT * FROM main.customers", Rule.QUALIFIED_TABLE),
    ("main-master", "SELECT * FROM main.sqlite_master", Rule.QUALIFIED_TABLE),
    ("temp-master", "SELECT * FROM temp.sqlite_master", Rule.QUALIFIED_TABLE),
    ("attached-qualified", "SELECT * FROM evil.secrets", Rule.QUALIFIED_TABLE),
    # union exfiltration
    (
        "union-master",
        "SELECT id FROM customers UNION SELECT name FROM sqlite_master",
        Rule.SYSTEM_TABLE,
    ),
    (
        "union-all-master",
        "SELECT id FROM customers UNION ALL SELECT sql FROM sqlite_master",
        Rule.SYSTEM_TABLE,
    ),
    (
        "union-unknown-table",
        "SELECT id FROM customers UNION SELECT id FROM users",
        Rule.UNKNOWN_TABLE,
    ),
    ("subquery-master", "SELECT (SELECT sql FROM sqlite_master LIMIT 1)", Rule.SYSTEM_TABLE),
    (
        "where-subquery-master",
        "SELECT * FROM customers WHERE id IN (SELECT rootpage FROM sqlite_master)",
        Rule.SYSTEM_TABLE,
    ),
    ("cte-master", "WITH m AS (SELECT * FROM sqlite_master) SELECT * FROM m", Rule.SYSTEM_TABLE),
    ("join-master", "SELECT * FROM customers c JOIN sqlite_master m ON 1=1", Rule.SYSTEM_TABLE),
    # unknown tables / columns
    ("unknown-table", "SELECT * FROM users", Rule.UNKNOWN_TABLE),
    ("unknown-column", "SELECT password FROM customers", Rule.UNKNOWN_COLUMN),
    ("unknown-qualified-column", "SELECT c.password FROM customers c", Rule.UNKNOWN_COLUMN),
    ("wrong-table-column", "SELECT o.email FROM orders o", Rule.UNKNOWN_COLUMN),
    ("unknown-qualifier", "SELECT x.id FROM customers", Rule.UNKNOWN_COLUMN),
    ("where-unknown-column", "SELECT id FROM customers WHERE secret = 1", Rule.UNKNOWN_COLUMN),
    ("rowid", "SELECT rowid FROM customers", Rule.UNKNOWN_COLUMN),
    ("column-without-table", "SELECT password", Rule.UNKNOWN_COLUMN),
    # table-valued / dangerous functions
    ("pragma-func", "SELECT * FROM pragma_table_info('customers')", Rule.TABLE_FUNCTION),
    ("pragma-func-join", "SELECT * FROM customers, pragma_database_list()", Rule.TABLE_FUNCTION),
    ("json-each", "SELECT * FROM json_each('[1,2]')", Rule.TABLE_FUNCTION),
    ("generate-series", "SELECT * FROM generate_series(1, 1000000000)", Rule.TABLE_FUNCTION),
    ("load-extension", "SELECT load_extension('/tmp/evil.so')", Rule.FUNCTION_NOT_ALLOWED),
    ("readfile", "SELECT readfile('/etc/passwd')", Rule.FUNCTION_NOT_ALLOWED),
    ("writefile", "SELECT writefile('/tmp/x', 'y')", Rule.FUNCTION_NOT_ALLOWED),
    ("randomblob-dos", "SELECT randomblob(1000000000)", Rule.FUNCTION_NOT_ALLOWED),
    ("zeroblob-dos", "SELECT zeroblob(1000000000)", Rule.FUNCTION_NOT_ALLOWED),
    ("sqlite-version", "SELECT sqlite_version()", Rule.FUNCTION_NOT_ALLOWED),
    ("sqlite-source-id", "SELECT sqlite_source_id()", Rule.FUNCTION_NOT_ALLOWED),
    ("printf-dos", "SELECT printf('%1000000000d', 1)", Rule.FUNCTION_NOT_ALLOWED),
    ("fts-match-fn", "SELECT fts3_tokenizer('x')", Rule.FUNCTION_NOT_ALLOWED),
    (
        "func-in-where",
        "SELECT id FROM customers WHERE load_extension('x')",
        Rule.FUNCTION_NOT_ALLOWED,
    ),
    ("func-in-subquery", "SELECT (SELECT readfile('x'))", Rule.FUNCTION_NOT_ALLOWED),
    ("typed-unlisted-func", "SELECT MD5(email) FROM customers", Rule.FUNCTION_NOT_ALLOWED),
    # DoS shapes
    (
        "recursive-cte",
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT n FROM r",
        Rule.RECURSIVE_CTE,
    ),
    ("select-into", "SELECT * INTO backup FROM customers", Rule.FORBIDDEN_OPERATION),
]


@pytest.fixture(scope="module")
def schema(seeded_db: Path) -> SchemaInfo:
    return get_schema(seeded_db)


def check(sql: str, schema: SchemaInfo, **kwargs: int) -> ValidationResult:
    kwargs.setdefault("max_rows", MAX_ROWS)
    return validate_sql(sql, schema, **kwargs)


@pytest.mark.parametrize("sql", LEGIT_QUERIES)
def test_legit_queries_pass_and_execute(sql: str, schema: SchemaInfo, seeded_db: Path) -> None:
    result = check(sql, schema)
    assert result.ok, f"{result.rule}: {result.reason}"
    assert result.sql_normalized is not None
    assert result.rule is None
    assert result.reason is None
    # the normalized SQL must be valid SQLite and run on the read-only connection
    conn = connect_readonly(seeded_db)
    try:
        rows = conn.execute(result.sql_normalized).fetchall()
    finally:
        conn.close()
    assert len(rows) <= MAX_ROWS


@pytest.mark.parametrize(
    ("sql", "expected"),
    [pytest.param(sql, rule, id=ident) for ident, sql, rule in MALICIOUS],
)
def test_malicious_queries_rejected(sql: str, expected: Rule, schema: SchemaInfo) -> None:
    result = check(sql, schema)
    assert not result.ok
    assert result.sql_normalized is None
    assert result.rule == expected, result.reason
    assert result.reason


def test_rejection_never_returns_sql(schema: SchemaInfo) -> None:
    assert check("DROP TABLE customers", schema).sql_normalized is None


# --- LIMIT handling ---------------------------------------------------------------------


def test_limit_added_when_missing(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM customers", schema)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith(f"LIMIT {MAX_ROWS}")
    assert result.warnings == (f"A LIMIT of {MAX_ROWS} was added.",)


def test_limit_added_to_set_operation_not_just_last_branch(schema: SchemaInfo) -> None:
    result = check("SELECT id FROM customers UNION SELECT id FROM orders", schema)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith(f"LIMIT {MAX_ROWS}")


def test_small_limit_is_kept_without_warning(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM customers LIMIT 5", schema)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith("LIMIT 5")
    assert result.warnings == ()


def test_limit_equal_to_max_is_kept(schema: SchemaInfo) -> None:
    result = check(f"SELECT * FROM customers LIMIT {MAX_ROWS}", schema)
    assert result.warnings == ()


@pytest.mark.parametrize(
    "limit",
    ["999999", "-1", "(SELECT 999999)", "id", "1.5", "5 + 1000"],
)
def test_large_or_nonliteral_limit_is_capped(limit: str, schema: SchemaInfo) -> None:
    result = check(f"SELECT * FROM customers LIMIT {limit}", schema)
    assert result.ok, result.reason
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith(f"LIMIT {MAX_ROWS}")
    assert result.warnings == (f"LIMIT was capped to {MAX_ROWS}.",)


def test_offset_is_preserved_when_capping(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM customers LIMIT 99999 OFFSET 10", schema)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith(f"LIMIT {MAX_ROWS} OFFSET 10")


def test_max_rows_parameter_is_respected(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM customers", schema, max_rows=7)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith("LIMIT 7")


def test_inner_limit_does_not_replace_outer_limit(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM (SELECT * FROM customers LIMIT 3) AS s", schema)
    assert result.sql_normalized is not None
    assert result.sql_normalized.endswith(f"LIMIT {MAX_ROWS}")


# --- misc behaviour ---------------------------------------------------------------------


def test_max_length_parameter(schema: SchemaInfo) -> None:
    result = check("SELECT * FROM customers", schema, max_length=10)
    assert result.rule == Rule.TOO_LONG


def test_comment_markers_inside_string_literals_are_fine(schema: SchemaInfo) -> None:
    assert check("SELECT '-- not a comment'", schema).ok


def test_cte_may_shadow_nothing_but_still_validates_inner_tables(schema: SchemaInfo) -> None:
    result = check("WITH t AS (SELECT * FROM nope) SELECT * FROM t", schema)
    assert result.rule == Rule.UNKNOWN_TABLE


def test_validation_is_pure_and_repeatable(schema: SchemaInfo) -> None:
    sql = "SELECT * FROM customers"
    assert check(sql, schema) == check(sql, schema)


def test_result_is_immutable(schema: SchemaInfo) -> None:
    result = check("SELECT 1", schema)
    with pytest.raises(ValueError, match="frozen"):
        result.ok = False  # type: ignore[misc]
