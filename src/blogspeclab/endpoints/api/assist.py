"""Smart review assist route (thin HTTP layer, no logic, feature 002).

Authenticates via the session loader, reads the composed provider, delegates
to the Application use case, and lets the centralized handlers render
failures as Problem Details. No provider call and no business decision
happens here; the operation performs no database write.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify

from blogspeclab.core.application import review_assist as use_cases
from blogspeclab.endpoints.api import errors as http_errors
from blogspeclab.endpoints.api.auth import load_current_user
from blogspeclab.infra.data_access.repositories import (
    SQLitePostRepository,
    SQLiteUserStore,
)

assist_bp = Blueprint("assist", __name__)


def _context() -> tuple[Any, dict[str, Any]]:
    # Local import: app.py imports this module for blueprint registration,
    # so a top-level import of app.py would be circular (same as posts.py).
    from blogspeclab.endpoints.api.app import get_connection

    connection = get_connection()
    actor = load_current_user(SQLiteUserStore(connection))
    if actor is None:
        raise http_errors.UnauthorizedError("Authentication is required.")
    return connection, actor


def _map_errors(caller) -> Any:
    try:
        return caller()
    except use_cases.NotFoundError as exc:
        raise http_errors.PostNotFoundError(str(exc)) from exc
    except use_cases.ForbiddenError as exc:
        raise http_errors.ForbiddenError(str(exc)) from exc
    except use_cases.ReviewUnavailableError as exc:
        raise http_errors.ReviewAssistUnavailableError(str(exc)) from exc


@assist_bp.post("/posts/<int:post_id>/review-assist")
def review_assist(post_id: int):
    connection, actor = _context()
    provider = current_app.config.get("REVIEW_ASSIST_PROVIDER")

    def _run():
        if provider is None:
            raise use_cases.ReviewUnavailableError(
                "The smart review service is not configured."
            )
        return use_cases.request_review_assist(
            SQLitePostRepository(connection), actor, provider, post_id
        )

    return jsonify(_map_errors(_run)), 200
