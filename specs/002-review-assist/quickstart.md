# Quickstart: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Date**: 2026-10-25 | **Validated**: 2026-10-25 (commands below were executed against this repository)

> Built on feature `001-simple-blog-post`; see its `quickstart.md` for the
> base setup. This guide covers only the review-assist capability.

## Prerequisites

- The `001` setup (virtualenv, install, schema, seeded demo users) — same
  commands as `specs/001-simple-blog-post/quickstart.md`.
- The app starts WITHOUT the review engine (the feature is optional).

## Provider configuration (environment only; never commit secrets)

```powershell
$env:BLOGSPECLAB_REVIEW_ASSIST_BASE_URL = "https://<openai-compatible-base>/v1"
$env:BLOGSPECLAB_REVIEW_ASSIST_API_KEY = "<provider-api-key>"
$env:BLOGSPECLAB_REVIEW_ASSIST_MODEL = "<model-id>"
# optional: $env:BLOGSPECLAB_REVIEW_ASSIST_TIMEOUT_SECONDS = "30"
```

With any missing variable the app still starts; the next step answers
`503 REVIEW_ASSIST_UNAVAILABLE` (no guessing, per spec FR-007).

## Run

```powershell
.\.venv\Scripts\python.exe -m flask --app blogspeclab.endpoints.api.app:create_app run
```

## Verified checks (live server)

- `POST /api/posts/<id>/review-assist` without a session → `401`
  `application/problem+json` with `code=UNAUTHORIZED`.

## Verified behavior (via test suite)

No `login` route exists yet (contract of `001`, not implemented), so
authenticated live calls are not possible outside the tests. The following
are covered by `pytest` (application + HTTP levels):

- Author reviews an owned `draft` post →
  `200 {post_id, state, assessment}` with a schema-valid assessment
  (`summary`, `issues[]`, `needs_more_information`, `missing_information`).
- "Needs more information" outcome → still `200` with explicit missing
  information and NO fabricated issues (FR-004).
- Missing or another user's post → `404` `POST_NOT_FOUND`; non-`draft` own
  post or non-author role → `403` (error semantics inherited from `001`).
- Review is advisory-only: post row and decision history are unchanged.
- Provider not configured, unreachable, or schema-invalid model output →
  `503` `REVIEW_ASSIST_UNAVAILABLE` problem+json (FR-007/FR-009).
- The HTTP adapter is unit-tested with an injected transport; a live call to
  a real provider key is NOT covered here.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
