"""Database connection helpers. Query execution always uses a read-only connection."""

import sqlite3
from pathlib import Path


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open SQLite with `mode=ro` so writes fail at the engine level (last line of defense)."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}. Run `python -m app.db.seed`.")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def connect_readwrite(db_path: Path) -> sqlite3.Connection:
    """Writable connection - used ONLY by the seed script, never by request handlers."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
