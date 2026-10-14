"""SQLite connection helper and schema management (infrastructure only).

No business logic lives here: this module only opens connections, applies the
relational schema derived from data-model.md, and exposes an explicit
transaction boundary. Schema creation and seeding are explicit calls; nothing
runs implicitly on import.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    roles TEXT NOT NULL DEFAULT 'author'
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users (id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts (id),
    actor_id INTEGER NOT NULL REFERENCES users (id),
    action TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with row access and foreign keys enabled."""
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_schema(connection: sqlite3.Connection) -> None:
    """Create tables if they do not exist. Explicit call only."""
    connection.executescript(SCHEMA)
    connection.commit()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Atomic boundary: BEGIN IMMEDIATE, COMMIT on success, ROLLBACK on error.

    `sqlite3.Connection` objects MUST NOT leave `infra.data_access`; callers
    only see the effects (committed or rolled back), never cursors or rows
    beyond the repository layer.
    """
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
