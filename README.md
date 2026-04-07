# AI Usage Dashboard

A local Python dashboard for tracking AI API usage across OpenAI, Anthropic, Google Gemini, Mistral, and OpenRouter — plus coding tool windows for Claude Code, OpenAI Codex, Gemini CLI, and Mistral Vibe.

## Features

- Normalized metrics architecture across providers
- Dark-first dashboard UI with KPIs, charts, tables, and empty states
- Auto-refresh every 15 minutes plus manual refresh
- SQLite persistence for refresh runs, snapshots, metrics, and endpoint tests
- Provider filtering so only configured providers appear in provider and window views
- Honest endpoint smoke tests with PASS / FAIL / SKIPPED states and real HTTP status verification
- Subscription usage and savings view for Claude Code, OpenAI Codex, and Mistral Vibe
- Experimental support for hidden session-based endpoints for Claude Code and Mistral Vibe
- OpenAPI docs at `/docs`

## Quick Start

```bash
cd ai-usage-dashboard
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

## Environment Variables

Copy `.env.example` to `.env` and set the variables you have.

### API providers

- `OPENAI_API_KEY`
- `OPENAI_ORG_ID`
- `OPENAI_PROJECT_ID`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`
- `OPENROUTER_API_KEY`

### App config

- `HOST`
- `PORT`
- `DEBUG`
- `DB_PATH`
- `REFRESH_INTERVAL_MINUTES`
- `ENABLE_EXPERIMENTAL`

### Experimental hidden endpoint auth

- `CLAUDE_CODE_SESSION`
- `CLAUDE_CODE_ORG_ID`
- `MISTRAL_VIBE_SESSION`
- `GOOGLE_CLOUD_PROJECT`

### Subscription pricing inputs

- `CLAUDE_CODE_SUBSCRIPTION_PRICE`
- `CLAUDE_CODE_PLAN_NAME`
- `CODEX_SUBSCRIPTION_PRICE`
- `CODEX_PLAN_NAME`
- `MISTRAL_VIBE_SUBSCRIPTION_PRICE`
- `MISTRAL_VIBE_PLAN_NAME`
- `CLAUDE_API_COST_PER_1K_TOKENS`
- `OPENAI_API_COST_PER_1K_TOKENS`
- `MISTRAL_API_COST_PER_1K_TOKENS`

## Dashboard sections

- Overview
- Providers
- Models
- Usage History
- Subscriptions
- Windows
- Endpoint Tests

## Provider behavior

### API providers

- OpenAI
- Anthropic
- Google Gemini
- Mistral AI
- OpenRouter

These appear in provider and usage-window views only when the relevant credentials are configured.

### Tool and subscription views

- OpenAI Codex
- Claude Code
- Gemini CLI
- Mistral Vibe

The subscriptions section tracks Claude Code, Codex, and Mistral Vibe subscription pricing and estimated API-equivalent savings. Actual usage is shown when enough data is available. Otherwise, the UI shows clear caveats and placeholders.

## Hidden endpoints

Two hidden session-based endpoints are wired behind `ENABLE_EXPERIMENTAL=true`:

- Claude Code: `https://claude.ai/api/organizations/{org_id}/usage`
- Mistral Vibe: `https://console.mistral.ai/api/billing/v2/vibe-usage`

These require browser session cookies, not just API keys, and may break without notice.

## Smoke tests

Run from the UI or via the API.

- `GET /api/tests`
- `POST /api/tests/run`

Status meanings:
- `pass`: HTTP response under 400 and valid JSON
- `fail`: HTTP error, timeout, non-JSON, or network failure
- `skipped`: provider not configured

## Project structure

```text
ai-usage-dashboard/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── db.py
│   ├── scheduler.py
│   ├── providers/
│   ├── services/
│   ├── templates/
│   └── static/
├── tests/
├── data/
├── .env.example
├── README.md
├── ENDPOINTS.md
├── FRONTEND_HANDOFF.md
├── openapi.json
└── openapi.yaml
```

## Notes

- OpenAI usage and billing access varies by account and key scope.
- Anthropic official admin usage endpoints exist, but standard API-key coverage differs from admin-key coverage.
- Gemini still has limited usage visibility via the standard AI Studio API.
- Mistral spend may be EUR-denominated and should not be merged into USD totals without conversion.
- Hidden session-based endpoints are experimental by nature.

See `ENDPOINTS.md` for the full endpoint reference.
