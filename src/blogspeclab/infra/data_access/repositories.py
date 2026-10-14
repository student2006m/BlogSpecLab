"""SQLite-backed implementations of the application ports.

Pure row mapping only: no state-transition rules, no ownership or role
checks, no validation beyond storage mechanics. All business rules live in
Domain/Application layers built later. `sqlite3` objects never leave this
module: every method returns plain `dict`/`list`/`int`/`bool` values.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from blogspeclab.core.application import ports

_POST_COLUMNS = "id, owner_id, title, content, state, created_at, updated_at"
_USER_COLUMNS = "id, username, password_hash, roles"


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class SQLitePostRepository:
    """`PostRepository` over one caller-managed `sqlite3` connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def insert_post(self, row: dict[str, Any]) -> int:
        cursor = self._connection.execute(
            "INSERT INTO posts (owner_id, title, content, state, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["owner_id"],
                row["title"],
                row["content"],
                row["state"],
                row["created_at"],
                row["updated_at"],
            ),
        )
        return int(cursor.lastrowid)

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        cursor = self._connection.execute(
            f"SELECT {_POST_COLUMNS} FROM posts WHERE id = ?", (post_id,)
        )
        return _row_to_dict(cursor.fetchone())

    def list_posts_by_owner(self, owner_id: int) -> list[dict[str, Any]]:
        cursor = self._connection.execute(
            f"SELECT {_POST_COLUMNS} FROM posts WHERE owner_id = ?"
            " ORDER BY id",
            (owner_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_posts_by_state(self, state: str) -> list[dict[str, Any]]:
        cursor = self._connection.execute(
            f"SELECT {_POST_COLUMNS} FROM posts WHERE state = ? ORDER BY id",
            (state,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_published_posts(self) -> list[dict[str, Any]]:
        return self.list_posts_by_state("published")

    def update_post(self, post_id: int, changes: dict[str, Any]) -> bool:
        if not changes:
            return self.get_post(post_id) is not None
        assignments = ", ".join(f"{column} = ?" for column in changes)
        cursor = self._connection.execute(
            f"UPDATE posts SET {assignments} WHERE id = ?",
            (*changes.values(), post_id),
        )
        return cursor.rowcount > 0

    def delete_post(self, post_id: int) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM posts WHERE id = ?", (post_id,)
        )
        return cursor.rowcount > 0

    def append_decision(self, row: dict[str, Any]) -> int:
        cursor = self._connection.execute(
            "INSERT INTO decisions (post_id, actor_id, action, reason,"
            " created_at) VALUES (?, ?, ?, ?, ?)",
            (
                row["post_id"],
                row["actor_id"],
                row["action"],
                row.get("reason"),
                row["created_at"],
            ),
        )
        return int(cursor.lastrowid)


class SQLiteUserStore:
    """`UserStore` over one caller-managed `sqlite3` connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        cursor = self._connection.execute(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username = ?",
            (username,),
        )
        return _row_to_dict(cursor.fetchone())

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        cursor = self._connection.execute(
            f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)
        )
        return _row_to_dict(cursor.fetchone())

    def upsert_demo_user(
        self, username: str, password_hash: str, roles: str
    ) -> int:
        self._connection.execute(
            "INSERT INTO users (username, password_hash, roles)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT (username) DO UPDATE SET"
            " password_hash = excluded.password_hash,"
            " roles = excluded.roles",
            (username, password_hash, roles),
        )
        row = self.get_by_username(username)
        assert row is not None
        return int(row["id"])


class Pbkdf2PasswordHasher:
    """`PasswordHasher` via stdlib `hashlib.pbkdf2_hmac` (SHA-256)."""

    def __init__(self, iterations: int = 210_000) -> None:
        self._iterations = iterations

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, self._iterations
        )
        return (
            f"pbkdf2-sha256${self._iterations}"
            f"${salt.hex()}${digest.hex()}"
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            _, iterations, salt_hex, digest_hex = password_hash.split("$")
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(digest.hex(), digest_hex)


class SystemClock:
    """`Clock` returning current UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


# Static conformance checks (fail at import time on signature drift).
_POST_REPOSITORY: type[ports.PostRepository] = SQLitePostRepository
_USER_STORE: type[ports.UserStore] = SQLiteUserStore
_HASHER: type[ports.PasswordHasher] = Pbkdf2PasswordHasher
_CLOCK: type[ports.Clock] = SystemClock
