"""Tests for endpoint smoke test functionality."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest

from app.models import EndpointTestResult, TestStatus
from app.services.smoke_tests import (
    _get_official_endpoints,
    _get_experimental_endpoints,
    _get_skipped_providers,
)


class FakeSettings:
    """Minimal settings stub for smoke test registry functions."""
    openai_api_key = None
    anthropic_api_key = None
    gemini_api_key = None
    mistral_api_key = None
    openrouter_api_key = None
    openai_org_id = None
    enable_experimental = False
    claude_code_session = None
    claude_code_org_id = None
    mistral_vibe_session = None
    google_cloud_project = None


def test_no_keys_produces_no_official_endpoints():
    settings = FakeSettings()
    endpoints = _get_official_endpoints(settings)
    assert endpoints == []


def test_openai_key_produces_endpoints():
    settings = FakeSettings()
    settings.openai_api_key = "sk-test"
    endpoints = _get_official_endpoints(settings)
    assert len(endpoints) == 3
    assert all(e[0] == "openai" for e in endpoints)


def test_skipped_providers_for_unconfigured():
    settings = FakeSettings()
    skipped = _get_skipped_providers(settings)
    # All 5 API providers should be skipped
    assert len(skipped) == 5
    for r in skipped:
        assert r.test_status == TestStatus.SKIPPED
        assert r.ok is False
        assert "not configured" in r.notes.lower()


def test_skipped_excludes_configured():
    settings = FakeSettings()
    settings.openai_api_key = "sk-test"
    settings.anthropic_api_key = "sk-ant-test"
    skipped = _get_skipped_providers(settings)
    providers = {r.provider for r in skipped}
    assert "openai" not in providers
    assert "anthropic" not in providers
    assert "gemini" in providers
    assert "mistral" in providers
    assert "openrouter" in providers


def test_experimental_disabled_returns_empty():
    settings = FakeSettings()
    settings.enable_experimental = False
    settings.claude_code_session = "some-session"
    endpoints = _get_experimental_endpoints(settings)
    assert endpoints == []


def test_experimental_claude_code_with_org_id():
    settings = FakeSettings()
    settings.enable_experimental = True
    settings.claude_code_session = "some-session"
    settings.claude_code_org_id = "org-123"
    endpoints = _get_experimental_endpoints(settings)
    claude_endpoints = [e for e in endpoints if e[0] == "claude_code"]
    assert len(claude_endpoints) == 1
    assert "org-123" in claude_endpoints[0][1]
    assert claude_endpoints[0][3] is True  # is_experimental


def test_experimental_claude_code_without_org_id():
    settings = FakeSettings()
    settings.enable_experimental = True
    settings.claude_code_session = "some-session"
    settings.claude_code_org_id = None
    endpoints = _get_experimental_endpoints(settings)
    claude_endpoints = [e for e in endpoints if e[0] == "claude_code"]
    assert len(claude_endpoints) == 1
    assert "/api/organizations" in claude_endpoints[0][1]
    assert "org discovery" in claude_endpoints[0][4].lower()


def test_experimental_mistral_vibe():
    settings = FakeSettings()
    settings.enable_experimental = True
    settings.mistral_vibe_session = "cookie=value"
    endpoints = _get_experimental_endpoints(settings)
    vibe_endpoints = [e for e in endpoints if e[0] == "mistral_vibe"]
    assert len(vibe_endpoints) == 1
    assert "vibe-usage" in vibe_endpoints[0][1]
    assert vibe_endpoints[0][3] is True  # is_experimental


def test_test_status_enum_values():
    """Verify TestStatus enum has expected values."""
    assert TestStatus.PASS.value == "pass"
    assert TestStatus.FAIL.value == "fail"
    assert TestStatus.SKIPPED.value == "skipped"


def test_endpoint_test_result_default_status():
    """Default test_status should be FAIL."""
    r = EndpointTestResult(provider="test", endpoint="http://example.com")
    assert r.test_status == TestStatus.FAIL
    assert r.ok is False
