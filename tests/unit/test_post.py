"""Domain unit tests for User Story 1 (T012).

Pure domain: no Flask, no sqlite3, no HTTP. Covers Post validation, ownership
immutability, draft-only guards, and User roles per spec.md / data-model.md.
"""

import pytest

from blogspeclab.core.domain.post import (
    DRAFT,
    PENDING_REVIEW,
    PUBLISHED,
    Post,
    StateError,
    ValidationError,
)
from blogspeclab.core.domain.user import User, parse_roles


def _make_post(**overrides):
    values = {
        "owner_id": 1,
        "title": "Hello",
        "content": "World",
        "now": "2026-10-14T00:00:00+00:00",
    }
    values.update(overrides)
    return Post.create(**values)


def test_states_have_spec_values():
    assert (DRAFT, PENDING_REVIEW, PUBLISHED) == (
        "draft",
        "pending_review",
        "published",
    )


def test_create_sets_draft_and_owner():
    post = _make_post(owner_id=7)
    assert post.state == DRAFT
    assert post.owner_id == 7
    assert post.title == "Hello"


def test_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        _make_post(title="   ")


def test_create_rejects_empty_content():
    with pytest.raises(ValidationError):
        _make_post(content="")


def test_revise_draft_updates_and_keeps_owner():
    post = _make_post(owner_id=3)
    post.revise("New", "Body", "2026-10-14T01:00:00+00:00")
    assert (post.title, post.content, post.owner_id) == ("New", "Body", 3)


def test_revise_rejects_empty_values():
    post = _make_post()
    with pytest.raises(ValidationError):
        post.revise("", "Body", "2026-10-14T01:00:00+00:00")


def test_revise_pending_is_forbidden():
    post = _make_post()
    post.submit("2026-10-14T01:00:00+00:00")
    with pytest.raises(StateError):
        post.revise("New", "Body", "2026-10-14T02:00:00+00:00")


def test_submit_moves_draft_to_pending():
    post = _make_post()
    post.submit("2026-10-14T01:00:00+00:00")
    assert post.state == PENDING_REVIEW


def test_submit_twice_is_forbidden():
    post = _make_post()
    post.submit("2026-10-14T01:00:00+00:00")
    with pytest.raises(StateError):
        post.submit("2026-10-14T02:00:00+00:00")


def test_ensure_deletable_allows_draft_only():
    _make_post().ensure_deletable()
    pending = _make_post()
    pending.submit("2026-10-14T01:00:00+00:00")
    with pytest.raises(StateError):
        pending.ensure_deletable()


def test_parse_roles_single_and_dual():
    assert parse_roles("author") == frozenset({"author"})
    assert parse_roles("author,editor") == frozenset({"author", "editor"})


def test_parse_roles_rejects_unknown():
    with pytest.raises(ValidationError):
        parse_roles("admin")


def test_user_has_role():
    user = User(id=1, username="a", roles=frozenset({"author", "editor"}))
    assert user.has_role("author") and user.has_role("editor")
    assert not user.has_role("reviewer")


def _pending_post(owner_id=1):
    post = _make_post(owner_id=owner_id)
    post.submit("2026-10-14T01:00:00+00:00")
    return post


def test_approve_publishes_directly():
    post = _pending_post()
    post.approve(9, "2026-10-14T02:00:00+00:00")
    assert post.state == PUBLISHED


def test_approve_and_revise_reject_self_approval():
    post = _pending_post(owner_id=5)
    with pytest.raises(StateError):
        post.approve(5, "2026-10-14T02:00:00+00:00")
    with pytest.raises(StateError):
        post.revise_by_editor(5, "X", "Y", "2026-10-14T02:00:00+00:00")


def test_approve_draft_is_forbidden():
    with pytest.raises(StateError):
        _make_post().approve(9, "2026-10-14T02:00:00+00:00")


def test_revise_by_editor_keeps_pending_and_owner():
    post = _pending_post(owner_id=5)
    post.revise_by_editor(9, "Fixed", "Body", "2026-10-14T02:00:00+00:00")
    assert (post.title, post.state, post.owner_id) == (
        "Fixed", PENDING_REVIEW, 5)


def test_reject_and_unpublish_require_reason():
    post = _pending_post()
    with pytest.raises(ValidationError):
        post.reject("  ", "2026-10-14T02:00:00+00:00")
    post.reject("Too short", "2026-10-14T02:00:00+00:00")
    assert post.state == DRAFT
    published = _pending_post()
    published.approve(9, "2026-10-14T02:00:00+00:00")
    with pytest.raises(ValidationError):
        published.unpublish("", "2026-10-14T03:00:00+00:00")
    published.unpublish("Mistake", "2026-10-14T03:00:00+00:00")
    assert published.state == DRAFT


def test_unpublish_draft_is_forbidden():
    with pytest.raises(StateError):
        _make_post().unpublish("R", "2026-10-14T02:00:00+00:00")
