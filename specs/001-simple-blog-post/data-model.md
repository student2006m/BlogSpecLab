# Data Model: Simple Blog Post Management and Controlled Publishing

**Feature**: `001-simple-blog-post` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

Technology-agnostic definitions; storage mapping notes reference research D1 (SQLite via stdlib) without selecting an ORM.

## Entities

### Post

| Field | Type | Rules |
|---|---|---|
| `id` | integer, surrogate | Unique, immutable, assigned at creation |
| `owner_id` | User reference | Immutable; set at creation (`FR-002`) |
| `title` | text | MUST be non-empty after trimming; no max length in v1 (`FR-013`) |
| `content` | text | MUST be non-empty after trimming; no max length in v1 (`FR-013`) |
| `state` | enum | One of `draft`, `pending_review`, `published`; see transitions |
| `created_at` / `updated_at` | timestamp | Set/maintained by the system, never by the caller |
| `history` | list of Decision records | Append-only; every review/publish/edit-by-editor/unpublish action recorded |

### User

| Field | Type | Rules |
|---|---|---|
| `id` | integer, surrogate | Unique, immutable |
| `username` | text | Unique, non-empty; v1 accounts are pre-seeded (`FR-015`) |
| `password_hash` | text | `pbkdf2_hmac` hash + salt; never exposed, never logged (research D2) |
| `roles` | set of `author` / `editor` | MAY hold both; MUST NOT approve/publish own post (`FR-008`, `FR-015`) |

### Decision record (history entry)

| Field | Type | Rules |
|---|---|---|
| `post_id` | Post reference | Immutable |
| `actor_id` | User reference | The editor/author performing the transition |
| `action` | enum | `submit`, `approve_publish`, `reject`, `editor_edit`, `unpublish` |
| `reason` | text \| null | Mandatory for `reject` and `unpublish`; optional otherwise |
| `at` | timestamp | System-assigned |

## State transitions

```text
draft ──submit (owner)──▶ pending_review ──approve (different editor)──▶ published
  ▲                          │                                              │
  │                          │ reject (editor, reason!)                      │ unpublish (editor, reason!)
  │                          ▼                                              ▼
  └────────────── draft ◀───────────────────────────────────────────────────┘
```

Additional rules:
- `draft → published` directly is impossible (`FR-010`).
- Author edit/delete allowed only in `draft` (`FR-004`, `FR-005`); published posts are locked (`FR-004`).
- Editor content edits allowed only in `pending_review` and never on own posts (`FR-008c`).
- Concurrent conflicting transitions: first committed wins; the loser is rejected against the new state.

## Invariants (enforced in Domain/Application, never in endpoints)

1. Every post has exactly one owner; ownership never changes.
2. `published` is reachable only from `pending_review` via a different editor's approval.
3. `reject`/`unpublish` always carry a non-empty reason.
4. History is append-only and records actor + action + timestamp for every transition and editor edit.
