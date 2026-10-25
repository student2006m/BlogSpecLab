# Implementation Plan: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Date**: 2026-10-25
**Input**: [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api.md](contracts/api.md)

## Tech context

- Python 3.12+, Flask; pytest. No new pip dependencies (see research D1):
  the language-model adapter uses the standard library (`urllib.request`,
  `json`) against an OpenAI-compatible chat completions endpoint.
- Constitution `infra/ai` package becomes real with this feature: it holds
  the provider adapter only.

## Architecture

New module flow for `POST /api/posts/<id>/review-assist`:

```text
endpoints.api.assist          thin HTTP: auth context, error mapping, 200 render
  → core.application.review_assist   use case: author role, ownership,
                                     draft-state guard; validation of the
                                     provider record; builds domain records
      → core.domain.review_assist    ReviewAssessment/ReviewIssue value
                                     objects (schema-validating constructors)
      → ReviewAssistProvider port    contract for the language-model call
          → infra.ai.providers        HTTP adapter (OpenAI-compatible,
                                     stdlib urllib); untrusted output parsed
                                     then re-validated by the application
   → infra.data_access               post read-only via SQLitePostRepository
```

- No business logic in `endpoints`/`infra`; the adapter performs transport
  and raw parsing only, semantic/schema validation stays in Domain/Application.
- Advisory-only guarantee (FR-005): the use case performs no writes — no
  `update_post`, no `append_decision`. State invariance is asserted in tests.

## Structure of changes

```text
src/blogspeclab/core/domain/review_assist.py        NEW value objects + validation
src/blogspeclab/core/application/ports.py           + ReviewAssistProvider port
src/blogspeclab/core/application/review_assist.py   NEW use case + error classes
src/blogspeclab/infra/ai/__init__.py                NEW package marker
src/blogspeclab/infra/ai/providers.py               NEW HTTP provider adapter
src/blogspeclab/endpoints/api/assist.py             NEW thin route module
src/blogspeclab/endpoints/api/errors.py             + ReviewAssistUnavailableError (503)
src/blogspeclab/endpoints/api/app.py                + provider composition (env-based)
tests/unit/test_review_assist.py                    NEW domain tests
tests/application/test_review_assist.py             NEW use case tests (fakes)
tests/unit/test_review_providers.py                 NEW adapter tests (injected transport)
tests/http/test_review_assist.py                    NEW HTTP contract tests
```

## Configuration (environment only; never committed)

- `BLOGSPECLAB_REVIEW_ASSIST_BASE_URL` — OpenAI-compatible base URL.
- `BLOGSPECLAB_REVIEW_ASSIST_API_KEY` — bearer key; never logged.
- `BLOGSPECLAB_REVIEW_ASSIST_MODEL` — model identifier.
- `BLOGSPECLAB_REVIEW_ASSIST_TIMEOUT_SECONDS` — optional, default `30`.

If any required variable is missing, the app still starts (this feature is
optional) and the endpoint answers `503 REVIEW_ASSIST_UNAVAILABLE`.

## Risks / mitigations

- Language-model output untrusted → strict schema validation in Application,
  rebuild via Domain constructors; invalid → `503` (never rendered raw).
- Concrete provider schema ignored / unavailable → JSON-mode structured
  output is requested and re-validated; `ProviderError` mapping kept at one place.
- Secret leakage → key lives in env; adapter logs nothing; problem bodies carry no internals.
