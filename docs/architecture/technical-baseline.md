# BlogSpecLab Technical Baseline

**Status**: Approved | **Date**: 2026-10-13 | **Authority**: Subordinate to the Constitution — in case of conflict, `.specify/memory/constitution.md` prevails.

## 1. Purpose and Scope

This document records ONLY technical decisions that hold for the whole `BlogSpecLab` repository or are accepted as project architecture defaults from this point on. It MUST NOT turn temporary, experimental, or single-feature decisions into global ones. Feature designs MUST comply with it and MUST NOT re-decide or silently replace what is recorded here; changing it requires a documented architecture decision.

## 2. Platform

- Primary language: `Python`.
- Target version: `Python 3.12` or newer.
- Primary web framework: `Flask`.

## 3. Architecture

- Package structure and dependency (`Import`) direction follow the Constitution; `core.domain` stays independent of infrastructure and of `Flask`.
- `core.application` owns use-case orchestration and use-case permission checks.
- `infra` implements external dependencies behind ports defined by `Application`.
- Flask routes and view functions in `endpoints.api` MUST NOT hold business logic.
- Dependency composition happens in the `Application Factory` in `endpoints.api`.

## 4. Persistence

- Relational persistence for the project uses `SQLAlchemy`.
- The global database provider is NOT finalized yet.
- SQLite is only the current local/educational choice of the first feature and is NOT the project database baseline.
- Approved exception: the first feature (`001-simple-blog-post`) uses SQLite via stdlib `sqlite3` with hand-written SQL and no ORM (research D1); this exception does not change the project direction above.
- ORM details, mapped classes, and sessions MUST NOT leak into `Domain`.

## 5. Security

- Authentication and authorization are separate responsibilities.
- Identifying the user alone does NOT authorize an operation.
- The effective permission MUST be checked against a trusted server-side source during sensitive operations.
- Client claims, tokens, or raw `HTTP` input alone are NOT the source of truth for permissions.

## 6. HTTP Contracts

- `HTTP` errors use Problem Details (`application/problem+json`, RFC 9457).
- Client-actionable errors carry a stable `code`.
- Internals, stack traces, credentials, and sensitive data MUST NOT be exposed in error responses.
- Error handling is centralized (e.g. Flask error handlers), never repeated per endpoint.

## 7. Testing

- Primary test framework: `pytest`.
- `HTTP` integration tests use `create_app` and Flask's built-in test client (`app.test_client()`).
- `Domain` and `Application` rules MUST be testable without unnecessary external services and without starting Flask.
- Real integrations are verified at the appropriate level with a real or near-real provider.

## 8. Concurrency and Transactions

- Use cases whose execution on stale state could produce an incorrect business outcome MUST have explicit concurrency control.
- The exact mechanism MAY be chosen per aggregate, persistence provider, and external contract.
- A `Version` column or `ETag` is NOT a mandatory rule for all future entities.
- State changes that form one business operation MUST commit atomically within an appropriate transaction boundary.

## 9. Still Open

- Final database provider: NOT selected.
- Final authentication provider: NOT selected.
- Global endpoint style (e.g. plain view functions vs. class-based views): NOT finalized.
- Model provider and embedding model: decided when AI/RAG work starts.

## 10. Changing This Baseline

- Propose the change with rationale, affected specs/plans/code/tests, and alternatives considered.
- Record version, date, and change summary in this file.
- A change that contradicts the Constitution requires resolving the conflict first.
