"""Application authorization tests for User Story 3 (T026), no HTTP.

Every scenario asserts the rejection AND that post state plus history are
unchanged. Cross-author access is indistinguishable from a missing post.
"""

from typing import Any

import pytest

from blogspeclab.core.application import author_posts, review
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
    def now(self):
        from datetime import datetime, timezone

        return datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def ctx():
    repo, clock = FakePosts(), FakeClock()
    author = {"id": 1, "username": "a", "roles": "author"}
    other = {"id": 2, "username": "b", "roles": "author"}
    editor = {"id": 3, "username": "e", "roles": "editor"}
    dual = {"id": 4, "username": "d", "roles": "author,editor"}
    noroles = {"id": 5, "username": "n", "roles": ""}
    post = author_posts.create_post(
        repo, clock, author, title="T", content="C"
    )
    return {
        "repo": repo, "clock": clock, "author": author, "other": other,
        "editor": editor, "dual": dual, "noroles": noroles, "post": post,
    }


def _snapshot(ctx):
    post_id = ctx["post"]["id"]
    return (
        dict(ctx["repo"].rows[post_id]),
        list(ctx["repo"].decisions),
    )


def _assert_unchanged(ctx, before):
    post_id = ctx["post"]["id"]
    assert ctx["repo"].rows[post_id] == before[0]
    assert ctx["repo"].decisions == before[1]


def _missing_error(ctx):
    try:
        author_posts.get_post(ctx["repo"], ctx["author"], 999)
    except NotFoundError as exc:
        return str(exc)
    raise AssertionError("expected NotFoundError")


def test_cross_author_access_matches_missing_post(ctx):
    before = _snapshot(ctx)
    for op in ("get", "update", "delete", "submit"):
        try:
            if op == "get":
                author_posts.get_post(
                    ctx["repo"], ctx["other"], ctx["post"]["id"]
                )
            elif op == "update":
                author_posts.update_post(
                    ctx["repo"], ctx["clock"], ctx["other"],
                    ctx["post"]["id"], title="X",
                )
            elif op == "delete":
                author_posts.delete_post(
                    ctx["repo"], ctx["other"], ctx["post"]["id"]
                )
            else:
                author_posts.submit_post(
                    ctx["repo"], ctx["clock"], ctx["other"],
                    ctx["post"]["id"],
                )
        except NotFoundError as exc:
            assert str(exc) == _missing_error(ctx).replace("999", str(ctx["post"]["id"]))
        else:
            raise AssertionError(f"{op} should have been rejected")
    _assert_unchanged(ctx, before)


def test_direct_publish_without_approval_is_impossible(ctx):
    before = _snapshot(ctx)
    with pytest.raises(ForbiddenError):
        review.approve_post(
            ctx["repo"], ctx["clock"], ctx["editor"], ctx["post"]["id"]
        )
    _assert_unchanged(ctx, before)


def test_non_editor_cannot_review(ctx):
    pending = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["author"], ctx["post"]["id"]
    )
    before = (
        dict(ctx["repo"].rows[pending["id"]]), list(ctx["repo"].decisions)
    )
    for call in (
        lambda: review.list_review_queue(ctx["repo"], ctx["author"]),
        lambda: review.approve_post(
            ctx["repo"], ctx["clock"], ctx["author"], pending["id"]),
        lambda: review.reject_post(
            ctx["repo"], ctx["clock"], ctx["author"], pending["id"],
            reason="R"),
        lambda: review.revise_post(
            ctx["repo"], ctx["clock"], ctx["author"], pending["id"],
            title="X"),
        lambda: review.unpublish_post(
            ctx["repo"], ctx["clock"], ctx["author"], pending["id"],
            reason="R"),
    ):
        with pytest.raises(ForbiddenError):
            call()
    assert ctx["repo"].rows[pending["id"]] == before[0]
    assert ctx["repo"].decisions == before[1]


def test_user_without_roles_is_rejected_everywhere(ctx):
    with pytest.raises(ForbiddenError):
        author_posts.create_post(
            ctx["repo"], ctx["clock"], ctx["noroles"],
            title="T", content="C",
        )
    with pytest.raises(ForbiddenError):
        review.list_review_queue(ctx["repo"], ctx["noroles"])


def test_self_approval_and_self_revision_rejected(ctx):
    own = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["dual"], title="D", content="C"
    )
    own = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["dual"], own["id"]
    )
    before = (dict(ctx["repo"].rows[own["id"]]), list(ctx["repo"].decisions))
    with pytest.raises(ForbiddenError):
        review.approve_post(
            ctx["repo"], ctx["clock"], ctx["dual"], own["id"])
    with pytest.raises(ForbiddenError):
        review.revise_post(
            ctx["repo"], ctx["clock"], ctx["dual"], own["id"], title="X")
    assert ctx["repo"].rows[own["id"]] == before[0]
    assert ctx["repo"].decisions == before[1]


def test_published_post_locked_for_owner_editor_and_dual(ctx):
    published = review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"],
        author_posts.submit_post(
            ctx["repo"], ctx["clock"], ctx["author"], ctx["post"]["id"]
        )["id"],
    )
    before = (dict(ctx["repo"].rows[published["id"]]), list(ctx["repo"].decisions))
    with pytest.raises(ForbiddenError):
        author_posts.update_post(
            ctx["repo"], ctx["clock"], ctx["author"], published["id"],
            title="X",
        )
    with pytest.raises(ForbiddenError):
        author_posts.delete_post(
            ctx["repo"], ctx["author"], published["id"]
        )
    with pytest.raises(ForbiddenError):
        review.revise_post(
            ctx["repo"], ctx["clock"], ctx["editor"], published["id"],
            title="X",
        )
    with pytest.raises(NotFoundError):
        author_posts.update_post(
            ctx["repo"], ctx["clock"], ctx["dual"], published["id"],
            title="X",
        )
    assert ctx["repo"].rows[published["id"]] == before[0]
    assert ctx["repo"].decisions == before[1]


def test_rejected_operations_record_no_history(ctx):
    pending = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["author"], ctx["post"]["id"]
    )
    count = len(ctx["repo"].decisions)
    with pytest.raises(InvalidInputError):
        review.reject_post(
            ctx["repo"], ctx["clock"], ctx["editor"], pending["id"], reason=""
        )
    with pytest.raises(ForbiddenError):
        review.approve_post(
            ctx["repo"], ctx["clock"], ctx["author"], pending["id"]
        )
    assert len(ctx["repo"].decisions) == count
