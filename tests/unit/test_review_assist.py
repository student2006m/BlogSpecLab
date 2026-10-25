"""Domain tests for smart review assist value objects (T001).

Model output is UNTRUSTED: the constructors must validate schema and raise
ValidationError on any violation so the application can treat the review as
unavailable instead of guessing (FR-004, FR-009).
"""

import pytest

from blogspeclab.core.domain.post import ValidationError
from blogspeclab.core.domain.review_assist import (
    SEVERITY_MAJOR,
    ReviewAssessment,
    ReviewIssue,
)

GOOD_ISSUE = {
    "severity": "major",
    "category": "clarity",
    "excerpt": "some text",
    "explanation": "The sentence is ambiguous.",
}


@pytest.mark.parametrize("field", ["category", "explanation"])
def test_issue_rejects_empty_required_fields(field):
    raw = {**GOOD_ISSUE, field: "   "}
    with pytest.raises(ValidationError):
        ReviewIssue.from_dict(raw)


def test_issue_rejects_unknown_severity():
    with pytest.raises(ValidationError):
        ReviewIssue.from_dict({**GOOD_ISSUE, "severity": "huge"})


def test_issue_allows_empty_excerpt():
    issue = ReviewIssue.from_dict({**GOOD_ISSUE, "excerpt": ""})
    assert issue.excerpt == ""


def test_issue_from_dict_builds_typed_record():
    issue = ReviewIssue.from_dict(GOOD_ISSUE)
    assert issue.severity == SEVERITY_MAJOR == issue.to_dict()["severity"]
    assert issue.to_dict() == GOOD_ISSUE


@pytest.mark.parametrize("field", ["severity", "category", "excerpt", "explanation"])
def test_issue_from_dict_rejects_missing_or_non_string(field):
    raw = {k: v for k, v in GOOD_ISSUE.items() if k != field}
    with pytest.raises(ValidationError):
        ReviewIssue.from_dict(raw)
    with pytest.raises(ValidationError):
        ReviewIssue.from_dict({**GOOD_ISSUE, field: 123})


def test_issue_from_dict_rejects_non_dict():
    with pytest.raises(ValidationError):
        ReviewIssue.from_dict(["major"])


GOOD_ASSESSMENT = {
    "summary": "Two likely clarity problems found.",
    "issues": [GOOD_ISSUE],
    "needs_more_information": False,
    "missing_information": [],
}


def test_assessment_from_dict_builds_valid_record():
    assessment = ReviewAssessment.from_dict(GOOD_ASSESSMENT)
    assert len(assessment.issues) == 1
    assert isinstance(assessment.issues[0], ReviewIssue)
    assert assessment.to_dict() == GOOD_ASSESSMENT


def test_assessment_needs_more_information_requires_missing_list():
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict({**GOOD_ASSESSMENT, "needs_more_information": True})
    assessment = ReviewAssessment.from_dict(
        {
            "summary": "",
            "issues": [],
            "needs_more_information": True,
            "missing_information": ["Content is nearly empty."],
        }
    )
    assert assessment.needs_more_information is True


def test_assessment_needs_more_information_rejects_issues_and_summary():
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict(
            {
                "summary": "Some summary",
                "issues": [],
                "needs_more_information": True,
                "missing_information": ["More context required."],
            }
        )
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict(
            {
                "summary": "",
                "issues": [GOOD_ISSUE],
                "needs_more_information": True,
                "missing_information": ["More context required."],
            }
        )


def test_assessment_completed_review_rejects_empty_summary_and_missing():
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict({**GOOD_ASSESSMENT, "summary": "  "})
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict(
            {**GOOD_ASSESSMENT, "missing_information": ["unknown"]}
        )


def test_assessment_rejects_non_boolean_flag():
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict({**GOOD_ASSESSMENT, "needs_more_information": 1})
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict({**GOOD_ASSESSMENT, "needs_more_information": "no"})


def test_assessment_rejects_non_list_or_empty_missing_items():
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict(
            {
                "summary": "",
                "issues": [],
                "needs_more_information": True,
                "missing_information": "content",
            }
        )
    with pytest.raises(ValidationError):
        ReviewAssessment.from_dict(
            {
                "summary": "",
                "issues": [],
                "needs_more_information": True,
                "missing_information": ["  "],
            }
        )
