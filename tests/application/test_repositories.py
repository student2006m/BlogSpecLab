"""Repository tests on temporary SQLite, User Story 2 support (T021).

Verifies row mapping, append-only decision history, transaction atomicity
(state change + history commit together or not at all), and the demo-user
store backed by the real schema from T004 (unchanged here).
"""

import pytest

from blogspeclab.infra.data_access import db, repositories


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(str(tmp_path / "repo.db"))
    db.init_schema(connection)
    store = repositories.SQLiteUserStore(connection)
    hasher = repositories.Pbkdf2PasswordHasher(iterations=1000)
    store.upsert_demo_user("u1", hasher.hash_password("p1"), "author")
    store.upsert_demo_user("u2", hasher.hash_password("p2"), "author,editor")
    connection.commit()
    yield connection
    connection.close()


def _post(owner_id=1, state="draft"):
    return {
        "owner_id": owner_id,
        "title": "T",
        "content": "C",
        "state": state,
        "created_at": "2026-10-14T00:00:00+00:00",
        "updated_at": "2026-10-14T00:00:00+00:00",
    }


def test_post_crud_roundtrip(conn):
    repo = repositories.SQLitePostRepository(conn)
    post_id = repo.insert_post(_post())
    assert repo.get_post(post_id)["title"] == "T"
    assert repo.update_post(post_id, {"state": "pending_review"})
    assert repo.get_post(post_id)["state"] == "pending_review"
    assert repo.delete_post(post_id)
    assert repo.get_post(post_id) is None
    conn.commit()


def test_state_and_owner_listings(conn):
    repo = repositories.SQLitePostRepository(conn)
    repo.insert_post(_post(owner_id=1, state="pending_review"))
    repo.insert_post(_post(owner_id=2, state="pending_review"))
    repo.insert_post(_post(owner_id=1, state="published"))
    assert len(repo.list_posts_by_state("pending_review")) == 2
    assert [p["owner_id"] for p in repo.list_posts_by_owner(1)] == [1, 1]
    assert len(repo.list_published_posts()) == 1
    conn.commit()


def test_decisions_are_append_only_and_ordered(conn):
    repo = repositories.SQLitePostRepository(conn)
    post_id = repo.insert_post(_post())
    for action in ("submit", "approve_publish"):
        repo.append_decision(
            {
                "post_id": post_id,
                "actor_id": 2,
                "action": action,
                "reason": None,
                "created_at": "2026-10-14T00:00:00+00:00",
            }
        )
    rows = conn.execute(
        "SELECT action, actor_id FROM decisions ORDER BY id"
    ).fetchall()
    assert [(r["action"], r["actor_id"]) for r in rows] == [
        ("submit", 2),
        ("approve_publish", 2),
    ]
    assert not hasattr(repo, "update_decision")
    assert not hasattr(repo, "delete_decision")
    conn.commit()


def test_state_change_and_history_commit_atomically(conn):
    repo = repositories.SQLitePostRepository(conn)
    post_id = repo.insert_post(_post())
    conn.commit()
    with pytest.raises(RuntimeError):
        with db.transaction(conn):
            repo.update_post(post_id, {"state": "pending_review"})
            raise RuntimeError("history write failed")
    assert repo.get_post(post_id)["state"] == "draft"


def test_user_store_and_hasher(conn):
    hasher = repositories.Pbkdf2PasswordHasher(iterations=1000)
    store = repositories.SQLiteUserStore(conn)
    user_id = store.upsert_demo_user(
        "ed", hasher.hash_password("pw"), "editor"
    )
    row = store.get_by_id(user_id)
    assert row["username"] == "ed" and row["roles"] == "editor"
    assert store.get_by_username("missing") is None
    assert hasher.verify("pw", row["password_hash"])
    assert not hasher.verify("nope", row["password_hash"])
    assert not hasher.verify("pw", "garbage-hash")
    conn.commit()
