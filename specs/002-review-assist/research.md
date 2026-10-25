# Research: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Date**: 2026-10-25

Decisions (user accepted Default Mode: decisions are documented here instead
of interactive clarification; each is aligned with the Constitution).

## D1 — Provider integration: OpenAI-compatible HTTP, stdlib only

- **Decision**: call an OpenAI-compatible `/chat/completions` endpoint with
  JSON-mode structured output using `urllib.request` + `json` from the
  standard library. No new pip dependency.
- **Rationale**: Constitution §V (no new SDK/framework without a real need;
  avoid dependency-management churn), the feature defines the behavior, not a
  specific vendor. An OpenAI-compatible surface is the most portable contract.
- **Consequences**: production needs `BLOGSPECLAB_REVIEW_ASSIST_*` env
  settings; tests inject a transport callable instead of a network.

## D2 — Port and error surface

- The port `ReviewAssistProvider` lives in `core/application/ports.py`:
  `review_post(title, content) -> dict` (raw but parsed JSON record).
- The adapter raises `infra.ai.providers.ProviderError` (subclass of
  `ApplicationError` in `core.application.review_assist`) for transport
  failures; the application maps any unusable result (transport error or
  schema-invalid record) to `ReviewUnavailableError` → HTTP `503`.
- "Not enough information" is a *valid structured outcome* (FR-004), not an
  error: unchanged `200` with `needs_more_information: true`.

## D3 — Scope of the review call

- Author role required; owner-only (non-owner/missing → `404 POST_NOT_FOUND`,
  same as `_owned_or_not_found` in `001`); own post in `draft` only → else
  `403` (state violation on own post; role violation) — matches FR-014
  semantics of `001` and the amended clarification (403, not 422).
- The prompt context sent to the provider is title + content only; no user
  secrets, no other users' data.

## D4 — Advisory-only enforcement in Application

- The use case must not write. No repository mutation calls exist in
  `review_assist.py`; tests assert row equality before/after (SC-005).
  Domain `Post` transition methods are not used at all in this feature.

## D5 — Composition

- `create_app` builds the provider only when all required env settings are
  present; otherwise registers `None` and the route answers `503`. The app
  MUST start without the review engine (Constitution §V: system runs
  without AI dependence). Tests inject a provider object via the
  `REVIEW_ASSIST_PROVIDER` config key (composition seam, endpoints layer).

## D6 — Model result schema (contract with the provider)

Requested from the model as JSON object:

```json
{
  "summary": "string, <= 500 chars",
  "issues": [
    {"severity": "minor|major|critical",
     "category": "string, short",
     "excerpt": "string from the text or empty",
     "explanation": "string"}
  ],
  "needs_more_information": false,
  "missing_information": ["string"]
}
```

Untrusted evaluation: rebuilt through `ReviewAssessment`/`ReviewIssue`
constructors in `core.domain.review_assist`; schema-invalid output reduces
to `503`, never silently guessed around (FR-009).
