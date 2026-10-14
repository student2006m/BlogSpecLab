"""Flask application factory and dependency composition (endpoints layer).

Composition root only: validates required startup configuration fail-fast,
builds infrastructure adapters, and registers centralized error handlers.
`create_app` NEVER creates schema or seeds users implicitly; those are
explicit calls (`db.init_schema`, `seed.seed_demo_users`). No business logic
lives here. TLS/HTTPS is the host's job, not this module's.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from collections.abc import Mapping
from typing import Any

from flask import Flask, current_app, g

from blogspeclab.endpoints.api import errors
from blogspeclab.infra.data_access import db

DATABASE_PATH_SETTINGS = ("DATABASE_PATH", "BLOGSPECLAB_DATABASE_PATH")


def _resolve_database_path(config: Mapping[str, Any]) -> str:
    for key in DATABASE_PATH_SETTINGS:
        value = config.get(key, os.environ.get(key, ""))
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(
        "Missing required startup setting: DATABASE_PATH "
        "(config key 'DATABASE_PATH' or env 'BLOGSPECLAB_DATABASE_PATH')."
    )


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build and return the Flask application (no routes yet in Phase 2)."""
    settings: dict[str, Any] = dict(config or {})
    database_path = _resolve_database_path(settings)

    app = Flask(__name__)
    app.config["DATABASE_PATH"] = database_path
    app.config["TESTING"] = bool(settings.get("TESTING", False))
    secret_key = settings.get("SECRET_KEY") or os.environ.get("SECRET_KEY")
    if secret_key:
        app.secret_key = secret_key
    elif app.config["TESTING"]:
        # Ephemeral per-process key for tests only; never logged, never
        # committed. Production MUST provide SECRET_KEY via config or env.
        app.secret_key = secrets.token_hex(32)

    errors.register_error_handlers(app)

    @app.teardown_appcontext
    def _close_connection(_error: BaseException | None = None) -> None:
        connection = g.pop("db_connection", None)
        if connection is not None:
            connection.close()

    return app


def get_connection() -> sqlite3.Connection:
    """Per-request SQLite connection for the composition root's adapters."""
    connection = g.get("db_connection")
    if connection is None:
        connection = db.connect(current_app.config["DATABASE_PATH"])
        g.db_connection = connection
    return connection
