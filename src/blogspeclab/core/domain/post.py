"""Post entity and lifecycle rules (domain only).

Independent of Flask, `sqlite3`, and HTTP. Review/approval/publishing
*behavior* belongs to User Story 2; only the minimal state structure needed
for US1 (draft lifecycle + submit) lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DRAFT = "draft"
PENDING_REVIEW = "pending_review"
PUBLISHED = "published"

ALLOWED_STATES = frozenset({DRAFT, PENDING_REVIEW, PUBLISHED})


class DomainError(Exception):
    """Base for domain rule violations (HTTP-independent)."""


class ValidationError(DomainError):
    """Raised when a value violates a domain invariant."""


class StateError(DomainError):
    """Raised when an operation is invalid in the current state."""


def _require_non_empty(name: str, value: str) -> str:
    cleaned = value.strip() if isinstance(value, str) else ""
    if not cleaned:
        raise ValidationError(f"{name} MUST be non-empty.")
    return value


@dataclass
class Post:
    """A blog post with immutable ownership and a guarded lifecycle."""

    id: int | None
    owner_id: int
    title: str
    content: str
    state: str = DRAFT
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if self.state not in ALLOWED_STATES:
            raise ValidationError(f"Unknown state: {self.state!r}.")
        self.title = _require_non_empty("title", self.title)
        self.content = _require_non_empty("content", self.content)

    @classmethod
    def create(
        cls, owner_id: int, title: str, content: str, now: str
    ) -> Post:
        """Create a new draft post owned by `owner_id`."""
        return cls(
            id=None,
            owner_id=owner_id,
            title=title,
            content=content,
            state=DRAFT,
            created_at=now,
            updated_at=now,
        )

    def revise(self, title: str, content: str, now: str) -> None:
        """Edit title/content. Draft only; ownership never changes."""
        self._require_state(DRAFT, "revise")
        self.title = _require_non_empty("title", title)
        self.content = _require_non_empty("content", content)
        self.updated_at = now

    def submit(self, now: str) -> None:
        """Move a draft post to pending review."""
        self._require_state(DRAFT, "submit")
        self.state = PENDING_REVIEW
        self.updated_at = now

    def ensure_deletable(self) -> None:
        """Guard author deletion: draft only."""
        self._require_state(DRAFT, "delete")

    def revise_by_editor(
        self, editor_id: int, title: str, content: str, now: str
    ) -> None:
        """Editor revision of a pending post. Never the owner's own post."""
        self._require_state(PENDING_REVIEW, "revise")
        self._reject_self_approval(editor_id, "revise")
        self.title = _require_non_empty("title", title)
        self.content = _require_non_empty("content", content)
        self.updated_at = now

    def approve(self, approver_id: int, now: str) -> None:
        """Approve a pending post: moves directly to published.

        Approve and publish are one operation, never two separate steps.
        Self-approval is rejected here and again in Application.
        """
        self._require_state(PENDING_REVIEW, "approve")
        self._reject_self_approval(approver_id, "approve")
        self.state = PUBLISHED
        self.updated_at = now

    def reject(self, reason: str, now: str) -> None:
        """Reject a pending post back to draft. Reason is mandatory."""
        self._require_state(PENDING_REVIEW, "reject")
        _require_non_empty("reason", reason)
        self.state = DRAFT
        self.updated_at = now

    def unpublish(self, reason: str, now: str) -> None:
        """Unpublish a published post back to draft. Reason is mandatory."""
        self._require_state(PUBLISHED, "unpublish")
        _require_non_empty("reason", reason)
        self.state = DRAFT
        self.updated_at = now

    def _reject_self_approval(self, actor_id: int, action: str) -> None:
        if actor_id == self.owner_id:
            raise StateError(
                f"Cannot {action} your own post: separation of duties."
            )

    def _require_state(self, expected: str, action: str) -> None:
        if self.state != expected:
            raise StateError(
                f"Cannot {action} a post in state {self.state!r};"
                f" required state is {expected!r}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Plain-data view for the application layer (no domain leakage)."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "content": self.content,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> Post:
        """Rebuild an entity from a persistence row (no validation skip)."""
        return cls(
            id=row["id"],
            owner_id=row["owner_id"],
            title=row["title"],
            content=row["content"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
