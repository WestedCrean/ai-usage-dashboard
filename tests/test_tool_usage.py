"""Tests for tool usage provider configuration checks."""

import pytest

from app.providers.tool_usage import (
    ClaudeCodeProvider,
    CodexProvider,
    GeminiCLIProvider,
    MistralVibeProvider,
)


class FakeSettings:
    openai_api_key = None
    anthropic_api_key = None
    gemini_api_key = None
    mistral_api_key = None
    enable_experimental = False
    claude_code_session = None
    claude_code_org_id = None
    mistral_vibe_session = None


def test_codex_configured_when_openai_key_present(monkeypatch):
    settings = FakeSettings()
    settings.openai_api_key = "sk-test"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = CodexProvider()
    assert provider.configured is True


def test_codex_not_configured_without_key(monkeypatch):
    settings = FakeSettings()
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = CodexProvider()
    assert provider.configured is False


def test_claude_code_configured_with_anthropic_key(monkeypatch):
    settings = FakeSettings()
    settings.anthropic_api_key = "sk-ant-test"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = ClaudeCodeProvider()
    assert provider.configured is True


def test_claude_code_configured_with_experimental_session(monkeypatch):
    settings = FakeSettings()
    settings.enable_experimental = True
    settings.claude_code_session = "session-value"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = ClaudeCodeProvider()
    assert provider.configured is True


def test_claude_code_not_configured_without_anything(monkeypatch):
    settings = FakeSettings()
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = ClaudeCodeProvider()
    assert provider.configured is False


def test_gemini_cli_configured_with_key(monkeypatch):
    settings = FakeSettings()
    settings.gemini_api_key = "AIzaSy-test"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = GeminiCLIProvider()
    assert provider.configured is True


def test_mistral_vibe_configured_with_api_key(monkeypatch):
    settings = FakeSettings()
    settings.mistral_api_key = "key-test"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = MistralVibeProvider()
    assert provider.configured is True


def test_mistral_vibe_configured_with_experimental_session(monkeypatch):
    settings = FakeSettings()
    settings.enable_experimental = True
    settings.mistral_vibe_session = "cookie=value"
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = MistralVibeProvider()
    assert provider.configured is True


def test_mistral_vibe_not_configured_without_anything(monkeypatch):
    settings = FakeSettings()
    monkeypatch.setattr("app.providers.tool_usage.get_settings", lambda: settings)
    provider = MistralVibeProvider()
    assert provider.configured is False
