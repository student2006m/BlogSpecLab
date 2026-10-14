"""Current-user loading for the composition root (identity only).

Extracts the authenticated identity from the Flask session and resolves it
— including roles — against the server-side `UserStore`. The session carries
ONLY the user id: roles, ownership, and permissions NEVER come from client
content (session data, cookies, headers, or tokens). This helper makes NO
authorization decision; permission checks belong to Application use cases.
There is deliberately NO login/logout route here (not a Phase 2 task).
"""

from __future__ import annotations

from typing import Any

from flask import session

SESSION_USER_KEY = "user_id"


def load_current_user(user_store: Any) -> dict[str, Any] | None:
    """Return `{id, username, roles}` for the session user, else None.

    Returns None when the session is absent, malformed, or references an
    unknown user. Never raises for authentication states; never logs
    identifiers beyond operational necessity.
    """
    raw_user_id = session.get(SESSION_USER_KEY)
    if not isinstance(raw_user_id, int) or isinstance(raw_user_id, bool):
        return None
    row = user_store.get_by_id(raw_user_id)
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "roles": row["roles"],
    }
