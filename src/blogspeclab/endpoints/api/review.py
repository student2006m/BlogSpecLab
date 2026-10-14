"""Editor review routes for User Story 2 (thin HTTP layer, no logic).

Every route requires the editor role (checked against the server-side
record), delegates to an Application use case inside the transaction
boundary, and relies on the centralized handlers for Problem Details.
Self-approval is rejected in Domain and Application, never here.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from blogspeclab.core.application import review as review_cases
from blogspeclab.core.application.author_posts import (
    ForbiddenError as AppForbidden,
)
from blogspeclab.core.application.author_posts import (
    InvalidInputError as AppInvalid,
)
from blogspeclab.core.application.author_posts import (
    NotFoundError as AppNotFound,
)
from blogspeclab.endpoints.api import errors as http_errors
from blogspeclab.endpoints.api.auth import load_current_user
from blogspeclab.infra.data_access import db
from blogspeclab.infra.data_access.repositories import (
    SQLitePostRepository,
    SQLiteUserStore,
    SystemClock,
)

review_bp = Blueprint("review", __name__)


def _editor_context() -> tuple[Any, Any, dict[str, Any]]:
    # Local import: app.py imports this module for blueprint registration,
    # so a top-level import would be circular (same package, still a cycle).
    from blogspeclab.endpoints.api.app import get_connection

    connection = get_connection()
    store = SQLiteUserStore(connection)
    actor = load_current_user(store)
    if actor is None:
        raise http_errors.UnauthorizedError("Authentication is required.")
    if "editor" not in {
        role.strip() for role in actor.get("roles", "").split(",")
    }:
        raise http_errors.ForbiddenError("The editor role is required.")
    return connection, SQLitePostRepository(connection), actor


def _map_errors(func) -> Any:
    try:
        return func()
    except AppInvalid as exc:
        raise http_errors.BadRequestError(str(exc)) from exc
    except AppNotFound as exc:
        raise http_errors.PostNotFoundError(str(exc)) from exc
    except AppForbidden as exc:
        raise http_errors.ForbiddenError(str(exc)) from exc


@review_bp.get("/review-queue")
def review_queue() -> tuple[Any, int]:
    _, repo, actor = _editor_context()
    return jsonify(review_cases.list_review_queue(repo, actor)), 200


@review_bp.patch("/posts/<int:post_id>/revise")
def revise_post(post_id: int) -> tuple[Any, int]:
    connection, repo, actor = _editor_context()
    data = request.get_json(silent=True) or {}

    def _run():
        with db.transaction(connection):
            return review_cases.revise_post(
                repo,
                SystemClock(),
                actor,
                post_id,
                title=data.get("title"),
                content=data.get("content"),
            )

    return jsonify(_map_errors(_run)), 200


@review_bp.post("/posts/<int:post_id>/approve")
def approve_post(post_id: int) -> tuple[Any, int]:
    connection, repo, actor = _editor_context()

    def _run():
        with db.transaction(connection):
            return review_cases.approve_post(
                repo, SystemClock(), actor, post_id
            )

    return jsonify(_map_errors(_run)), 200


@review_bp.post("/posts/<int:post_id>/reject")
def reject_post(post_id: int) -> tuple[Any, int]:
    connection, repo, actor = _editor_context()
    data = request.get_json(silent=True) or {}

    def _run():
        with db.transaction(connection):
            return review_cases.reject_post(
                repo, SystemClock(), actor, post_id,
                reason=data.get("reason", ""),
            )

    return jsonify(_map_errors(_run)), 200


@review_bp.post("/posts/<int:post_id>/unpublish")
def unpublish_post(post_id: int) -> tuple[Any, int]:
    connection, repo, actor = _editor_context()
    data = request.get_json(silent=True) or {}

    def _run():
        with db.transaction(connection):
            return review_cases.unpublish_post(
                repo, SystemClock(), actor, post_id,
                reason=data.get("reason", ""),
            )

    return jsonify(_map_errors(_run)), 200
