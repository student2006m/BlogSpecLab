# Implementation Plan: Simple Blog Post Management and Controlled Publishing

**Branch**: `001-simple-blog-post` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-simple-blog-post/spec.md`

## Summary

Authors manage their own draft posts; editors review a cross-ownership queue, optionally revise, then approve/publish or reject/unpublish with mandatory reasons. Approach: Flask HTTP layer over `Application` use cases enforcing ownership, roles, and separation of duties on the trusted path; SQLite persistence via stdlib `sqlite3` behind Repository ports (no ORM); `pytest` coverage of Domain rules, use cases, and HTTP contracts. Details in [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md).

## Technical Context

**Language/Version**: Python 3.12+ (per Constitution).

**Primary Dependencies**: `Flask` (runtime); `pytest` (dev). Nothing else — see research D4/D5.

**Storage**: SQLite via stdlib `sqlite3`, hand-written SQL in `infra.data_access`, no ORM (research D1; FR-016).

**Testing**: `pytest`: Domain/Application tests dependency-free; repository tests on temp SQLite; HTTP tests via Flask test client; `ast`-based import-rule test (research D4/D6).

**Target Platform**: Local/dev server, single integrated deployment (per Spec assumptions).

**Project Type**: Web service (single Flask application, non-modular per Constitution §II).

**Performance Goals**: N/A for educational v1 — correctness and authorization enforcement first; no Spec targets.

**Constraints**: MUST run without LLM/MCP/Agent/vector dependencies (Constitution §V); secrets only via environment; English docs.

**Scale/Scope**: Single deployment, pre-seeded demo accounts, minimal post model (Spec assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Spec-driven | Plan derives from approved `spec.md`; no behavior beyond the Spec | ✅ Pass |
| II. Architecture | Constitution layout reused; `infra/ai`, `infra/qdrant` NOT created; no new packages beyond `data_access`; Blueprint use stays inside `endpoints.api` | ✅ Pass |
| II. Imports | Domain imports nothing; Application ← Domain only; `infra` ← Application/Domain; `endpoints` composes; verified by planned `ast` test (D6) | ✅ Pass |
| III. Security | Invariants + role/ownership checks in Domain/Application; HTTP/CLI input untrusted; no self-approval; secrets via environment | ✅ Pass |
| IV. Quality | pytest plan covers Domain rules, use cases, unauthorized/boundary cases; Flask-free Domain tests; type hints on layer boundaries | ✅ Pass |
| V. Simplicity | No ORM, no new tools, no AI stack; v1 runs standalone; research defers all non-required choices | ✅ Pass |
| VI. Governance | No Constitution change; global-flavored decisions (D1, D3–D6) stay **candidates** pending human review | ✅ Pass |

## Project Structure

### Documentation (this feature)

```text
specs/001-simple-blog-post/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

Per Constitution §II (no re-decision; `infra/ai`, `infra/qdrant` omitted until a real need):

```text
BlogSpecLab/
├── pyproject.toml
├── src/
│   └── blogspeclab/
│       ├── core/
│       │   ├── domain/        # Post, User, Decision, state machine, invariants
│       │   └── application/   # Use cases + ports (PostRepository, UserStore, Hasher, Clock)
│       ├── infra/
│       │   └── data_access/   # SQLite repositories, seeded demo users
│       └── endpoints/
│           └── api/           # Flask app factory, routes, JSON mapping, status codes, composition
├── tests/
│   ├── unit/            # Domain rules, state machine, validation
│   ├── application/     # Use cases incl. unauthorized/self-approval/boundary cases
│   ├── architecture/    # ast-based import-rule test
│   └── http/            # Contract tests per contracts/api.md
└── .specify/
```

**Structure Decision**: The Constitution's target structure, minus AI/Qdrant packages (created only on real need).

## Complexity Tracking

> No Constitution violations — table intentionally empty.
