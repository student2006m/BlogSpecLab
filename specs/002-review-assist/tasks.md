# Tasks: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Setup**: user selected Default Mode (full SDD cycle without stops)

- [X] T001 [P] Domain value object tests for `ReviewIssue`/`ReviewAssessment` schema validation in tests/unit/test_review_assist.py
- [X] T002 Implement `core/domain/review_assist.py` value objects (constructor validation for untrusted input)
- [X] T003 [P] Application use case tests with fake provider (role/ownership/draft guards, needs-info passthrough, provider failure mapping, no-write invariance) in tests/application/test_review_assist.py
- [X] T004 Implement `ReviewAssistProvider` port in `core/application/ports.py` and the use case `request_review_assist` in `core/application/review_assist.py`
- [X] T005 [P] Provider adapter tests with injected transport (request build, JSON parse, malformed/failed transport) in tests/unit/test_review_providers.py
- [X] T006 Implement `infra/ai` package: `providers.py` OpenAI-compatible HTTP adapter (stdlib urllib, env config, no logging of keys)
- [X] T007 [P] HTTP contract tests for `POST /api/posts/<id>/review-assist` (200/401/403/404/503, unchanged post) in tests/http/test_review_assist.py
- [X] T008 Implement `ReviewAssistUnavailableError` in `errors.py`, thin route module `assist.py`, provider composition in `app.py`
- [X] T009 Full pytest suite green on all features; validate `quickstart.md` live; write `quickstart.md` with only verified commands
