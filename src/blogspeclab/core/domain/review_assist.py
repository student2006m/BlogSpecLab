"""Smart review assist value objects (domain only).

Independent of Flask, `sqlite3`, and HTTP. These records represent the
structured result of an advisory-only, AI-assisted content review. The
constructors validate UNTRUSTED input: any schema violation raises
`ValidationError`, and the application MUST treat such a review as
unavailable instead of guessing (feature `002-review-assist`, FR-004/FR-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from blogspeclab.core.domain.post import ValidationError

SEVERITY_MINOR = "minor"
SEVERITY_MAJOR = "major"
SEVERITY_CRITICAL = "critical"

ALLOWED_SEVERITIES = frozenset(
    {SEVERITY_MINOR, SEVERITY_MAJOR, SEVERITY_CRITICAL}
)


def _require_str(name: str, value: Any, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} MUST be a string.")
    if not allow_empty and not value.strip():
        raise ValidationError(f"{name} MUST be non-empty.")
    return value


def _require_str_list(name: str, values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValidationError(f"{name} MUST be a list of strings.")
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"Every {name} item MUST be non-empty.")
    return list(values)


@dataclass
class ReviewIssue:
    """One potential problem reported by the smart review."""

    severity: str
    category: str
    excerpt: str
    explanation: str

    def __post_init__(self) -> None:
        if self.severity not in ALLOWED_SEVERITIES:
            raise ValidationError(f"Unknown severity: {self.severity!r}.")
        self.category = _require_str("category", self.category, allow_empty=False)
        self.excerpt = _require_str("excerpt", self.excerpt, allow_empty=True)
        self.explanation = _require_str(
            "explanation", self.explanation, allow_empty=False
        )

    @classmethod
    def from_dict(cls, raw: Any) -> ReviewIssue:
        """Validate untrusted input and build one issue record."""
        if not isinstance(raw, dict):
            raise ValidationError("An issue MUST be an object.")
        try:
            return cls(
                severity=raw["severity"],
                category=raw["category"],
                excerpt=raw["excerpt"],
                explanation=raw["explanation"],
            )
        except KeyError as exc:
            raise ValidationError(f"Missing issue field: {exc.args[0]!r}.") from exc
        except TypeError as exc:
            raise ValidationError("An issue MUST be an object.") from exc

    def to_dict(self) -> dict[str, Any]:
        """Plain-data view for the application layer."""
        return {
            "severity": self.severity,
            "category": self.category,
            "excerpt": self.excerpt,
            "explanation": self.explanation,
        }


@dataclass
class ReviewAssessment:
    """Structured smart review result.

    Exactly one outcome is valid: either a completed review (non-empty
    summary, no missing-information list) or an explicit request for more
    information (no summary, no issues, at least one missing item). The
    system never guesses.
    """

    summary: str
    issues: list[ReviewIssue]
    needs_more_information: bool = False
    missing_information: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.needs_more_information, bool):
            raise ValidationError(
                "needs_more_information MUST be a boolean."
            )
        if self.needs_more_information:
            if self.issues:
                raise ValidationError(
                    "issues MUST be empty when needs_more_information is True."
                )
            self.missing_information = _require_str_list(
                "missing_information", self.missing_information
            )
            if not self.missing_information:
                raise ValidationError(
                    "missing_information MUST be non-empty when"
                    " needs_more_information is True."
                )
            if isinstance(self.summary, str) and self.summary.strip():
                raise ValidationError(
                    "summary MUST be empty when needs_more_information is True."
                )
            _require_str("summary", self.summary, allow_empty=True)
        else:
            _require_str("summary", self.summary, allow_empty=False)
            if self.missing_information:
                raise ValidationError(
                    "missing_information MUST be empty when"
                    " needs_more_information is False."
                )
            for issue in self.issues:
                if not isinstance(issue, ReviewIssue):
                    raise ValidationError("Each issue MUST be a ReviewIssue.")

    @classmethod
    def from_dict(cls, raw: Any) -> ReviewAssessment:
        """Validate untrusted input and build the assessment record."""
        if not isinstance(raw, dict):
            raise ValidationError("An assessment MUST be an object.")
        try:
            issues_raw = raw["issues"]
        except KeyError as exc:
            raise ValidationError(f"Missing field: {exc.args[0]!r}.") from exc
        if not isinstance(issues_raw, list):
            raise ValidationError("issues MUST be a list.")
        issues = [ReviewIssue.from_dict(item) for item in issues_raw]
        try:
            return cls(
                summary=raw["summary"],
                issues=issues,
                needs_more_information=raw["needs_more_information"],
                missing_information=raw.get("missing_information", []),
            )
        except KeyError as exc:
            raise ValidationError(f"Missing field: {exc.args[0]!r}.") from exc
        except TypeError as exc:
            raise ValidationError("An assessment MUST be an object.") from exc

    def to_dict(self) -> dict[str, Any]:
        """Plain-data view for the application and HTTP layers."""
        return {
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "needs_more_information": self.needs_more_information,
            "missing_information": list(self.missing_information),
        }
