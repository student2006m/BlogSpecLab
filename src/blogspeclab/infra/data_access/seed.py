"""Seeding of demo users from environment configuration (explicit call only).

Source: `BLOGSPECLAB_SEED_USERS` — a JSON list of
`{"username": ..., "password": ..., "roles": "author" | "editor" |
"author,editor"}`. Usernames appear in logs; passwords never do. Nothing is
seeded implicitly: callers (CLI/tests) invoke `seed_demo_users` directly.
"""

from __future__ import annotations

import json
import os
from typing import Any

from blogspeclab.infra.data_access import repositories

SEED_USERS_ENV_VAR = "BLOGSPECLAB_SEED_USERS"
_ALLOWED_ROLES = {"author", "editor"}


def _parse_seed_users(raw: str) -> list[dict[str, Any]]:
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{SEED_USERS_ENV_VAR} is not valid JSON."
        ) from exc
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{SEED_USERS_ENV_VAR} must be a non-empty list.")
    parsed: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"{SEED_USERS_ENV_VAR}[{index}] must be an object."
            )
        username = entry.get("username", "")
        password = entry.get("password", "")
        roles = {
            role.strip()
            for role in str(entry.get("roles", "")).split(",")
            if role.strip()
        }
        if not username or not password:
            raise ValueError(
                f"{SEED_USERS_ENV_VAR}[{index}] needs a non-empty"
                " username and password."
            )
        if not roles or not roles <= _ALLOWED_ROLES:
            raise ValueError(
                f"{SEED_USERS_ENV_VAR}[{index}] roles must be a subset of"
                " {author, editor}."
            )
        parsed.append(
            {
                "username": username,
                "password": password,
                "roles": ",".join(sorted(roles)),
            }
        )
    return parsed


def seed_demo_users(connection: Any, hasher: Any) -> list[str]:
    """Hash env-provided passwords and upsert demo users. Return usernames."""
    raw = os.environ.get(SEED_USERS_ENV_VAR, "")
    if not raw.strip():
        raise ValueError(f"{SEED_USERS_ENV_VAR} is required for seeding.")
    store = repositories.SQLiteUserStore(connection)
    usernames: list[str] = []
    for entry in _parse_seed_users(raw):
        store.upsert_demo_user(
            entry["username"],
            hasher.hash_password(entry["password"]),
            entry["roles"],
        )
        usernames.append(entry["username"])
    return usernames


def demo_usernames() -> list[str]:
    """Usernames declared in the seed env var (no secrets, no DB access)."""
    raw = os.environ.get(SEED_USERS_ENV_VAR, "")
    if not raw.strip():
        return []
    return [entry["username"] for entry in _parse_seed_users(raw)]
