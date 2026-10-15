"""Unit security tests for User Story 3 (T028), no I/O beyond tmp files.

Covers password hashing properties, env-only secrets, fail-fast startup
without secret leakage, and a source scan proving no hardcoded credentials.
"""

import inspect
import os
from pathlib import Path

import pytest

from blogspeclab.endpoints.api.app import create_app
from blogspeclab.infra.data_access.repositories import Pbkdf2PasswordHasher


def _hasher():
    return Pbkdf2PasswordHasher(iterations=1000)


def test_correct_password_verifies_wrong_does_not():
    stored = _hasher().hash_password("s3cret")
    assert _hasher().verify("s3cret", stored)
    assert not _hasher().verify("S3CRET", stored)
    assert not _hasher().verify("", stored)


def test_hash_uses_unique_salts_and_hides_plaintext():
    password = "same-password"
    first, second = _hasher().hash_password(password), _hasher().hash_password(password)
    assert first != second
    assert password not in first and password not in second


def test_comparison_is_constant_time_and_malformed_is_false():
    assert "compare_digest" in inspect.getsource(
        Pbkdf2PasswordHasher.verify
    )
    assert _hasher().verify("x", "not-a-hash") is False
    assert _hasher().verify("x", "") is False


def test_no_hardcoded_secrets_in_source():
    root = Path(__file__).resolve().parents[2] / "src"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            stripped = line.split("#", 1)[0]
            lowered = stripped.lower()
            if (
                ("password" in lowered or "secret" in lowered)
                and "=" in stripped
                and ('"' in stripped or "'" in stripped)
                and "password_hash" not in lowered
                and "secret_key" not in lowered
                and "secretkey" not in lowered
                and '.get(' not in stripped
                and '["password"]' not in stripped
                and "['password']" not in stripped
            ):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert offenders == []


def test_secret_key_defaults_to_none_outside_testing(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = create_app({"DATABASE_PATH": ":memory:"})
    assert app.secret_key is None


def test_testing_keys_are_ephemeral_and_unique(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    first = create_app({"TESTING": True, "DATABASE_PATH": ":memory:"})
    second = create_app({"TESTING": True, "DATABASE_PATH": ":memory:"})
    assert first.secret_key and second.secret_key
    assert first.secret_key != second.secret_key


def test_missing_database_setting_fails_fast_without_leak(monkeypatch):
    monkeypatch.setenv("BLOGSPECLAB_SEED_USERS", "super-secret-value")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.delenv("BLOGSPECLAB_DATABASE_PATH", raising=False)
    with pytest.raises(ValueError) as excinfo:
        create_app({})
    message = str(excinfo.value)
    assert "DATABASE_PATH" in message
    assert "super-secret-value" not in message
