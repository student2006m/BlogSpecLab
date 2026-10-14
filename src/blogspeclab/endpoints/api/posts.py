"""Author post routes for User Story 1 (thin HTTP layer, no logic).

Each route authenticates via the session loader, delegates to an Application
use case inside the transaction boundary, and lets the centralized handlers
in `errors.py` render failures as Problem Details. Permission and state
decisions happen in Application/Domain, never here.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from blogspeclab.core.application import author_posts as use_cases
from blogspeclab.endpoints.api import errors as http_errors
from blogspeclab.endpoints.api.auth import load_current_user
from blogspeclab.infra.data_access import db
from blogspeclab.infra.data_access.repositories import (
    SQLitePostRepository,
    SQLiteUserStore,
    SystemClock,
)

posts_bp = Blueprint("posts", __name__)


def _context() -> tuple[Any, Any, dict[str, Any]]:
    # Local import: app.py imports this module for blueprint registration,
    # so a top-level import would be circular (same package, still a cycle).
    from blogspeclab.endpoints.api.app import get_connection

    connection = get_connection()
    store = SQLiteUserStore(connection)
    actor = load_current_user(store)
    if actor is None:
        raise http_errors.UnauthorizedError("Authentication is required.")
    repo = SQLitePostRepository(connection)
    return connection, repo, actor


def _map_errors(func):
    try:
        return func()
    except use_cases.InvalidInputError as exc:
        raise http_errors.BadRequestError(str(exc)) from exc
    except use_cases.NotFoundError as exc:
        raise http_errors.PostNotFoundError(str(exc)) from exc
    except use_cases.ForbiddenError as exc:
        raise http_errors.ForbiddenError(str(exc)) from exc


@posts_bp.post("/posts")
def create_post():
    connection, repo, actor = _context()
    data = request.get_json(silent=True) or {}

    def _run():
        with db.transaction(connection):
            return use_cases.create_post(
                repo,
                SystemClock(),
                actor,
                title=data.get("title", ""),
                content=data.get("content", ""),
            )

    return jsonify(_map_errors(_run)), 201


@posts_bp.get("/posts")
def list_posts():
    _, repo, actor = _context()
    return jsonify(_map_errors(lambda: use_cases.list_own_posts(repo, actor))), 200


@posts_bp.get("/posts/<int:post_id>")
def get_post(post_id: int):
    _, repo, actor = _context()
    return jsonify(_map_errors(lambda: use_cases.get_post(repo, actor, post_id))), 200


@posts_bp.patch("/posts/<int:post_id>")
def update_post(post_id: int):
    connection, repo, actor = _context()
    data = request.get_json(silent=True) or {}

    def _run():
        with db.transaction(connection):
            return use_cases.update_post(
                repo,
                SystemClock(),
                actor,
                post_id,
                title=data.get("title"),
                content=data.get("content"),
            )

    return jsonify(_map_errors(_run)), 200


@posts_bp.delete("/posts/<int:post_id>")
def delete_post(post_id: int):
    connection, repo, actor = _context()

    def _run():
        with db.transaction(connection):
            return use_cases.delete_post(repo, actor, post_id)

    _map_errors(_run)
    return "", 204


@posts_bp.post("/posts/<int:post_id>/submit")
def submit_post(post_id: int):
    connection, repo, actor = _context()

    def _run():
        with db.transaction(connection):
            return use_cases.submit_post(
                repo, SystemClock(), actor, post_id
            )

    return jsonify(_map_errors(_run)), 200
