"""HTTP contract tests for the author API, User Story 1 (T014).

Real Flask app + real temporary SQLite (no mocks at the HTTP boundary).
Status codes follow contracts/api.md: 201/200/204 on success, 400 for
validation, 401 unauthenticated, 404 for missing or other authors' posts,
403 for wrong-state operations on the caller's own post.
"""

import pytest

from blogspeclab.endpoints.api.app import create_app
from blogspeclab.infra.data_access import db, repositories


@pytest.fixture()
def api(tmp_path):
    database_path = str(tmp_path / "api.db")
    app = create_app({"TESTING": True, "DATABASE_PATH": database_path})
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
    connection.commit()
    connection.close()
    client = app.test_client()
    return app, client, author_id, other_id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id


def test_create_returns_201(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    response = client.post("/api/posts", json={"title": "T", "content": "C"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["owner_id"] == author_id and body["state"] == "draft"
    assert set(body) >= {
        "id", "owner_id", "title", "content", "state",
        "created_at", "updated_at",
    }


def test_create_empty_title_returns_400_problem(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    response = client.post("/api/posts", json={"title": " ", "content": "C"})
    assert response.status_code == 400
    assert response.content_type == "application/problem+json"
    assert response.get_json()["code"]


def test_unauthenticated_create_returns_401(api):
    _, client, _, _ = api
    response = client.post("/api/posts", json={"title": "T", "content": "C"})
    assert response.status_code == 401


def test_list_shows_only_own_posts(api):
    _, client, author_id, other_id = api
    _login(client, author_id)
    client.post("/api/posts", json={"title": "Mine", "content": "C"})
    _login(client, other_id)
    client.post("/api/posts", json={"title": "Theirs", "content": "C"})
    _login(client, author_id)
    body = client.get("/api/posts").get_json()
    assert [p["title"] for p in body] == ["Mine"]


def test_get_other_authors_post_returns_404_without_leak(api):
    _, client, author_id, other_id = api
    _login(client, other_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    _login(client, author_id)
    response = client.get(f"/api/posts/{post_id}")
    assert response.status_code == 404
    assert "NOT_FOUND" in response.get_json()["code"]


def test_update_own_draft_returns_200(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    response = client.patch(
        f"/api/posts/{post_id}", json={"title": "New", "content": "B"}
    )
    assert response.status_code == 200
    assert response.get_json()["title"] == "New"


def test_update_pending_post_returns_403(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    client.post(f"/api/posts/{post_id}/submit")
    response = client.patch(f"/api/posts/{post_id}", json={"title": "X"})
    assert response.status_code == 403


def test_delete_own_draft_returns_204(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    assert client.delete(f"/api/posts/{post_id}").status_code == 204
    assert client.get(f"/api/posts/{post_id}").status_code == 404


def test_delete_other_authors_post_returns_404(api):
    _, client, author_id, other_id = api
    _login(client, other_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    _login(client, author_id)
    assert client.delete(f"/api/posts/{post_id}").status_code == 404


def test_submit_moves_to_pending_review(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    response = client.post(f"/api/posts/{post_id}/submit")
    assert response.status_code == 200
    assert response.get_json()["state"] == "pending_review"


def test_second_submit_returns_403(api):
    _, client, author_id, _ = api
    _login(client, author_id)
    post_id = client.post(
        "/api/posts", json={"title": "T", "content": "C"}
    ).get_json()["id"]
    client.post(f"/api/posts/{post_id}/submit")
    assert client.post(f"/api/posts/{post_id}/submit").status_code == 403


def test_unauthenticated_list_returns_401(api):
    _, client, _, _ = api
    assert client.get("/api/posts").status_code == 401
