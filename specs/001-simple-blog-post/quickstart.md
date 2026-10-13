# Quickstart: Simple Blog Post Management and Controlled Publishing

**Feature**: `001-simple-blog-post` | **Date**: 2026-10-13

> Valid AFTER implementation (`/speckit.tasks` + `/speckit.implement`). Do not invent commands for files that do not exist yet.

## Prerequisites

- `Python 3.12+`, Flask (see `pyproject.toml` after implementation).

## Setup and run (intended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
# configure demo credentials via environment (never commit secrets)
$env:BLOG01_AUTHOR_PASSWORD = "..."
$env:BLOG01_EDITOR_PASSWORD = "..."
flask --app blogspeclab run
```

## Exercise the flow

1. Login as demo author → `POST /api/auth/login`.
2. Create a draft → `POST /api/posts`; verify it appears in `GET /api/posts`.
3. Submit → `POST /api/posts/<id>/submit`; verify author edit now fails.
4. Login as a DIFFERENT demo editor → `GET /api/review-queue` shows the post.
5. Approve → `POST /api/posts/<id>/approve`; verify anonymous `GET /api/published` includes it.
6. Negative checks: direct publish of a draft fails; cross-author access returns `404`; self-approval returns `403`.

## Test (intended)

```powershell
pip install -e ".[dev]"
pytest
```

Domain/Application tests run without Flask or a database; repository tests use a temporary SQLite file.
