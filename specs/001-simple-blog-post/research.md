# Research: Simple Blog Post Management and Controlled Publishing

**Feature**: `001-simple-blog-post` | **Date**: 2026-10-13

**Scope rule applied**: Global decisions already recorded in the Constitution or repository docs are NOT re-decided here (monolith layout, package responsibilities, import rules, SDD workflow, English docs). Only new technical decisions required to design THIS feature are recorded below. Decisions marked **Technical Baseline candidate** are project-wide and stay candidates until human review records them in a global architecture document.

## D1. Operational storage for v1 — **Technical Baseline candidate**

**Decision**: SQLite accessed via Python stdlib `sqlite3`, with hand-written SQL confined to `infra.data_access` Repository implementations. No ORM.

**Rationale**: `FR-016` requires persistence across restarts; SQLite is file-based, zero-dependency, and sufficient for a single-deployment educational v1 with seeded accounts. Hand-written SQL keeps `core.domain`/`core.application` free of infrastructure and defers the ORM choice until a real need appears, per Constitution Principle V.

**Alternatives considered**:
- `SQLAlchemy` (or other ORM): rejected — new dependency and abstraction layer without an approved need; violates simplicity.
- JSON file store: rejected — no atomic writes, manual querying/filtering, corruption risk on concurrent access.
- In-memory store: rejected — violates `FR-016` (persistence across restarts).

## D2. Password hashing for seeded accounts

**Decision**: stdlib `hashlib.pbkdf2_hmac` (SHA-256, per-password salt, high iteration count) for verifying seeded demo credentials. No password storage in code or logs; seed credentials come from environment configuration.

**Rationale**: Secure password verification with zero new dependencies; matches the Constitution's secrets rule and simplicity principle.

**Alternatives considered**:
- `bcrypt` / `passlib`: rejected — new dependencies for a v1 with fixed demo accounts; re-evaluate if password policies grow.
- Plaintext comparison: rejected — unacceptable security posture.

## D3. Session mechanism

**Decision**: Flask's built-in signed-cookie sessions; the session carries only user id and roles. — **Technical Baseline candidate**

**Rationale**: Zero-dependency, sufficient for v1 seeded accounts on a single deployment; identity/roles are resolved into request context on the trusted path before reaching `Application` use cases.

**Alternatives considered**:
- Server-side sessions (`Flask-Session` + store): rejected — new dependency and storage need without an approved requirement (no scale/logout-revocation requirement in v1).

## D4. Test framework — **Technical Baseline candidate**

**Decision**: `pytest` (single dev-dependency). Domain/Application tests run without Flask or SQLite (fakes for ports); repository tests use a temporary SQLite file; HTTP tests use Flask's test client.

**Rationale**: De-facto Python standard with fixtures/parametrize; directly supports Constitution Principle IV (automated coverage of Domain rules, use cases, unauthorized access, boundaries).

**Alternatives considered**:
- stdlib `unittest`: rejected — weaker fixture/parametrize support; `pytest` is one justified dev-dependency serving the approved testing obligation.

## D5. Dependency and environment tooling — **Technical Baseline candidate**

**Decision**: `pyproject.toml` (PEP 621) + stdlib `venv` + `pip`. Runtime dependency: `Flask` only. Dev dependencies: `pytest` only.

**Rationale**: Minimal standard tooling; no new package manager without need, per Principle V.

**Alternatives considered**:
- `Poetry` / `uv` / `Pipenv`: rejected — new tools without an approved need.

## D6. Import-rule enforcement — **Technical Baseline candidate**

**Decision**: Automated architecture test in `tests/` using stdlib `ast` import parsing (no new tool), asserting the Constitution's import rules (§II.1–5, §II.9).

**Rationale**: Makes dependency rules verifiable as the Constitution requires, with zero new dependencies and no premature framework.

**Alternatives considered**:
- `import-linter` / `pytest-archon`: rejected for now — new dependencies; re-evaluate if the rule set outgrows the script.

## Non-decisions (explicitly deferred)

- ORM selection, language-model provider, embedding model, vector store: out of scope for this feature per Spec and Constitution; no research performed.
- Production hosting, backups, observability stack: no Spec requirement; deferred.
