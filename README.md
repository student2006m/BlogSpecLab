# BlogSpecLab

An educational `Python` / `Flask` system for managing blog posts with
controlled publishing of approved content, built with
Specification-Driven Development (`Spec Kit`).

Authors manage their own draft posts; editors review a cross-ownership
queue, then approve/publish, reject, revise, or unpublish — with mandatory
reasons, separation of duties (no self-approval), and append-only history.
Before submitting, an author can request an advisory-only, AI-assisted
smart review of the draft (structured result; never modifies, approves,
or publishes).

## Stack

- `Python 3.12+`, `Flask`, `SQLite` (stdlib `sqlite3`, no ORM)
- Smart review assist: OpenAI-compatible provider over stdlib
  `urllib` (no extra pip dependency; optional — the app runs without it)
- `pytest` for tests
- See `docs/architecture/technical-baseline.md` for project-wide decisions
  and `AGENTS.md` for the agent working guide.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_PATH = ".\blogspeclab.db"
$env:SECRET_KEY = "<unique-local-secret>"
$env:BLOGSPECLAB_SEED_USERS = '[{"username":"<author>","password":"<pw>","roles":"author"},{"username":"<editor>","password":"<pw>","roles":"editor"}]'
.\.venv\Scripts\python.exe -m flask --app blogspeclab.endpoints.api.app:create_app run
```

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Docs

- Constitution (binding principles): `.specify/memory/constitution.md`
- Feature 001 (core workflow): `specs/001-simple-blog-post/`
- Feature 002 (smart review assist): `specs/002-review-assist/`
- Validated walkthroughs: `specs/001-simple-blog-post/quickstart.md` and
  `specs/002-review-assist/quickstart.md`
- HTTP contracts: `specs/001-simple-blog-post/contracts/api.md` and
  `specs/002-review-assist/contracts/api.md`

## Smart Review Assist (optional)

Configure the engine through the environment only (values stay outside the
repository):

```powershell
$env:BLOGSPECLAB_REVIEW_ASSIST_BASE_URL = "https://<openai-compatible-base>/v1"
$env:BLOGSPECLAB_REVIEW_ASSIST_API_KEY = "<provider-api-key>"
$env:BLOGSPECLAB_REVIEW_ASSIST_MODEL = "<model-id>"
```

Endpoint: `POST /api/posts/<id>/review-assist` → `200` with a structured
assessment (`summary`, `issues[]`, `needs_more_information`,
`missing_information`). Without configuration the endpoint answers
`503 REVIEW_ASSIST_UNAVAILABLE`.

## Status

Implemented and tested: author post management, editor review and
controlled publishing, anonymous published listing, authorization
enforcement, and advisory-only smart review assist (151 tests passing).

Not yet implemented: the contract-defined `POST /api/auth/login` and
`POST /api/auth/logout` routes — authenticated flows are currently covered
by the test suite only.
