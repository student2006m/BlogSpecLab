# HTTP API Contract: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

Conventions as in `001-simple-blog-post/contracts/api.md` (session cookie,
`application/problem+json` failures with stable `code`).

## Smart review of a draft post

| Method & Path | Auth | Request | Success | Failures |
|---|---|---|---|---|
| `POST /api/posts/<id>/review-assist` | author, owner, `draft` only | — (empty body) | `200 {post_id, state, assessment}` | `401` unauthenticated; `404` missing or not owned; `403` non-author role or own post not in `draft`; `503` review engine unconfigured/unreachable/output unusable |

Success body (`assessment` is schema-valid; machine-processable, FR-003):

```json
{
  "post_id": 7,
  "state": "draft",
  "assessment": {
    "summary": "Short overall summary of likely problems.",
    "issues": [
      {"severity": "major", "category": "clarity",
       "excerpt": "...", "explanation": "..."}
    ],
    "needs_more_information": false,
    "missing_information": []
  }
}
```

Insufficient-information outcome (FR-004, still `200` — no guessing):

```json
{
  "post_id": 7,
  "state": "draft",
  "assessment": {
    "summary": "",
    "issues": [],
    "needs_more_information": true,
    "missing_information": ["The post content is too short to review."]
  }
}
```

`503` problem body (FR-007; e.g. engine not configured, transport failure,
or schema-invalid model output):

```json
{
  "type": "about:blank",
  "title": "Review Assist Unavailable",
  "status": 503,
  "code": "REVIEW_ASSIST_UNAVAILABLE",
  "detail": "The smart review service is not available right now."
}
```

Stability guarantees: every success or failure leaves the post row
(state, content, timestamps) and decision history unchanged (FR-005).
No response body includes provider internals, API keys, or raw model output.
