# BlogSpecLab

An educational `Python` / `Flask` system for managing blog posts with
controlled publishing of approved content, built with
Specification-Driven Development (`Spec Kit`).

Authors manage their own draft posts; editors review a cross-ownership
queue, then approve/publish, reject, revise, or unpublish — with mandatory
reasons, separation of duties (no self-approval), and append-only history.

## Stack

- `Python 3.12+`, `Flask`, `SQLite` (stdlib `sqlite3`, no ORM)
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
- Feature spec, plan, and tasks: `specs/001-simple-blog-post/`
- Validated walkthrough: `specs/001-simple-blog-post/quickstart.md`
- HTTP contract: `specs/001-simple-blog-post/contracts/api.md`

## Status

Implemented and tested: author post management, editor review and
controlled publishing, anonymous published listing, authorization
enforcement (103 tests passing).

Not yet implemented: the contract-defined `POST /api/auth/login` and
`POST /api/auth/logout` routes — authenticated flows are currently covered
by the test suite only.
