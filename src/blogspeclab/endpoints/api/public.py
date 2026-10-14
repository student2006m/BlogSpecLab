"""Anonymous public routes for published posts (thin HTTP layer, no logic).

The ONLY routes allowed without a session. They expose published posts and
nothing else: any non-published or missing id reads as not-found, so
unpublished content is never leaked.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify

from blogspeclab.core.application import review as review_cases
from blogspeclab.core.application.author_posts import (
    NotFoundError as AppNotFound,
)
from blogspeclab.endpoints.api import errors as http_errors

public_bp = Blueprint("public", __name__)


def _public_repo():
    # Local import: app.py imports this module for blueprint registration,
    # so a top-level import would be circular (same package, still a cycle).
    from blogspeclab.endpoints.api.app import get_connection

    from blogspeclab.infra.data_access.repositories import (
        SQLitePostRepository,
    )

    return SQLitePostRepository(get_connection())


@public_bp.get("/published")
def list_published() -> tuple[Any, int]:
    return jsonify(review_cases.list_published_posts(_public_repo())), 200


@public_bp.get("/published/<int:post_id>")
def get_published(post_id: int) -> tuple[Any, int]:
    try:
        return jsonify(
            review_cases.get_published_post(_public_repo(), post_id)
        ), 200
    except AppNotFound as exc:
        raise http_errors.PostNotFoundError(str(exc)) from exc
