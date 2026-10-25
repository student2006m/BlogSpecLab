"""Review provider adapter for `infra.ai` (feature `002-review-assist`).

Transport-only adapter for an OpenAI-compatible `/chat/completions`
endpoint using the standard library (`urllib.request`, `json`): builds the
request, calls the API, and parses the JSON envelope. No business rules
live here; the returned record is UNTRUSTED and is re-validated in
`core.domain` / `core.application`. Configuration values, including the API
key, come from the environment and are never logged, echoed, or persisted.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from blogspeclab.core.application.review_assist import ProviderError

SYSTEM_PROMPT = (
    "You are a writing assistant helping an author improve a blog post"
    " draft before it is submitted for editorial review. Review ONLY the"
    " given title and content; do not rewrite the text. Return ONLY a JSON"
    ' object with keys: {"summary": string, "issues": [{"severity":'
    ' "minor"|"major"|"critical", "category": string, "excerpt": string,'
    ' "explanation": string}], "needs_more_information": boolean,'
    ' "missing_information": [string]}. When the text is too short or too'
    " ambiguous to review meaningfully, set needs_more_information to true,"
    " list what information is missing, and report NO issues; never invent"
    " findings. Answer in the language of the reviewed text."
)


def chat_completions_url(base_url: str) -> str:
    """Build the chat completions endpoint URL from a base URL."""
    return base_url.rstrip("/") + "/chat/completions"


def build_request(
    base_url: str,
    api_key: str,
    model: str,
    title: str,
    content: str,
) -> urllib.request.Request:
    """Build one structured chat completions request (JSON mode)."""
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"title": title, "content": content},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(
        chat_completions_url(base_url),
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )


def _extract_record(envelope: Any) -> dict[str, Any]:
    """Extract the model's JSON record from the response envelope."""
    try:
        content = envelope["choices"][0]["message"]["content"]
        record = json.loads(content)
    except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
        raise ProviderError("Unusable provider response.") from exc
    if not isinstance(record, dict):
        raise ProviderError("Unusable provider response.")
    return record


class OpenAICompatibleReviewProvider:
    """`ReviewAssistProvider` over an OpenAI-compatible HTTP API."""

    def __init__(
        self, base_url: str, api_key: str, model: str, timeout: float = 30.0
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def review_post(self, title: str, content: str) -> dict[str, Any]:
        """Return the parsed model record; raises ProviderError on failure."""
        request = build_request(
            self._base_url, self._api_key, self._model, title, content
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except ValueError as exc:  # json.JSONDecodeError subclasses ValueError
            raise ProviderError("Unusable provider response.") from exc
        except Exception as exc:  # network, HTTP status, decode failures
            raise ProviderError("The review provider call failed.") from exc
        return _extract_record(envelope)
