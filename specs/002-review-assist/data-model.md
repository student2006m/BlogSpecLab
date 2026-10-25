# Data Model: Smart Review Assist for Posts

**Feature**: `002-review-assist` | **Date**: 2026-10-25

No database schema changes (advisory-only feature; results are never
persisted — see FR-005/D4). Only new in-memory value objects.

## ReviewIssue (value object, `core.domain.review_assist`)

| Field        | Type | Rules |
|---|---|---|
| `severity`   | `str` | one of `minor` \| `major` \| `critical` |
| `category`   | `str` | non-empty after strip |
| `excerpt`    | `str` | may be empty; non-string → invalid |
| `explanation`| `str` | non-empty after strip |

## ReviewAssessment (value object, `core.domain.review_assist`)

| Field                      | Type | Rules |
|---|---|---|
| `summary`                  | `str` | non-empty when `needs_more_information` is `False`; empty string permitted (and unused) otherwise |
| `issues`                   | `list[ReviewIssue]` | MUST be empty when `needs_more_information` is `True` |
| `needs_more_information`   | `bool` | `True` ⇒ `missing_information` non-empty and `issues` empty |
| `missing_information`      | `list[str]` | each non-empty after strip; empty list permitted when the flag is `False` |

Constructors accept untrusted raw dictionaries and raise `ValidationError`
on any schema violation; valid ones build the typed record and `to_dict()`
returns the plain-data view used by endpoints.

## Existing entities

Unchanged: `Post`, `User`, decision rows, SQLite schema
(`001-simple-blog-post/data-model.md` remains authoritative).
