"""Smart review assist use cases (no Flask, no HTTP, no sqlite3).

Advisory-only, feature `002-review-assist`: reviews an OWN draft post and
never performs a write (no post update, no decision history). Role,
ownership, and state checks run here against the server-side actor record.
The provider record is untrusted; schema validation happens in `core.domain`
and any unusable review reduces to `ReviewUnavailableError` (HTTP 503) —
the system never guesses.
"""

from __future__ import annotations

from typing import Any

from blogspeclab.core.application import ports
from blogspeclab.core.application.author_posts import (
    ApplicationError,
    ForbiddenError,
    NotFoundError,
)
from blogspeclab.core.domain.post import DRAFT, ValidationError
from blogspeclab.core.domain.review_assist import ReviewAssessment
from blogspeclab.core.domain.user import AUTHOR, parse_roles


class ProviderError(ApplicationError):
    """Review provider transport/parse failure (raised by `infra.ai`)."""


class ReviewUnavailableError(ApplicationError):
    """The smart review cannot be performed reliably → HTTP 503."""


def request_review_assist(
    repo: ports.PostRepository,
    actor: dict[str, Any],
    provider: ports.ReviewAssistProvider,
    post_id: int,
) -> dict[str, Any]:
    """Run an advisory-only smart review of an owned draft post.

    Returns `{post_id, state, assessment}`; performs no writes.
    """
    if AUTHOR not in parse_roles(actor.get("roles", "")):
        raise ForbiddenError("The author role is required.")
    row = repo.get_post(post_id)
    if row is None or row["owner_id"] != actor["id"]:
        raise NotFoundError(f"Post {post_id} was not found.")
    if row["state"] != DRAFT:
        # State guard on the caller's own post, consistent with 001 (403).
        raise ForbiddenError(
            "The smart review is available for draft posts only."
        )
    try:
        raw_record = provider.review_post(row["title"], row["content"])
        assessment = ReviewAssessment.from_dict(raw_record)
    except (ProviderError, ValidationError) as exc:
        raise ReviewUnavailableError(
            "The smart review service is not available right now."
        ) from exc
    except Exception as exc:  # FR-007: any provider breakdown degrades to 503
        raise ReviewUnavailableError(
            "The smart review service is not available right now."
        ) from exc

    return {
        "post_id": row["id"],
        "state": row["state"],
        "assessment": assessment.to_dict(),
    }
