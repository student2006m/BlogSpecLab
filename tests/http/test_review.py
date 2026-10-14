"""HTTP contract tests for review + public endpoints, US2 (T020).

Real Flask app + real temporary SQLite. Authentication is injected directly
into the session (the login/logout routes have no task coverage yet, so they
are intentionally NOT built here). Codes follow contracts/api.md; wrong-state
rejections on reject/unpublish use 403 per FR-014 (contract is silent there).
"""

import pytest

from blogspeclab.endpoints.api.app import create_app
from blogspeclab.infra.data_access import db, repositories


@pytest.fixture()
def api(tmp_path):
    database_path = str(tmp_path / "review.db")
    app = create_app({"TESTING": True, "DATABASE_PATH": database_path})
    connection = db.connect(database_path)
    db.init_schema(connection)
    hasher = repositories.Pbkdf2PasswordHasher(iterations=1000)
    store = repositories.SQLiteUserStore(connection)
    ids = {
        name: store.upsert_demo_user(
            name, hasher.hash_password("pw"), roles
        )
        for name, roles in {
            "author-a": "author",
            "author-b": "author",
            "ed": "editor",
            "dual": "author,editor",
        }.items()
    }
    connection.commit()
    connection.close()
    return app.test_client(), ids


def _login(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id


def _pending(client, author_id, title="T"):
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": title, "content": "C"}
    ).get_json()["id"]
    assert client.post(f"/api/posts/{post_id}/submit").status_code == 200
    return post_id


def test_queue_lists_all_pending_for_editor(api):
    client, ids = api
    first = _pending(client, ids["author-a"], "A")
    second = _pending(client, ids["author-b"], "B")
    _login(client, ids["ed"])
    body = client.get("/api/review-queue").get_json()
    assert {p["id"] for p in body} == {first, second}


def test_queue_forbids_author_and_anonymous(api):
    client, ids = api
    _pending(client, ids["author-a"])
    _login(client, ids["author-a"])
    assert client.get("/api/review-queue").status_code == 403
    with client.session_transaction() as session:
        session.clear()
    assert client.get("/api/review-queue").status_code == 401


def test_revise_then_approve_publishes(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    revised = client.patch(
        f"/api/posts/{post_id}/revise", json={"title": "Fixed"}
    )
    assert revised.status_code == 200
    assert revised.get_json()["title"] == "Fixed"
    approved = client.post(f"/api/posts/{post_id}/approve")
    assert approved.status_code == 200
    assert approved.get_json()["state"] == "published"


def test_self_revise_and_self_approve_return_403(api):
    client, ids = api
    post_id = _pending(client, ids["dual"])
    _login(client, ids["dual"])
    assert client.patch(
        f"/api/posts/{post_id}/revise", json={"title": "X"}
    ).status_code == 403
    assert client.post(f"/api/posts/{post_id}/approve").status_code == 403


def test_revise_empty_value_returns_400(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    assert client.patch(
        f"/api/posts/{post_id}/revise", json={"title": " "}
    ).status_code == 400


def test_revise_missing_returns_404(api):
    client, ids = api
    _login(client, ids["ed"])
    response = client.patch("/api/posts/999/revise", json={"title": "X"})
    assert response.status_code == 404
    assert "NOT_FOUND" in response.get_json()["code"]


def test_approve_draft_returns_403(api):
    client, ids = api
    _login(client, ids["author-a"])
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    _login(client, ids["ed"])
    assert client.post(f"/api/posts/{post_id}/approve").status_code == 403


def test_reject_returns_to_draft(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    response = client.post(
        f"/api/posts/{post_id}/reject", json={"reason": "Too short"}
    )
    assert response.status_code == 200
    assert response.get_json()["state"] == "draft"


def test_reject_without_reason_returns_400(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    assert client.post(
        f"/api/posts/{post_id}/reject", json={"reason": "  "}
    ).status_code == 400
    assert client.post(
        f"/api/posts/{post_id}/reject", json={}
    ).status_code == 400


def test_unpublish_leaves_public_listing(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    client.post(f"/api/posts/{post_id}/approve")
    assert client.get(f"/api/published/{post_id}").status_code == 200
    response = client.post(
        f"/api/posts/{post_id}/unpublish", json={"reason": "Mistake"}
    )
    assert response.status_code == 200
    assert response.get_json()["state"] == "draft"
    assert client.get(f"/api/published/{post_id}").status_code == 404
    assert client.get("/api/published").get_json() == []


def test_unpublish_without_reason_returns_400(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    client.post(f"/api/posts/{post_id}/approve")
    assert client.post(
        f"/api/posts/{post_id}/unpublish", json={}
    ).status_code == 400


def test_public_listing_hides_unpublished_anonymously(api):
    client, ids = api
    _pending(client, ids["author-a"], "Hidden")
    published = _pending(client, ids["author-b"], "Shown")
    _login(client, ids["ed"])
    client.post(f"/api/posts/{published}/approve")
    with client.session_transaction() as session:
        session.clear()
    body = client.get("/api/published").get_json()
    assert [p["title"] for p in body] == ["Shown"]
    assert client.get(f"/api/published/{published}").status_code == 200


def test_error_bodies_are_problem_json(api):
    client, ids = api
    _login(client, ids["ed"])
    response = client.patch("/api/posts/999/revise", json={"title": "X"})
    assert response.content_type == "application/problem+json"
    body = response.get_json()
    assert set(body) == {"type", "title", "status", "code", "detail"}
    assert body["status"] == 404
