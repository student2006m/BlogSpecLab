# Specification: Smart Review Assist for Posts

**Feature ID**: `002-review-assist` | **Date**: 2026-10-25 | **Mode**: Default (full SDD cycle, no stops)
**Status**: Approved (requirements provided by the user in this run)

## Overview

Before submitting a post to an editor, the author can ask the system for a
smart, AI-assisted review of the post content. The system reports likely
problems with the text as a structured, machine-processable result. The check
is strictly advisory: it never changes the post, never approves it, and never
publishes it.

## User Stories

### US1 — Request a smart review of a draft post (P1, MVP)

As the **author** of a **draft** post, I can request an automated content
review of my post, so that I can fix likely problems before submitting it for
editorial review.

**Requirements:**

- FR-001: The system exposes an authenticated operation by which the author
  requests a smart review for one of their own posts in `draft` state.
- FR-002: The result reports potential problems with the text as a list of
  issues, each with a severity, a category, a textual excerpt, and an
  explanation, and a short overall summary.
- FR-003: The result MUST be structured data (machine-processable and
  renderable by software), not free-form prose.
- FR-004: When there is not enough information to perform a meaningful
  review, the system MUST return an explicit "needs more information" result
  naming what is missing; it MUST NOT guess or fabricate findings.
- FR-005: The smart review is advisory-only: it MUST NOT modify post content,
  MUST NOT change the post state, MUST NOT approve/publish, and MUST NOT
  append decision history entries.
- FR-006: Authorization follows feature `001-simple-blog-post` semantics:
  owner-only access (other users' or missing posts → `404`), own-post state
  violations (`draft` required) and missing `author` role → `403`,
  unauthenticated → `401`.
- FR-007: When the review engine is not configured, unreachable, or its raw
  output is unusable, the system MUST NOT guess: it answers with
  `application/problem+json` (`503`, stable code) and leaves the post
  untouched.
- FR-008: Provider configuration (endpoint, API key, model) comes exclusively
  from environment variables; no secrets in code, docs, or logs.
- FR-009: Language-model output is untrusted: it MUST be validated against
  the result schema in Domain/Application before it reaches HTTP; only
  schema-valid output is returned.

### Out of scope

- Changing the submit/review/publish workflow from `001-simple-blog-post`.
- Model/Agent/Tool-calling capabilities; RAG, MCP, Qdrant (Constitution: added only in response to approved requirements).
- Storing or persisting review results (results are returned, not stored).
- Browser/UI rendering of results.

## Success Criteria

- SC-001: The author receives `200` with a schema-valid assessment (summary,
  issues) for an owned draft post, and the behavioral shape is covered by
  automated tests.
- SC-002: Requests for a missing post or another user's post return `404`
  (identical to `POST_NOT_FOUND`) — 100% of tested trials.
- SC-003: Any request against a post not in `draft` (own or otherwise),
  or by a caller without the `author` role, returns `403` — 100% of tested trials.
- SC-004: Unauthenticated requests return `401` — 100% of tested trials.
- SC-005: A successful or failed review request leaves post state, content,
  and decision history unchanged (verified in tests).
- SC-006: When the underlying review cannot be performed reliably, the
  response is either an explicit structured "needs more information" result
  or a `503` problem — never fabricated findings (verified with tests for the
  configured/broken-provider/unparseable-output cases).

Criteria stated as "100% of trials" are verified deterministically over the
defined test scenarios; they are not a substitute for ongoing human
acceptance.
