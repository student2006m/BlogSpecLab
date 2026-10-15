"""HTTP authorization + error-shape tests for User Story 3 (T027).

Real Flask app + real temporary SQLite. Covers 401/403/404 mapping,
indistinguishable 404s, self-approval 403s, spoofed roles/owners, tampered
sessions, stable problem+json codes, and no-leak guarantees.
"""

import pytest

from blogspeclab.endpoints.api.app import create_app
from blogspeclab.infra.data_access import db, repositories

PROBLEM_FIELDS = {"type", "title", "status", "code", "detail"}


@pytest.fixture()
def api(tmp_path):
    database_path = str(tmp_path / "authz.db")
    app = create_app({"TESTING": True, "DATABASE_PATH": database_path})
    connection = db.connect(database_path)
    db.init_schema(connection)
    hasher = repositories.Pbkdf2PasswordHasher(iterations=1000)
    store = repositories.SQLiteUserStore(connection)
    ids = {
        name: store.upsert_demo_user(name, hasher.hash_password("pw"), roles)
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


def _logout(client):
    with client.session_transaction() as session:
        session.clear()


def _pending(client, author_id, title="T"):
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": title, "content": "C"}
    ).get_json()["id"]
    assert client.post(f"/api/posts/{post_id}/submit").status_code == 200
    return post_id


def _problem(response, status, code):
    assert response.status_code == status
    assert response.content_type == "application/problem+json"
    body = response.get_json()
    assert set(body) == PROBLEM_FIELDS
    assert body["status"] == status
    assert body["code"] == code
    assert "Traceback" not in response.get_data(as_text=True)
    return body


def test_unauthenticated_protected_routes_return_401(api):
    client, _ = api
    routes = [
        ("post", "/api/posts", {"title": "T", "content": "C"}),
        ("get", "/api/posts", None),
        ("get", "/api/posts/1", None),
        ("patch", "/api/posts/1", {"title": "X"}),
        ("delete", "/api/posts/1", None),
        ("post", "/api/posts/1/submit", None),
        ("get", "/api/review-queue", None),
        ("patch", "/api/posts/1/revise", {"title": "X"}),
        ("post", "/api/posts/1/approve", None),
        ("post", "/api/posts/1/reject", {"reason": "R"}),
        ("post", "/api/posts/1/unpublish", {"reason": "R"}),
    ]
    for method, path, payload in routes:
        call = getattr(client, method)
        kwargs = {"json": payload} if payload is not None else {}
        response = call(path, **kwargs)
        _problem(response, 401, "UNAUTHORIZED")


def test_author_on_editor_routes_returns_403(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["author-a"])
    for method, path, payload in [
        ("get", "/api/review-queue", None),
        ("patch", f"/api/posts/{post_id}/revise", {"title": "X"}),
        ("post", f"/api/posts/{post_id}/approve", None),
        ("post", f"/api/posts/{post_id}/reject", {"reason": "R"}),
        ("post", f"/api/posts/{post_id}/unpublish", {"reason": "R"}),
    ]:
        call = getattr(client, method)
        kwargs = {"json": payload} if payload is not None else {}
        _problem(call(path, **kwargs), 403, "FORBIDDEN")


def test_missing_vs_other_authors_post_indistinguishable(api):
    client, ids = api
    _login(client, ids["author-b"])
    hidden_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    _login(client, ids["author-a"])
    missing = client.get("/api/posts/999999")
    other = client.get(f"/api/posts/{hidden_id}")
    assert missing.status_code == other.status_code == 404
    missing_body = _problem(missing, 404, "POST_NOT_FOUND")
    other_body = _problem(other, 404, "POST_NOT_FOUND")
    assert missing_body["title"] == other_body["title"]
    for body in (missing_body, other_body):
        assert "author-b" not in body["detail"]
        assert "Hidden" not in body.get("detail", "")


def test_self_approval_returns_403(api):
    client, ids = api
    post_id = _pending(client, ids["dual"])
    _login(client, ids["dual"])
    _problem(
        client.patch(f"/api/posts/{post_id}/revise", json={"title": "X"}),
        403, "FORBIDDEN",
    )
    _problem(client.post(f"/api/posts/{post_id}/approve"), 403, "FORBIDDEN")


def test_validation_errors_return_400(api):
    client, ids = api
    _login(client, ids["author-a"])
    _problem(
        client.post("/api/posts", json={"title": "", "content": "C"}),
        400, "BAD_REQUEST",
    )
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["ed"])
    _problem(
        client.post(f"/api/posts/{post_id}/reject", json={}), 400,
        "BAD_REQUEST",
    )


def test_spoofed_role_owner_or_status_have_no_effect(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["author-a"])
    spoof = client.post(
        f"/api/posts/{post_id}/approve",
        json={"roles": "editor"},
        headers={"X-Roles": "editor", "X-Editor": "true"},
    )
    _problem(spoof, 403, "FORBIDDEN")
    forged = client.post(
        "/api/posts",
        json={"title": "T", "content": "C", "owner_id": ids["ed"],
              "state": "published", "roles": "editor"},
    )
    assert forged.status_code == 201
    body = forged.get_json()
    assert body["owner_id"] == ids["author-a"]
    assert body["state"] == "draft"


def test_tampered_session_returns_401(api):
    client, _ = api
    with client.session_transaction() as session:
        session["user_id"] = 999999
    _problem(client.get("/api/posts"), 401, "UNAUTHORIZED")
    with client.session_transaction() as session:
        session["user_id"] = "editor"
    _problem(client.get("/api/posts"), 401, "UNAUTHORIZED")


def test_rejected_operations_leave_state_unchanged(api):
    client, ids = api
    post_id = _pending(client, ids["author-a"])
    _login(client, ids["author-b"])
    assert client.get(f"/api/posts/{post_id}").status_code == 404
    assert client.delete(f"/api/posts/{post_id}").status_code == 404
    _login(client, ids["author-a"])
    body = client.get(f"/api/posts/{post_id}").get_json()
    assert body["state"] == "pending_review"
    _logout(client)
    assert client.get("/api/published").get_json() == []
