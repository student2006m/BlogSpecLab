"""Application ports: contracts for external services (infrastructure-independent).

These protocols use plain record mappings (`dict[str, Any]`) keyed as defined
in data-model.md, deliberately avoiding domain entities (built in T015/T016).
No infrastructure imports are allowed here: `core.application` depends only
on `core.domain` and the standard library.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

# Record shapes (see data-model.md):
#   post:   {id, owner_id, title, content, state, created_at, updated_at}
#   user:   {id, username, password_hash, roles}
#   decision: {id, post_id, actor_id, action, reason, created_at}


class PostRepository(Protocol):
    """Persistence port for post and decision rows (no business rules)."""

    def insert_post(self, row: dict[str, Any]) -> int:
        """Insert a post row; return the assigned id."""
        ...

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        """Return one post row by id, or None."""
        ...

    def list_posts_by_owner(self, owner_id: int) -> list[dict[str, Any]]:
        """Return all post rows owned by one user."""
        ...

    def list_posts_by_state(self, state: str) -> list[dict[str, Any]]:
        """Return all post rows in a given state (e.g. review queue)."""
        ...

    def list_published_posts(self) -> list[dict[str, Any]]:
        """Return all published post rows for the public listing."""
        ...

    def update_post(self, post_id: int, changes: dict[str, Any]) -> bool:
        """Apply field changes; return False when the row does not exist."""
        ...

    def delete_post(self, post_id: int) -> bool:
        """Delete one post row; return False when the row does not exist."""
        ...

    def append_decision(self, row: dict[str, Any]) -> int:
        """Append a decision history row; return the assigned id."""
        ...


class UserStore(Protocol):
    """Authoritative server-side source of user identity and roles."""

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        """Return one user row by username, or None."""
        ...

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Return one user row by id, or None."""
        ...

    def upsert_demo_user(
        self, username: str, password_hash: str, roles: str
    ) -> int:
        """Insert or update a seeded demo user; return the user id."""
        ...


class PasswordHasher(Protocol):
    """Password hashing and verification (no storage, no logging of secrets)."""

    def hash_password(self, password: str) -> str:
        """Return a salted hash string for storage."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Return True only when the password matches the stored hash."""
        ...


class Clock(Protocol):
    """System time source (seam for deterministic tests)."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        ...
