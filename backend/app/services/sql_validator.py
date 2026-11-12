"""AST-based SQL validator: the safety layer between untrusted LLM output and the database.

Pure function, allow-list first. Anything not explicitly permitted is rejected.
The read-only DB connection remains the last line of defense, not the first.
"""

from enum import StrEnum

import sqlglot
from pydantic import BaseModel, ConfigDict
from sqlglot import exp
from sqlglot.errors import SqlglotError

from app.services.schema import SchemaInfo, TableInfo

DEFAULT_MAX_SQL_LENGTH = 2_000
_DIALECT = "sqlite"


class Rule(StrEnum):
    EMPTY = "empty_query"
    TOO_LONG = "query_too_long"
    ILLEGAL_CHARS = "illegal_characters"
    COMMENTS = "comments_not_allowed"
    SYNTAX = "syntax_error"
    MULTIPLE_STATEMENTS = "multiple_statements"
    NOT_SELECT = "select_only"
    FORBIDDEN_OPERATION = "forbidden_operation"
    RECURSIVE_CTE = "recursive_cte"
    TABLE_FUNCTION = "table_function"
    QUALIFIED_TABLE = "qualified_table"
    SYSTEM_TABLE = "system_table"
    UNKNOWN_TABLE = "unknown_table"
    UNKNOWN_COLUMN = "unknown_column"
    FUNCTION_NOT_ALLOWED = "function_not_allowed"


class ValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    sql_normalized: str | None = None
    rule: Rule | None = None
    reason: str | None = None
    warnings: tuple[str, ...] = ()


class SqlRejectedError(Exception):
    """Internal control-flow signal; converted to a ValidationResult at the boundary."""

    def __init__(self, rule: Rule, reason: str) -> None:
        super().__init__(reason)
        self.rule = rule
        self.reason = reason


# --- allow-lists -----------------------------------------------------------------------

_ROOT_TYPES = (exp.Select, exp.SetOperation)

_FORBIDDEN_NODES: tuple[type[exp.Expr], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Pragma,
    exp.Attach,
    exp.Detach,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Set,
    exp.Use,
    exp.Into,
    exp.Lock,
)

# typed sqlglot function nodes (sqlglot normalises e.g. IFNULL -> Coalesce, IIF -> If)
_ALLOWED_FUNC_TYPES: frozenset[type[exp.Expr]] = frozenset(
    {
        exp.Abs, exp.And, exp.Avg, exp.Case, exp.Cast, exp.Ceil, exp.Coalesce, exp.Count,
        exp.CurrentDate, exp.CurrentTime, exp.CurrentTimestamp, exp.Date, exp.DenseRank,
        exp.Exists, exp.Floor, exp.GroupConcat, exp.Greatest, exp.If, exp.Lag, exp.Lead,
        exp.Least, exp.Length, exp.Lower, exp.Max, exp.Min, exp.Ntile, exp.Nullif, exp.Or,
        exp.Pow, exp.Rand, exp.Rank, exp.Replace, exp.Round, exp.RowNumber, exp.Sign,
        exp.Sqrt, exp.StrPosition, exp.Substring, exp.Sum, exp.TimeToStr, exp.Trim,
        exp.TsOrDsToTimestamp, exp.Typeof, exp.Upper, exp.Xor,
    }
)  # fmt: skip

# functions sqlglot leaves untyped for SQLite; matched by lower-cased name
_ALLOWED_ANONYMOUS_FUNCS: frozenset[str] = frozenset(
    {
        "date", "time", "datetime", "julianday", "strftime", "total", "random",
        "rank", "dense_rank", "lag", "lead", "ntile", "ifnull", "iif", "instr",
        "sign", "ltrim", "rtrim",
    }
)  # fmt: skip


# --- individual checks (each raises SqlRejectedError) ---------------------------------------


def _check_text(sql: str, max_length: int) -> None:
    if not sql.strip():
        raise SqlRejectedError(Rule.EMPTY, "The query is empty.")
    if len(sql) > max_length:
        raise SqlRejectedError(Rule.TOO_LONG, f"The query is longer than {max_length} characters.")
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in sql):
        raise SqlRejectedError(Rule.ILLEGAL_CHARS, "The query contains control characters.")
    try:
        tokens = sqlglot.tokenize(sql, read=_DIALECT)
    except SqlglotError as exc:
        raise SqlRejectedError(Rule.SYNTAX, "The query could not be tokenised.") from exc
    if any(tok.comments for tok in tokens):
        raise SqlRejectedError(Rule.COMMENTS, "SQL comments are not allowed.")


def _parse_single(sql: str) -> exp.Expr:
    try:
        statements = [s for s in sqlglot.parse(sql, read=_DIALECT) if s is not None]
    except SqlglotError as exc:
        raise SqlRejectedError(Rule.SYNTAX, "The query is not valid SQL.") from exc
    if not statements:
        raise SqlRejectedError(Rule.EMPTY, "The query is empty.")
    if len(statements) > 1:
        raise SqlRejectedError(Rule.MULTIPLE_STATEMENTS, "Only a single statement is allowed.")
    return statements[0]


def _unwrap_root(root: exp.Expr) -> exp.Expr:
    """Peel redundant parentheses: `(SELECT 1)` is not valid top-level SQLite."""
    return root.unnest() if isinstance(root, exp.Subquery) else root


def _check_root(root: exp.Expr) -> None:
    if not isinstance(root, _ROOT_TYPES):
        raise SqlRejectedError(Rule.NOT_SELECT, "Only SELECT queries are allowed.")


