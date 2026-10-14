"""Shared pytest fixtures for BlogSpecLab (Phase 1 skeleton).

Phase 2 modules (db, repositories, app factory) do not exist yet. Imports of
those modules happen lazily INSIDE fixtures so that plain collection works
now; fixtures skip with a clear message until their module is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    """Filesystem path for an isolated temporary SQLite database file."""
    return tmp_path / "test.db"


@pytest.fixture()
def db_module():
    """The Phase 2 data_access.db module (schema + connection helper)."""
    try:
        from blogspeclab.infra import data_access
        from blogspeclab.infra.data_access import db
    except ImportError as exc:
        pytest.skip(f"Phase 2 module not implemented yet: {exc}")
    return db


@pytest.fixture()
def flask_app(tmp_path: Path):
    """Flask application built by the Phase 2 application factory."""
    try:
        from blogspeclab.endpoints.api.app import create_app
    except ImportError as exc:
        pytest.skip(f"Phase 2 module not implemented yet: {exc}")
    return create_app(
        {"TESTING": True, "DATABASE_PATH": str(tmp_path / "app.db")}
    )


@pytest.fixture()
def client(flask_app):
    """Flask test client for HTTP contract tests."""
    return flask_app.test_client()


@pytest.fixture()
def demo_users():
    """Seeded demo author/editor accounts (usernames only, no secrets)."""
    try:
        from blogspeclab.infra.data_access import seed
    except ImportError as exc:
        pytest.skip(f"Phase 2 module not implemented yet: {exc}")
    return seed.demo_usernames()
