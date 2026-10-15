"""Centralized HTTP error mapping to RFC 9457 Problem Details.

Only translation lives here: application results/exceptions become
`application/problem+json` responses with a stable `code`. No business
logic, no existence leaks (see FR-014), no internals or secrets in bodies.
"""

from __future__ import annotations

import json
from typing import Any

from flask import Flask, current_app


class AppError(Exception):
    """Application-level failure with an HTTP mapping."""

    status: int = 500
    code: str = "INTERNAL_ERROR"
    title: str = "Internal Server Error"

    def __init__(self, detail: str = "", code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code


class BadRequestError(AppError):
    status = 400
    code = "BAD_REQUEST"
    title = "Bad Request"


class UnauthorizedError(AppError):
    status = 401
    code = "UNAUTHORIZED"
    title = "Unauthorized"


class ForbiddenError(AppError):
    status = 403
    code = "FORBIDDEN"
    title = "Forbidden"


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"
    title = "Not Found"


class PostNotFoundError(NotFoundError):
    code = "POST_NOT_FOUND"
    title = "Post Not Found"


class InternalError(AppError):
    status = 500
    code = "INTERNAL_ERROR"
    title = "Internal Server Error"


class MethodNotAllowedError(AppError):
    status = 405
    code = "METHOD_NOT_ALLOWED"
    title = "Method Not Allowed"


def problem_response(error: AppError) -> tuple[Any, int]:
    """Render one Problem Details body (never includes secrets or traces)."""
    payload = {
        "type": "about:blank",
        "title": error.title,
        "status": error.status,
        "code": error.code,
        "detail": error.detail,
    }
    return (
        current_app.response_class(
            response=json.dumps(payload),
            status=error.status,
            mimetype="application/problem+json",
        ),
        error.status,
    )


def register_error_handlers(app: Flask) -> None:
    """Register centralized handlers; endpoints MUST NOT duplicate this."""

    @app.errorhandler(AppError)
    def _handle_app_error(error: AppError) -> tuple[Any, int]:
        return problem_response(error)

    @app.errorhandler(404)
    def _handle_unknown_route(_error: Any) -> tuple[Any, int]:
        return problem_response(NotFoundError("Unknown endpoint."))

    @app.errorhandler(405)
    def _handle_method_not_allowed(_error: Any) -> tuple[Any, int]:
        return problem_response(MethodNotAllowedError("Method not allowed."))

    @app.errorhandler(Exception)
    def _handle_unexpected(_error: Any) -> tuple[Any, int]:
        # Last resort: never leak tracebacks or internals; specific handlers
        # above (AppError, 404, 405) take precedence for known failures.
        return problem_response(
            InternalError("An unexpected error occurred.")
        )
