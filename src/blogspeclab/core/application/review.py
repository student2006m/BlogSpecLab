"""Editor review use cases for User Story 2 (no Flask, no HTTP, no sqlite3).

The editor role is read from the server-side actor record on every call and
re-checked per operation; nothing is trusted from client content. Approve and
revise reject self-approval here in addition to the domain guard, so the rule
cannot be bypassed. State change and history append are issued together for
the caller (composition layer) to commit atomically inside `db.transaction`.
Errors are HTTP-independent; endpoints map them to Problem Details.
"""

from __future__ import annotations

from typing import Any

from blogspeclab.core.application import ports
from blogspeclab.core.application.author_posts import (
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)
from blogspeclab.core.domain.post import (
    PENDING_REVIEW,
    Post,
    StateError,
    ValidationError,
)
from blogspeclab.core.domain.user import EDITOR, parse_roles


def _require_editor(actor: dict[str, Any]) -> None:
    if EDITOR not in parse_roles(actor.get("roles", "")):
        raise ForbiddenError("The editor role is required.")


def _pending_or_not_found(
    repo: ports.PostRepository, post_id: int, action: str
) -> Post:
    """Fetch any post by id; editors act cross-ownership by design."""
    row = repo.get_post(post_id)
    if row is None:
        raise NotFoundError(f"Post {post_id} was not found.")
    post = Post.from_dict(row)
    if post.state != PENDING_REVIEW:
        raise ForbiddenError(
            f"Cannot {action} a post in state {post.state!r}."
        )
    return post


def _record(
    repo: ports.PostRepository,
    clock: ports.Clock,
    post: Post,
    actor_id: int,
    action: str,
    reason: str | None,
    changes: dict[str, Any],
) -> dict[str, Any]:
    repo.update_post(post.id, changes)  # type: ignore[arg-type]
    repo.append_decision(
        {
            "post_id": post.id,
            "actor_id": actor_id,
            "action": action,
            "reason": reason,
            "created_at": changes["updated_at"],
        }
    )
    updated = repo.get_post(post.id)  # type: ignore[arg-type]
    assert updated is not None
    return updated


def list_review_queue(
    repo: ports.PostRepository, actor: dict[str, Any]
) -> list[dict[str, Any]]:
    """List every pending post regardless of ownership (review queue)."""
    _require_editor(actor)
    return repo.list_posts_by_state(PENDING_REVIEW)


def approve_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
) -> dict[str, Any]:
    """Approve a pending post: publishes it directly with a history entry."""
    _require_editor(actor)
    post = _pending_or_not_found(repo, post_id, "approve")
    try:
        post.approve(actor["id"], clock.now().isoformat())
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    return _record(
        repo, clock, post, actor["id"], "approve_publish", None,
        {"state": post.state, "updated_at": post.updated_at},
    )


def reject_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
    reason: str,
) -> dict[str, Any]:
    """Reject a pending post to draft. Reason is mandatory."""
    _require_editor(actor)
    post = _pending_or_not_found(repo, post_id, "reject")
    try:
        post.reject(reason, clock.now().isoformat())
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    return _record(
        repo, clock, post, actor["id"], "reject", reason,
        {"state": post.state, "updated_at": post.updated_at},
    )


def revise_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
    title: str | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    """Revise a pending post as a non-owning editor, with history entry."""
    _require_editor(actor)
    post = _pending_or_not_found(repo, post_id, "revise")
    try:
        post.revise_by_editor(
            actor["id"],
            post.title if title is None else title,
            post.content if content is None else content,
            clock.now().isoformat(),
        )
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    return _record(
        repo, clock, post, actor["id"], "editor_edit", None,
        {
            "title": post.title,
            "content": post.content,
            "updated_at": post.updated_at,
        },
    )


def unpublish_post(
    repo: ports.PostRepository,
    clock: ports.Clock,
    actor: dict[str, Any],
    post_id: int,
    reason: str,
) -> dict[str, Any]:
    """Unpublish a published post to draft. Reason is mandatory."""
    _require_editor(actor)
    row = repo.get_post(post_id)
    if row is None:
        raise NotFoundError(f"Post {post_id} was not found.")
    post = Post.from_dict(row)
    try:
        post.unpublish(reason, clock.now().isoformat())
    except StateError as exc:
        raise ForbiddenError(str(exc)) from exc
    except ValidationError as exc:
        raise InvalidInputError(str(exc)) from exc
    return _record(
        repo, clock, post, actor["id"], "unpublish", reason,
        {"state": post.state, "updated_at": post.updated_at},
    )


def list_published_posts(repo: ports.PostRepository) -> list[dict[str, Any]]:
    """Public listing: published posts only, no actor required."""
    return repo.list_published_posts()


def get_published_post(
    repo: ports.PostRepository, post_id: int
) -> dict[str, Any]:
    """Public detail: the post only when published, else not-found."""
    row = repo.get_post(post_id)
    if row is None or row["state"] != "published":
        raise NotFoundError(f"Post {post_id} was not found.")
    return row
