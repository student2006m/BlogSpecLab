"""Application tests for User Story 2 (T019) with fake repositories.

No Flask, no SQLite. Covers review queue, approve (publishes), reject /
unpublish with mandatory reasons, editor revision with history, separation
of duties, and the public-listing queries.
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
    def __init__(self) -> None:
        self.tick = 0

    def now(self):
        from datetime import datetime, timezone

        self.tick += 1
        return datetime(2026, 10, 14, self.tick, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def ctx():
    repo, clock = FakePosts(), FakeClock()
    author_a = {"id": 1, "username": "a", "roles": "author"}
    author_b = {"id": 2, "username": "b", "roles": "author"}
    editor = {"id": 3, "username": "e", "roles": "editor"}
    dual = {"id": 4, "username": "d", "roles": "author,editor"}
    pending = author_posts.create_post(
        repo, clock, author_a, title="T", content="C"
    )
    pending = author_posts.submit_post(repo, clock, author_a, pending["id"])
    return {
        "repo": repo, "clock": clock, "author_a": author_a,
        "author_b": author_b, "editor": editor, "dual": dual,
        "pending": pending,
    }


def test_queue_lists_all_pending_regardless_of_owner(ctx):
    author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["author_b"], title="B", content="C"
    )
    second = author_posts.list_own_posts(ctx["repo"], ctx["author_b"])[0]
    author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["author_b"], second["id"]
    )
    queue = review.list_review_queue(ctx["repo"], ctx["editor"])
    assert {p["id"] for p in queue} == {ctx["pending"]["id"], second["id"]}


def test_queue_rejects_non_editor(ctx):
    with pytest.raises(ForbiddenError):
        review.list_review_queue(ctx["repo"], ctx["author_a"])


def test_approve_publishes_and_records_history(ctx):
    approved = review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    assert approved["state"] == "published"
    decision = ctx["repo"].decisions[-1]
    assert (decision["action"], decision["actor_id"]) == ("approve_publish", 3)
    assert decision["created_at"]


def test_approve_own_post_is_forbidden(ctx):
    own = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["dual"], title="D", content="C"
    )
    own = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["dual"], own["id"]
    )
    with pytest.raises(ForbiddenError):
        review.approve_post(ctx["repo"], ctx["clock"], ctx["dual"], own["id"])


def test_approve_draft_or_published_is_forbidden(ctx):
    draft = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["author_a"], title="D", content="C"
    )
    with pytest.raises(ForbiddenError):
        review.approve_post(
            ctx["repo"], ctx["clock"], ctx["editor"], draft["id"]
        )
    review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    with pytest.raises(ForbiddenError):
        review.approve_post(
            ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
        )


def test_approve_missing_post_is_not_found(ctx):
    with pytest.raises(NotFoundError):
        review.approve_post(ctx["repo"], ctx["clock"], ctx["editor"], 999)


def test_reject_returns_to_draft_with_reason(ctx):
    rejected = review.reject_post(
        ctx["repo"], ctx["clock"], ctx["editor"],
        ctx["pending"]["id"], reason="Too short",
    )
    assert rejected["state"] == "draft"
    decision = ctx["repo"].decisions[-1]
    assert (decision["action"], decision["reason"]) == ("reject", "Too short")


def test_reject_without_reason_is_invalid(ctx):
    with pytest.raises(InvalidInputError):
        review.reject_post(
            ctx["repo"], ctx["clock"], ctx["editor"],
            ctx["pending"]["id"], reason="   ",
        )


def test_reject_draft_is_forbidden(ctx):
    draft = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["author_a"], title="D", content="C"
    )
    with pytest.raises(ForbiddenError):
        review.reject_post(
            ctx["repo"], ctx["clock"], ctx["editor"], draft["id"], reason="R"
        )


def test_revise_updates_content_and_records_history(ctx):
    revised = review.revise_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"],
        title="Fixed", content="Body",
    )
    assert (revised["title"], revised["state"]) == ("Fixed", "pending_review")
    decision = ctx["repo"].decisions[-1]
    assert (decision["action"], decision["actor_id"]) == ("editor_edit", 3)


def test_revise_own_post_is_forbidden(ctx):
    own = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["dual"], title="D", content="C"
    )
    own = author_posts.submit_post(
        ctx["repo"], ctx["clock"], ctx["dual"], own["id"]
    )
    with pytest.raises(ForbiddenError):
        review.revise_post(
            ctx["repo"], ctx["clock"], ctx["dual"], own["id"], title="X"
        )


def test_revise_empty_values_are_invalid(ctx):
    with pytest.raises(InvalidInputError):
        review.revise_post(
            ctx["repo"], ctx["clock"], ctx["editor"],
            ctx["pending"]["id"], title="  ",
        )


def test_unpublish_returns_to_draft_with_reason(ctx):
    review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    unpublished = review.unpublish_post(
        ctx["repo"], ctx["clock"], ctx["editor"],
        ctx["pending"]["id"], reason="Error found",
    )
    assert unpublished["state"] == "draft"
    actions = [d["action"] for d in ctx["repo"].decisions]
    assert actions == ["submit", "approve_publish", "unpublish"]


def test_unpublish_without_reason_is_invalid(ctx):
    review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    with pytest.raises(InvalidInputError):
        review.unpublish_post(
            ctx["repo"], ctx["clock"], ctx["editor"],
            ctx["pending"]["id"], reason="",
        )


def test_unpublish_draft_is_forbidden(ctx):
    draft = author_posts.create_post(
        ctx["repo"], ctx["clock"], ctx["author_a"], title="D", content="C"
    )
    with pytest.raises(ForbiddenError):
        review.unpublish_post(
            ctx["repo"], ctx["clock"], ctx["editor"], draft["id"], reason="R"
        )


def test_public_listing_shows_only_published(ctx):
    assert review.list_published_posts(ctx["repo"]) == []
    review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    assert [p["id"] for p in review.list_published_posts(ctx["repo"])] == [
        ctx["pending"]["id"]
    ]


def test_get_published_post(ctx):
    with pytest.raises(NotFoundError):
        review.get_published_post(ctx["repo"], ctx["pending"]["id"])
    review.approve_post(
        ctx["repo"], ctx["clock"], ctx["editor"], ctx["pending"]["id"]
    )
    assert review.get_published_post(
        ctx["repo"], ctx["pending"]["id"]
    )["state"] == "published"
