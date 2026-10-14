"""Author use cases for User Story 1 (no Flask, no HTTP, no sqlite3).

All six operations require the `author` role (checked against the
server-side actor record), enforce ownership (other authors' posts read as
not-found), and apply domain guards. Mutating calls assume the caller
(composition layer) wraps them in the `db.transaction` boundary; fakes used
in tests are trivially atomic. Errors are HTTP-independent; endpoints map
them to Problem Details.
"""

from __future__ import annotations

from typing import Any

from blogspeclab.core.application import ports
from blogspeclab.core.domain.post import (
    PENDING_REVIEW,
    Post,
    StateError,
    ValidationError,
)
from blogspeclab.core.domain.user import AUTHOR, parse_roles


class ApplicationError(Exception):
    """Base for application failures (HTTP-independent)."""


class InvalidInputError(ApplicationError):
    """Validation failure → HTTP 400."""


class NotFoundError(ApplicationError):
    """Missing row or other author's post → HTTP 404 (no leak)."""


class ForbiddenError(ApplicationError):
    """Role or state violation on the caller's own post → HTTP 403."""


def _require_author(actor: dict[str, Any]) -> None:
    if AUTHOR not in parse_roles(actor.get("roles", "")):
        raise ForbiddenError("The author role is required.")


def _owned_or_not_found(
    repo: ports.PostRepository, actor_id: int, post_id: int
) -> Post:
    row = repo.get_post(post_id)
    if row is None or row["owner_id"] != actor_id:
        raise NotFoundError(f"Post {post_id} was not found.")
    return Post.from_dict(row)


def _now_iso(clock: ports.Clock) -> str:
    return clock.now().isoformat()


def create_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    title: str,
    content: str,
) -> dict[str, Any]:
    """Create a draft post owned by the actor."""
    _require_author(actor)
    try:
        post = Post.create(
            owner_id=actor["id"], title=title, content=content,
            now=_now_iso(clock),
        )
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    data = post.to_dict()
    data.pop("id")
    post_id = repo.insert_post(data)
    created = repo.get_post(post_id)
    assert created is not None
    return created


def get_post(
    repo: ports.PostRepository, actor: dict[str, Any], post_id: int
) -> dict[str, Any]:
    """Return one owned post; other authors' posts read as not-found."""
    _require_author(actor)
    return _owned_or_not_found(repo, actor["id"], post_id).to_dict()


def list_own_posts(
    repo: ports.PostRepository, actor: dict[str, Any]
) -> list[dict[str, Any]]:
    """List only the actor's own posts."""
    _require_author(actor)
    return repo.list_posts_by_owner(actor["id"])


def update_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
    title: str | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    """Revise an owned draft post (draft-only guard)."""
    _require_author(actor)
    post = _owned_or_not_found(repo, actor["id"], post_id)
    try:
        post.revise(
            post.title if title is None else title,
            post.content if content is None else content,
            _now_iso(clock),
        )
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    repo.update_post(
        post_id,
        {
            "title": post.title,
            "content": post.content,
            "updated_at": post.updated_at,
        },
    )
    updated = repo.get_post(post_id)
    assert updated is not None
    return updated


def delete_post(
    repo: ports.PostRepository, actor: dict[str, Any], post_id: int
) -> bool:
    """Delete an owned draft post (draft-only guard)."""
    _require_author(actor)
    post = _owned_or_not_found(repo, actor["id"], post_id)
    try:
        post.ensure_deletable()
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    return repo.delete_post(post_id)


def submit_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
) -> dict[str, Any]:
    """Submit an owned draft for review; records a decision entry."""
    _require_author(actor)
    post = _owned_or_not_found(repo, actor["id"], post_id)
    try:
        post.submit(_now_iso(clock))
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    repo.update_post(
        post_id, {"state": PENDING_REVIEW, "updated_at": post.updated_at}
    )
    repo.append_decision(
        {
            "post_id": post_id,
            "actor_id": actor["id"],
            "action": "submit",
            "reason": None,
            "created_at": post.updated_at,
        }
    )
    submitted = repo.get_post(post_id)
    assert submitted is not None
    return submitted
