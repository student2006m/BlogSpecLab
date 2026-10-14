"""Application tests for User Story 1 (T013) with fake repositories.

No Flask, no SQLite: fakes implement the ports in-memory. Covers the six
author use cases plus ownership (cross-author reads as not-found),
server-side role checks, draft-only guards, and decision recording.
"""

from typing import Any

import pytest

from blogspeclab.core.application import author_posts
from blogspeclab.core.application.author_posts import (
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)


class FakePosts:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, Any]] = {}
        self.decisions: list[dict[str, Any]] = []
        self._next_id = 1

    def insert_post(self, row: dict[str, Any]) -> int:
        post_id = self._next_id
        self._next_id += 1
        self.rows[post_id] = {**row, "id": post_id}
        return post_id

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        return self.rows.get(post_id)

    def list_posts_by_owner(self, owner_id: int) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["owner_id"] == owner_id]

    def list_posts_by_state(self, state: str) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["state"] == state]

    def list_published_posts(self) -> list[dict[str, Any]]:
        return self.list_posts_by_state("published")

    def update_post(self, post_id: int, changes: dict[str, Any]) -> bool:
        if post_id not in self.rows:
            return False
        self.rows[post_id].update(changes)
        return True

    def delete_post(self, post_id: int) -> bool:
        return self.rows.pop(post_id, None) is not None

    def append_decision(self, row: dict[str, Any]) -> int:
        self.decisions.append({**row, "id": len(self.decisions) + 1})
        return len(self.decisions)


class FakeClock:
    def __init__(self) -> None:
        self.tick = 0

    def now(self):
        from datetime import datetime, timezone

        self.tick += 1
        return datetime(2026, 10, 14, self.tick, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def ctx():
    return {
        "repo": FakePosts(),
        "clock": FakeClock(),
        "author": {"id": 1, "username": "a", "roles": "author"},
        "other": {"id": 2, "username": "b", "roles": "author"},
    }


def _create(ctx, **kwargs):
    values = {"title": "T", "content": "C"}
    values.update(kwargs)
    return author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["author"], **values
    )


def test_create_returns_owned_draft(ctx):
    post = _create(ctx)
    assert post["owner_id"] == 1 and post["state"] == "draft"


def test_create_rejects_empty_input(ctx):
    with pytest.raises(InvalidInputError):
        _create(ctx, title="  ")


def test_non_author_role_is_forbidden(ctx):
    ctx["author"] = {"id": 1, "username": "a", "roles": ""}
    with pytest.raises(ForbiddenError):
        _create(ctx)


def test_get_own_post(ctx):
    post = _create(ctx)
    assert author_posts.get_post(ctx["repo"], ctx["author"], post["id"]) == post


def test_get_other_authors_post_is_not_found(ctx):
    post = _create(ctx)
    with pytest.raises(NotFoundError):
        author_posts.get_post(ctx["repo"], ctx["other"], post["id"])


def test_get_missing_post_is_not_found(ctx):
    with pytest.raises(NotFoundError):
        author_posts.get_post(ctx["repo"], ctx["author"], 999)


def test_list_returns_only_own_posts(ctx):
    _create(ctx, title="A1")
    author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["other"], title="B1", content="C"
    )
    listed = author_posts.list_own_posts(ctx["repo"], ctx["author"])
    assert [p["title"] for p in listed] == ["A1"]


def test_update_own_draft(ctx):
    post = _create(ctx)
    updated = author_posts.update_post(
        ctx["repo"], ctx["clock"], ctx["author"], post["id"],
        title="New", content="Body",
    )
    assert (updated["title"], updated["owner_id"]) == ("New", 1)


def test_update_other_authors_post_is_not_found(ctx):
    post = _create(ctx)
    with pytest.raises(NotFoundError):
        author_posts.update_post(
            ctx["repo"], ctx["clock"], ctx["other"], post["id"], title="X"
        )


def test_update_pending_post_is_forbidden(ctx):
    post = _create(ctx)
    author_posts.submit_post(ctx["repo"], ctx["clock"], ctx["author"], post["id"])
    with pytest.raises(ForbiddenError):
        author_posts.update_post(
            ctx["repo"], ctx["clock"], ctx["author"], post["id"], title="X"
        )


def test_delete_own_draft(ctx):
    post = _create(ctx)
    assert author_posts.delete_post(ctx["repo"], ctx["author"], post["id"]) is True
    with pytest.raises(NotFoundError):
        author_posts.get_post(ctx["repo"], ctx["author"], post["id"])


def test_delete_pending_post_is_forbidden(ctx):
    post = _create(ctx)
    author_posts.submit_post(ctx["repo"], ctx["clock"], ctx["author"], post["id"])
    with pytest.raises(ForbiddenError):
        author_posts.delete_post(ctx["repo"], ctx["author"], post["id"])


def test_submit_moves_to_pending_and_records_decision(ctx):
    post = _create(ctx)
    submitted = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["author"], post["id"]
    )
    assert submitted["state"] == "pending_review"
    assert len(ctx["repo"].decisions) == 1
    decision = ctx["repo"].decisions[0]
    assert (decision["post_id"], decision["actor_id"]) == (post["id"], 1)
    assert decision["action"] == "submit"


def test_submit_twice_is_forbidden(ctx):
    post = _create(ctx)
    author_posts.submit_post(ctx["repo"], ctx["clock"], ctx["author"], post["id"])
    with pytest.raises(ForbiddenError):
        author_posts.submit_post(
            ctx["repo"], ctx["clock"], ctx["author"], post["id"]
        )
