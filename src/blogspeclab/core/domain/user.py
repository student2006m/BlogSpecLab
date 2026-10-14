"""User entity and roles (domain only).

Independent of Flask, `sqlite3`, and HTTP. A user MAY hold both `author`
and `editor` roles; separation of duties is enforced by use cases, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

from blogspeclab.core.domain.post import DomainError, ValidationError

AUTHOR = "author"
EDITOR = "editor"

ALLOWED_ROLES = frozenset({AUTHOR, EDITOR})


def parse_roles(raw: str) -> frozenset[str]:
    """Parse a comma-separated role string into a validated role set."""
    roles = frozenset(
        role.strip() for role in raw.split(",") if role.strip()
    )
    unknown = roles - ALLOWED_ROLES
    if unknown:
        raise ValidationError(f"Unknown roles: {sorted(unknown)}.")
    return roles


@dataclass(frozen=True)
class User:
    """An authenticated actor with server-side roles."""

    id: int
    username: str
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        """Return True when the user holds `role`."""
        return role in self.roles

    @classmethod
    def from_dict(cls, row: dict) -> User:
        """Rebuild an entity from a persistence row."""
        return cls(
            id=row["id"],
            username=row["username"],
            roles=parse_roles(row["roles"]),
        )
