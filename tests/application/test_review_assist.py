"""Application tests for smart review assist (T003) with fakes.

No Flask, no SQLite, no network. Covers role/ownership/draft guards, the
needs-more-information passthrough, provider failure mapping, and the
advisory-only guarantee (no writes, no decision entries, state unchanged).
"""

from typing import Any

import pytest

from blogspeclab.core.application import review_assist as use_cases
from blogspeclab.core.application.author_posts import (
    ForbiddenError,
    NotFoundError,
)

DRAFT_ROW = {
    "id": 7,
    "owner_id": 1,
    "title": "Draft title",
    "content": "Some draft content worth reviewing.",
    "state": "draft",
    "created_at": "2026-10-25T00:00:00+00:00",
    "updated_at": "2026-10-25T00:00:00+00:00",
}

GOOD_RECORD = {
    "summary": "Looks clear enough.",
    "issues": [
        {
            "severity": "minor",
            "category": "spelling",
            "excerpt": "recieve",
            "explanation": "Common misspelling: receive.",
        }
    ],
    "needs_more_information": False,
    "missing_information": [],
}

NEEDS_INFO_RECORD = {
    "summary": "",
    "issues": [],
    "needs_more_information": True,
    "missing_information": ["The content is too short to review."],
}


class FakePostRepository:
    """In-memory port double; records every mutating call."""

    def __init__(self, rows: dict[int, dict[str, Any]]) -> None:
        self.rows = dict(rows)
        self.decisions: list[dict[str, Any]] = []
        self.write_calls = 0

    def _record_write(self) -> None:
        self.write_calls += 1

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        return self.rows.get(post_id)

    def insert_post(self, row: dict[str, Any]) -> int:
        self._record_write()
        raise AssertionError("review assist must never insert posts")

    def update_post(self, post_id: int, changes: dict[str, Any]) -> bool:
        self._record_write()
        raise AssertionError("review assist must never update posts")

    def delete_post(self, post_id: int) -> bool:
        self._record_write()
        raise AssertionError("review assist must never delete posts")

    def append_decision(self, row: dict[str, Any]) -> int:
        self._record_write()
        raise AssertionError("review assist must never append decisions")

    def list_posts_by_owner(self, owner_id: int) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["owner_id"] == owner_id]

    def list_posts_by_state(self, state: str) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["state"] == state]

    def list_published_posts(self) -> list[dict[str, Any]]:
        return self.list_posts_by_state("published")


class ScriptedProvider:
    """Fake ReviewAssistProvider returning a record or raising."""

    def __init__(self, record: dict[str, Any] | None, exc=None) -> None:
        self.record = record
        self.exc = exc
        self.calls: list[tuple[str, str]] = []

    def review_post(self, title: str, content: str) -> dict[str, Any]:
        self.calls.append((title, content))
        if self.exc is not None:
            raise self.exc
        assert self.record is not None
        return self.record


@pytest.fixture()
def repo():
    return FakePostRepository({7: dict(DRAFT_ROW)})


@pytest.fixture()
def author():
    return {"id": 1, "username": "a", "roles": "author"}


def test_assisted_draft_returns_structured_result(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    result = use_cases.request_review_assist(repo, author, provider, 7)
    assert result["post_id"] == 7
    assert result["state"] == "draft"
    assert result["assessment"]["needs_more_information"] is False
    assert result["assessment"]["issues"][0]["severity"] == "minor"
    assert provider.calls == [("Draft title", "Some draft content worth reviewing.")]


def test_needs_more_information_passes_through(repo, author):
    provider = ScriptedProvider(NEEDS_INFO_RECORD)
    result = use_cases.request_review_assist(repo, author, provider, 7)
    assert result["assessment"]["needs_more_information"] is True
    assert result["assessment"]["missing_information"] == [
        "The content is too short to review."
    ]


def test_missing_post_returns_not_found(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    with pytest.raises(NotFoundError):
        use_cases.request_review_assist(repo, author, provider, 999)
    assert provider.calls == []


def test_other_users_post_returns_not_found(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    with pytest.raises(NotFoundError):
        use_cases.request_review_assist(repo, {"id": 2, "roles": "author"}, provider, 7)
    assert provider.calls == []


def test_non_author_role_returns_forbidden(repo):
    provider = ScriptedProvider(GOOD_RECORD)
    with pytest.raises(ForbiddenError):
        use_cases.request_review_assist(repo, {"id": 1, "roles": "editor"}, provider, 7)
    assert provider.calls == []


def test_non_draft_own_post_returns_forbidden(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    repo.rows[7]["state"] = "pending_review"
    with pytest.raises(ForbiddenError):
        use_cases.request_review_assist(repo, author, provider, 7)
    assert provider.calls == []


def test_published_own_post_returns_forbidden(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    repo.rows[7]["state"] = "published"
    with pytest.raises(ForbiddenError):
        use_cases.request_review_assist(repo, author, provider, 7)
    assert provider.calls == []


def test_provider_failure_maps_to_unavailable(repo, author):
    provider = ScriptedProvider(None, exc=use_cases.ProviderError("boom"))
    with pytest.raises(use_cases.ReviewUnavailableError):
        use_cases.request_review_assist(repo, author, provider, 7)


def test_provider_unexpected_error_maps_to_unavailable(repo, author):
    provider = ScriptedProvider(None, exc=RuntimeError("connection down"))
    with pytest.raises(use_cases.ReviewUnavailableError):
        use_cases.request_review_assist(repo, author, provider, 7)


def test_schema_broken_provider_output_maps_to_unavailable(repo, author):
    provider = ScriptedProvider({"summary": 42, "issues": "lots"})
    with pytest.raises(use_cases.ReviewUnavailableError):
        use_cases.request_review_assist(repo, author, provider, 7)


def test_review_never_writes(repo, author):
    provider = ScriptedProvider(GOOD_RECORD)
    snapshot = dict(repo.rows[7])
    use_cases.request_review_assist(repo, author, provider, 7)
    assert repo.rows[7] == snapshot
    assert repo.write_calls == 0
    assert not repo.decisions
