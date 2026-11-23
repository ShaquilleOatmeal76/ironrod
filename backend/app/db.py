"""Database connection and a tiny migration runner.

Migrations are plain .sql files in app/migrations, named NNN_description.sql.
Each one runs exactly once, in order, and is recorded in schema_migrations.
To change the database later, add a new file -- never edit an old one.
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("IRONROD_DB", "data/ironrod.db"))
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrent reads
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply any migrations that haven't run yet. Returns the names applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if file.name in done:
            continue
        with conn:  # one transaction per migration
            conn.executescript(file.read_text())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (file.name,))
        applied.append(file.name)
    return applied


def library_is_empty(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0] == 0
