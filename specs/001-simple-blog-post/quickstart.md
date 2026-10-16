# Quickstart: Simple Blog Post Management and Controlled Publishing

**Feature**: `001-simple-blog-post` | **Date**: 2026-10-13 | **Validated**: 2026-10-16 (commands below were executed against this repository)

## Prerequisites

- `Python 3.12+` (validated on `3.13.7`), dependencies from `pyproject.toml`.

## Setup and run (verified)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
# Demo credentials and database come ONLY from the environment (never commit secrets)
$env:DATABASE_PATH = ".\blogspeclab.db"
$env:SECRET_KEY = "<unique-local-secret>"
$env:BLOGSPECLAB_SEED_USERS = '[{"username":"<author>","password":"<pw>","roles":"author"},{"username":"<editor>","password":"<pw>","roles":"editor"}]'
.\.venv\Scripts\python.exe -c "import os; from blogspeclab.infra.data_access import db, repositories, seed; c = db.connect(os.environ['DATABASE_PATH']); db.init_schema(c); print(seed.seed_demo_users(c, repositories.Pbkdf2PasswordHasher())); c.commit()"
.\.venv\Scripts\python.exe -m flask --app blogspeclab.endpoints.api.app:create_app run
```

## Verified checks (live server)

- `GET /api/published` → `200` with the published list (anonymous).
- `GET /api/published/<id>` for a non-published id → `404` with `application/problem+json` and stable `code` (`POST_NOT_FOUND`).
- `GET /api/posts` without a session → `401` with `code` (`UNAUTHORIZED`).

## Authenticated flows (verified via test suite)

The full author flow (create, list own, edit, submit, delete) and editor flow
(review queue, revise, approve, reject, unpublish) are exercised by `pytest`
(see Test below). The contract-defined `POST /api/auth/login` and
`POST /api/auth/logout` routes are NOT implemented yet, so browser/`curl`
login is not currently possible; do not treat it as available.

## Test (verified)

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Domain/Application tests run without Flask or a database; repository and HTTP
tests use a temporary SQLite file.
