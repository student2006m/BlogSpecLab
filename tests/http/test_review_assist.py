"""HTTP contract tests for smart review assist (T007).

Real Flask app + real temporary SQLite; the review provider is injected as a
test double through the composition seam. Wire format per
specs/002-review-assist/contracts/api.md; feature `001` error semantics.
"""

from typing import Any

import pytest

from blogspeclab.endpoints.api.app import create_app
from blogspeclab.infra.data_access import db, repositories

GOOD_RECORD = {
    "summary": "Looks fine.",
    "issues": [
        {
            "severity": "minor",
            "category": "clarity",
            "excerpt": "",
            "explanation": "Consider a longer opening.",
        }
    ],
    "needs_more_information": False,
    "missing_information": [],
}

NEEDS_INFO_RECORD = {
    "summary": "",
    "issues": [],
    "needs_more_information": True,
    "missing_information": ["Too short to review."],
}

BROKEN_RECORD = {"summary": 42}


class StubProvider:
    def __init__(self, record: dict[str, Any] | None, exc=None) -> None:
        self.record = record
        self.exc = exc

    def review_post(self, title: str, content: str) -> dict[str, Any]:
        if self.exc is not None:
            raise self.exc
        assert self.record is not None
        return self.record


def _make_app(tmp_path, provider):
    database_path = str(tmp_path / "assist.db")
    config: dict[str, Any] = {
        "TESTING": True,
        "DATABASE_PATH": database_path,
        "REVIEW_ASSIST_PROVIDER": provider,
    }
    app = create_app(config)
    connection = db.connect(database_path)
    db.init_schema(connection)
    hasher = repositories.Pbkdf2PasswordHasher(iterations=1000)
    store = repositories.SQLiteUserStore(connection)
    author_id = store.upsert_demo_user(
        "author-a", hasher.hash_password("pw-a"), "author"
    )
    other_id = store.upsert_demo_user(
        "author-b", hasher.hash_password("pw-b"), "author"
    )
    editor_id = store.upsert_demo_user(
        "editor-e", hasher.hash_password("pw-e"), "editor"
    )
    connection.commit()
    connection.close()
    return app, author_id, other_id, editor_id, database_path


def _login(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id


@pytest.fixture()
def api(tmp_path):
    app, author_id, other_id, editor_id, database_path = _make_app(
        tmp_path, StubProvider(GOOD_RECORD)
    )
    client = app.test_client()
    return app, client, author_id, other_id, editor_id, database_path


def _create_post(client, author_id):
    _login(client, author_id)
    return client.post(
        "/api/posts", json={"title": "T", "content": "Some content."}
    ).get_json()["id"]


def test_review_assist_returns_structured_assessment(api):
    _, client, author_id, *_ = api
    post_id = _create_post(client, author_id)
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 200
    body = response.get_json()
    assert body["post_id"] == post_id
    assert body["state"] == "draft"
    assert body["assessment"]["summary"] == "Looks fine."
    assert body["assessment"]["issues"][0]["severity"] == "minor"
    assert response.content_type == "application/json"


def test_review_assist_needs_more_information_outcome(api):
    _, client, author_id, _, _, _ = api
    post_id = _create_post(client, author_id)
    with client.application.app_context():
        client.application.config["REVIEW_ASSIST_PROVIDER"] = StubProvider(
            NEEDS_INFO_RECORD
        )
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 200
    assessment = response.get_json()["assessment"]
    assert assessment["needs_more_information"] is True
    assert assessment["missing_information"] == ["Too short to review."]
    assert assessment["issues"] == []


def test_review_assist_returns_401_unauthenticated(api):
    _, client, author_id, _, _, _ = api
    post_id = _create_post(client, author_id)
    _login(client, -1)  # unknown user: treated as unauthenticated
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 401
    assert response.get_json()["code"] == "UNAUTHORIZED"


def test_review_assist_other_users_post_returns_404(api):
    _, client, author_id, other_id, _, _ = api
    post_id = _create_post(client, other_id)
    _login(client, author_id)
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 404
    assert response.get_json()["code"] == "POST_NOT_FOUND"


def test_review_assist_missing_post_returns_404(api):
    _, client, author_id, _, _, _ = api
    _login(client, author_id)
    response = client.post("/api/posts/9999/review-assist")
    assert response.status_code == 404


def test_review_assist_non_draft_returns_403(api):
    _, client, author_id, _, _, _ = api
    post_id = _create_post(client, author_id)
    assert client.post(f"/api/posts/{post_id}/submit").status_code == 200
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 403
    assert response.get_json()["code"] == "FORBIDDEN"


def test_review_assist_non_author_returns_403(api):
    _, client, _, _, editor_id, _ = api
    _login(client, editor_id)
    response = client.post("/api/posts/1/review-assist")
    assert response.status_code == 403


def test_review_assist_unconfigured_provider_returns_503(tmp_path):
    app, author_id, *_ = _make_app(tmp_path, StubProvider(GOOD_RECORD))
    app.config["REVIEW_ASSIST_PROVIDER"] = None
    client = app.test_client()
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 503
    assert response.content_type == "application/problem+json"
    assert response.get_json()["code"] == "REVIEW_ASSIST_UNAVAILABLE"


def test_review_assist_broken_provider_output_returns_503(tmp_path):
    app, author_id, *_ = _make_app(
        tmp_path, StubProvider(BROKEN_RECORD)
    )
    client = app.test_client()
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    response = client.post(f"/api/posts/{post_id}/review-assist")
    assert response.status_code == 503
    assert response.get_json()["code"] == "REVIEW_ASSIST_UNAVAILABLE"


def test_review_assist_leaves_post_and_history_unchanged(api):
    _, client, author_id, _, _, database_path = api
    post_id = _create_post(client, author_id)
    client.post(f"/api/posts/{post_id}/review-assist")
    connection = db.connect(database_path)
    try:
        store = repositories.SQLiteUserStore(connection)
        repo = repositories.SQLitePostRepository(connection)
        row = repo.get_post(post_id)
        assert row is not None
        assert row["state"] == "draft"
        assert row["title"] == "T"
        assert row["content"] == "Some content."
    finally:
        connection.close()


def test_review_assist_success_never_appends_decisions(api):
    _, client, author_id, _, _, database_path = api
    post_id = _create_post(client, author_id)
    client.post(f"/api/posts/{post_id}/review-assist")
    connection = db.connect(database_path)
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM decisions WHERE post_id = ?", (post_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == 0
    finally:
        connection.close()
