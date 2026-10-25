"""Unit tests for the review provider adapter (T005).

Network-free: `urllib.request.urlopen` is replaced with a scripted fake.
The adapter is transport-only; every breakdown reduces to ProviderError.
Secrets are never logged or echoed in error messages.
"""

import json

import pytest

from blogspeclab.infra.ai import providers
from blogspeclab.infra.ai.providers import (
    OpenAICompatibleReviewProvider,
    chat_completions_url,
)

API_KEY = "test-only-key"  # unit-test fixture value, never a real secret

GOOD_ENVELOPE = {
    "choices": [
        {"message": {"content": json.dumps(
            {
                "summary": "Two issues found.",
                "issues": [],
                "needs_more_information": False,
                "missing_information": [],
            }
        )}}
    ]
}


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def make_provider() -> OpenAICompatibleReviewProvider:
    return OpenAICompatibleReviewProvider(
        base_url="https://llm.example/v1",
        api_key=API_KEY,
        model="test-model",
        timeout=0.1,
    )


def test_chat_completions_url_appends_endpoint():
    assert (
        chat_completions_url("https://llm.example/v1")
        == "https://llm.example/v1/chat/completions"
    )
    assert (
        chat_completions_url("https://llm.example/v1/")
        == "https://llm.example/v1/chat/completions"
    )


def test_build_request_contains_payload_and_auth_header():
    request = providers.build_request(
        base_url="https://llm.example/v1/",
        api_key=API_KEY,
        model="test-model",
        title="T",
        content="C",
    )
    assert request.get_method() == "POST"
    assert request.full_url == "https://llm.example/v1/chat/completions"
    assert request.get_header("Authorization") == f"Bearer {API_KEY}"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == "test-model"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0]["role"] == "system"
    assert "T" in payload["messages"][1]["content"]
    assert "C" in payload["messages"][1]["content"]


def test_review_post_returns_parsed_record(monkeypatch):
    seen = {}
    capture = GOOD_ENVELOPE

    def fake_urlopen(request, timeout=None):
        seen["timeout"] = timeout
        seen["url"] = request.full_url
        return FakeResponse(json.dumps(capture).encode("utf-8"))

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    record = make_provider().review_post("T", "C")
    assert record["summary"] == "Two issues found."
    assert "needs_more_information" in record
    assert seen["url"].endswith("/chat/completions")


def test_transport_failure_maps_to_provider_error(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(providers.ProviderError):
        make_provider().review_post("T", "C")


def test_non_json_body_maps_to_provider_error(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return FakeResponse(b"<html>not json</html>")

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(providers.ProviderError, match="Unusable"):
        make_provider().review_post("T", "C")


@pytest.mark.parametrize(
    "envelope",
    [
        {"error": {"message": "unauthorized"}},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": "[1, 2, 3]"}}]},
    ],
)
def test_unusable_envelopes_map_to_provider_error(envelope, monkeypatch):
    def fake_urlopen(request, timeout=None):
        return FakeResponse(json.dumps(envelope).encode("utf-8"))

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(providers.ProviderError, match="Unusable"):
        make_provider().review_post("T", "C")


def test_errors_never_contain_the_api_key(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise OSError("boom")

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(providers.ProviderError) as info:
        make_provider().review_post("T", "C")
    assert API_KEY not in str(info.value)
    assert API_KEY not in repr(info.value)
