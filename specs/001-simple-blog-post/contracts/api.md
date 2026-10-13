# HTTP API Contract: Simple Blog Post Management and Controlled Publishing

**Feature**: `001-simple-blog-post` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

Conventions: JSON request/response bodies; session cookie for authenticated calls; status codes per `FR-014` (`404` for non-existent or other users' unpublished posts, `403` for own-post role violations, `401` for unauthenticated access to protected operations, `400` for validation failures). Anonymous access is allowed ONLY on the published endpoints.

## Auth

| Method & Path | Auth | Request | Success | Failures |
|---|---|---|---|---|
| `POST /api/auth/login` | — | `{username, password}` | `200 {id, username, roles}` + session | `401` bad credentials; `400` missing fields |
| `POST /api/auth/logout` | session | — | `200` | `401` |

## Author post management

| Method & Path | Auth | Request | Success | Failures |
|---|---|---|---|---|
| `POST /api/posts` | author | `{title, content}` | `201 Post` (`draft`, owner = caller) | `401`; `400` empty title/content |
| `GET /api/posts` | author | — | `200 [Post]` owned by caller only | `401` |
| `GET /api/posts/<id>` | owner | — | `200 Post` | `404` (missing OR owned by another user) |
| `PATCH /api/posts/<id>` | owner, `draft` only | `{title?, content?}` | `200 Post` | `404`; `400` empty values; `422` (or `403`) when not in `draft` |
| `DELETE /api/posts/<id>` | owner, `draft` only | — | `204` | `404`; `403` when in `pending_review`/`published` |
| `POST /api/posts/<id>/submit` | owner, `draft` only | — | `200 Post` (`pending_review`) | `404`; `403` when not in `draft` |

## Editor review and publishing

| Method & Path | Auth | Request | Success | Failures |
|---|---|---|---|---|
| `GET /api/review-queue` | editor | — | `200 [Post]` all `pending_review` | `401`; `403` non-editor |
| `PATCH /api/posts/<id>/revise` | editor, `pending_review`, not own | `{title?, content?}` | `200 Post` + history entry | `404`; `403` own post or wrong state; `400` empty values |
| `POST /api/posts/<id>/approve` | editor, `pending_review`, not own | — | `200 Post` (`published`) + history entry | `404`; `403` own post or wrong state |
| `POST /api/posts/<id>/reject` | editor, `pending_review` | `{reason!}` | `200 Post` (`draft`) + history entry | `404`; `400` missing reason |
| `POST /api/posts/<id>/unpublish` | editor, `published` | `{reason!}` | `200 Post` (`draft`, leaves public listing) | `404`; `400` missing reason |

## Public (anonymous allowed)

| Method & Path | Auth | Success | Failures |
|---|---|---|---|
| `GET /api/published` | — | `200 [Post]` all published | — |
| `GET /api/published/<id>` | — | `200 Post` if published | `404` otherwise |

## Error body

Content type `application/problem+json` (RFC 9457):

```json
{
  "type": "about:blank",
  "title": "<short human-readable summary>",
  "status": 404,
  "code": "<stable machine-readable code, e.g. POST_NOT_FOUND>",
  "detail": "<human-readable detail>"
}
```

`code` is stable per failure class. Neither status codes, `detail`, nor messages leak the existence of other users' unpublished posts, and no internals, stack traces, or credentials are exposed.
