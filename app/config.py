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

    # Claude Code organization ID (for experimental /api/organizations/{org_id}/usage)
    claude_code_org_id: str | None = Field(default=None, alias="CLAUDE_CODE_ORG_ID")

    # Mistral Vibe session cookie (for experimental console.mistral.ai vibe-usage)
    mistral_vibe_session: str | None = Field(default=None, alias="MISTRAL_VIBE_SESSION")

    # ── Subscription pricing (configurable) ───────────────────────────────
    # Monthly subscription prices in USD.  Set to 0 or leave default to
    # indicate "unknown / not subscribed".
    claude_code_subscription_price: float = Field(
        default=20.0, alias="CLAUDE_CODE_SUBSCRIPTION_PRICE",
        description="Monthly price (USD) for the Claude Code subscription plan.",
    )
    claude_code_plan_name: str = Field(
        default="Pro", alias="CLAUDE_CODE_PLAN_NAME",
    )
    codex_subscription_price: float = Field(
        default=200.0, alias="CODEX_SUBSCRIPTION_PRICE",
        description="Monthly price (USD) for the OpenAI Codex / ChatGPT Pro plan.",
    )
    codex_plan_name: str = Field(
        default="Pro", alias="CODEX_PLAN_NAME",
    )
    mistral_vibe_subscription_price: float = Field(
        default=19.99, alias="MISTRAL_VIBE_SUBSCRIPTION_PRICE",
        description="Monthly price (USD) for the Mistral le Chat / Vibe subscription.",
    )
    mistral_vibe_plan_name: str = Field(
        default="Pro", alias="MISTRAL_VIBE_PLAN_NAME",
    )

    # Per-token API pricing assumptions for savings estimation (USD per 1K tokens).
    # These are rough averages; override via env if your usage profile differs.
    claude_api_cost_per_1k_tokens: float = Field(
        default=0.015, alias="CLAUDE_API_COST_PER_1K_TOKENS",
    )
    openai_api_cost_per_1k_tokens: float = Field(
        default=0.01, alias="OPENAI_API_COST_PER_1K_TOKENS",
    )
    mistral_api_cost_per_1k_tokens: float = Field(
        default=0.002, alias="MISTRAL_API_COST_PER_1K_TOKENS",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