def _check_forbidden_nodes(root: exp.Expr) -> None:
    bad = root.find(*_FORBIDDEN_NODES)
    if bad is not None:
        raise SqlRejectedError(
            Rule.FORBIDDEN_OPERATION,
            f"{type(bad).__name__.upper()} operations are not allowed; the data is read-only.",
        )


def _cte_names(root: exp.Expr) -> frozenset[str]:
    with_nodes = list(root.find_all(exp.With))
    if any(w.args.get("recursive") for w in with_nodes):
        raise SqlRejectedError(Rule.RECURSIVE_CTE, "Recursive queries are not allowed.")
    return frozenset(cte.alias.lower() for w in with_nodes for cte in w.expressions)


def _check_tables(
    root: exp.Expr, schema: SchemaInfo, cte_names: frozenset[str]
) -> dict[str, list[TableInfo]]:
    """Validate every table reference; return alias -> real tables (for column checks)."""
    aliases: dict[str, list[TableInfo]] = {}
    for node in root.find_all(exp.Table):
        if not isinstance(node.this, exp.Identifier):
            raise SqlRejectedError(Rule.TABLE_FUNCTION, "Table-valued functions are not allowed.")
        if node.db or node.catalog:
            raise SqlRejectedError(
                Rule.QUALIFIED_TABLE, "Schema-qualified table names are not allowed."
            )
        name = node.name.lower()
        if name in cte_names:
            continue
        if name.startswith("sqlite_"):
            raise SqlRejectedError(Rule.SYSTEM_TABLE, "System tables are not accessible.")
        table = schema.table(name)
        if table is None:
            raise SqlRejectedError(Rule.UNKNOWN_TABLE, f"Unknown table '{node.name}'.")
        aliases.setdefault(node.alias_or_name.lower(), []).append(table)
    return aliases


def _defined_names(root: exp.Expr, cte_names: frozenset[str]) -> frozenset[str]:
    """Names introduced by the query itself: select aliases, subquery aliases, CTE columns."""
    names = {a.alias.lower() for a in root.find_all(exp.Alias)}
    names |= {s.alias.lower() for s in root.find_all(exp.Subquery) if s.alias}
    for alias in root.find_all(exp.TableAlias):
        names |= {c.name.lower() for c in alias.columns}
    return frozenset(names) | cte_names


def _check_columns(
    root: exp.Expr,
    aliases: dict[str, list[TableInfo]],
    cte_names: frozenset[str],
) -> None:
    defined = _defined_names(root, cte_names)
    visible = frozenset(c for tables in aliases.values() for t in tables for c in t.column_names)
    for col in root.find_all(exp.Column):
        if isinstance(col.this, exp.Star):
            continue
        name, qualifier = col.name.lower(), col.table.lower()
        if qualifier and not _qualified_ok(name, qualifier, aliases, defined):
            raise SqlRejectedError(Rule.UNKNOWN_COLUMN, f"Unknown column '{qualifier}.{col.name}'.")
        if not qualifier and name not in visible and name not in defined:
            raise SqlRejectedError(Rule.UNKNOWN_COLUMN, f"Unknown column '{col.name}'.")


def _qualified_ok(
    name: str, qualifier: str, aliases: dict[str, list[TableInfo]], defined: frozenset[str]
) -> bool:
    if qualifier in aliases:
        return any(name in t.column_names for t in aliases[qualifier])
    return qualifier in defined  # CTE / subquery alias: its columns are query-defined


def _check_functions(root: exp.Expr) -> None:
    for node in root.find_all(exp.Func):
        if isinstance(node, exp.Anonymous):
            if node.name.lower() not in _ALLOWED_ANONYMOUS_FUNCS:
                raise SqlRejectedError(
                    Rule.FUNCTION_NOT_ALLOWED, f"Function '{node.name}' is not allowed."
                )
        elif type(node) not in _ALLOWED_FUNC_TYPES:
            raise SqlRejectedError(
                Rule.FUNCTION_NOT_ALLOWED, f"Function '{node.sql_name()}' is not allowed."
            )


def _enforce_limit(root: exp.Expr, max_rows: int) -> tuple[str, ...]:
    """Ensure the outer query returns at most `max_rows` rows. Returns warnings."""
    limit = root.args.get("limit")
    if limit is None:
        root.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
        return (f"A LIMIT of {max_rows} was added.",)
    value = limit.expression
    if isinstance(value, exp.Literal) and value.is_int and int(value.name) <= max_rows:
        return ()
    limit.set("expression", exp.Literal.number(max_rows))
    return (f"LIMIT was capped to {max_rows}.",)


# --- public API ------------------------------------------------------------------------


def validate_sql(
    sql: str,
    schema: SchemaInfo,
    *,
    max_rows: int,
    max_length: int = DEFAULT_MAX_SQL_LENGTH,
) -> ValidationResult:
    """Validate untrusted SQL. On success `sql_normalized` is the only text to execute."""
    try:
        _check_text(sql, max_length)
        root = _unwrap_root(_parse_single(sql))
        _check_root(root)
        _check_forbidden_nodes(root)
        ctes = _cte_names(root)
        aliases = _check_tables(root, schema, ctes)
        _check_columns(root, aliases, ctes)
        _check_functions(root)
        warnings = _enforce_limit(root, max_rows)
        return ValidationResult(
            ok=True, sql_normalized=root.sql(dialect=_DIALECT), warnings=warnings
        )
    except SqlRejectedError as rejected:
        return ValidationResult(ok=False, rule=rejected.rule, reason=rejected.reason)
