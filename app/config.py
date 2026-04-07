"""
Configuration — loaded from environment variables or .env file.
All API keys are optional; missing keys result in graceful empty states.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")

    # ── Database ─────────────────────────────────────────────────────────────
    db_path: str = Field(default="data/dashboard.db", alias="DB_PATH")

    # ── Refresh ───────────────────────────────────────────────────────────────
    # Interval in minutes between automatic background refreshes
    refresh_interval_minutes: int = Field(default=15, alias="REFRESH_INTERVAL_MINUTES")

    # ── Provider API keys (all optional) ──────────────────────────────────────
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    mistral_api_key: str | None = Field(default=None, alias="MISTRAL_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")

    # ── Optional org / project IDs ────────────────────────────────────────────
    openai_org_id: str | None = Field(default=None, alias="OPENAI_ORG_ID")
    openai_project_id: str | None = Field(default=None, alias="OPENAI_PROJECT_ID")

    # ── Experimental / reverse-engineered endpoints ───────────────────────────
    # Must be explicitly opted-in; never enabled by default.
    enable_experimental: bool = Field(default=False, alias="ENABLE_EXPERIMENTAL")

    # Claude Code session cookie (used only when ENABLE_EXPERIMENTAL=true)
    claude_code_session: str | None = Field(default=None, alias="CLAUDE_CODE_SESSION")

    # Gemini project ID for quota metrics (optional, ENABLE_EXPERIMENTAL)
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
