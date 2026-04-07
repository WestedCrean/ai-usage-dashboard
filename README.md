# AI Usage Dashboard

A local Python dashboard for tracking AI API usage across OpenAI, Anthropic, Google Gemini, Mistral, and OpenRouter — plus coding tool windows for Claude Code, OpenAI Codex, Gemini CLI, and Mistral Vibe.

## Features

- **Normalized metrics architecture** — all providers share a common data model
- **Dark-first, polished UI** — technical dashboard with charts, KPI cards, and data tables
- **Auto-refresh every 15 minutes** via APScheduler + manual Refresh button
- **SQLite persistence** — snapshots and metric history survive restarts
- **Graceful empty states** — missing API keys show clear "not configured" UI rather than errors
- **Data source transparency** — every metric labeled Official / Inferred / Experimental / N/A
- **Endpoint smoke tests** — one-click test of all configured provider endpoints
- **OpenAPI docs** at `/docs`

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)

## Quick Start

```bash
# 1. Clone or unzip the project
cd ai-usage-dashboard

# 2. Install dependencies
uv sync

# 3. Configure credentials (copy the example and fill in your keys)
cp .env.example .env
# Edit .env with your API keys

# 4. Run the dashboard
uv run uvicorn app.main:app --reload
# OR
uv run python -m app.main
```

Open http://localhost:8000 in your browser.

## Environment Variables

Copy `.env.example` to `.env` and set the variables you have:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Optional | OpenAI API key (sk-...) |
| `OPENAI_ORG_ID` | Optional | OpenAI organization ID — enables org-level usage data |
| `OPENAI_PROJECT_ID` | Optional | OpenAI project ID |
| `ANTHROPIC_API_KEY` | Optional | Anthropic API key (sk-ant-...) |
| `GEMINI_API_KEY` | Optional | Google AI Studio API key |
| `MISTRAL_API_KEY` | Optional | Mistral AI API key |
| `OPENROUTER_API_KEY` | Optional | OpenRouter API key (sk-or-...) |
| `HOST` | Optional | Bind address (default: `127.0.0.1`) |
| `PORT` | Optional | Port (default: `8000`) |
| `DEBUG` | Optional | Enable Uvicorn reload (default: `false`) |
| `DB_PATH` | Optional | SQLite database path (default: `data/dashboard.db`) |
| `REFRESH_INTERVAL_MINUTES` | Optional | Auto-refresh interval (default: `15`) |
| `ENABLE_EXPERIMENTAL` | Optional | Enable experimental/community endpoints (default: `false`) |
| `CLAUDE_CODE_SESSION` | Optional | Claude Code session cookie (requires `ENABLE_EXPERIMENTAL=true`) |
| `GOOGLE_CLOUD_PROJECT` | Optional | GCP project ID for Cloud Monitoring quota (requires `ENABLE_EXPERIMENTAL=true`) |

## Providers

### API Providers (official REST APIs)

| Provider | Usage Data | Cost Data | Notes |
|---|---|---|---|
| OpenAI | ⚠️ Access-dependent (`/v1/usage`, experimental org usage path also documented) | ⚠️ Dashboard billing path tested as best-effort | Org-level key recommended; response shape may vary |
| Anthropic | ⚠️ Beta/admin usage reporting endpoints researched | ⚠️ Inferred from public pricing in this build | Adapter currently uses beta `/v1/usage` assumptions |
| Google Gemini | ❌ Not available via AI Studio API | ❌ Not available | Model list only; Cloud Monitoring quota path is documented but not implemented |
| Mistral AI | ⚠️ Usage endpoint assumptions implemented | ⚠️ EUR balance and spend tracked separately from USD totals | Workspace-level key |
| OpenRouter | ✅ Official (`/api/v1/auth/key`) | ✅ Official | Credit-based billing; recent generations queried for token breakdown |

### Coding Tools (subscription / CLI tools)

These tools do not expose machine-readable usage APIs. They appear in the dashboard with appropriate empty states.

| Tool | Notes |
|---|---|
| OpenAI Codex | Billed through OpenAI account; visible under OpenAI billing |
| Claude Code | Subscription; session-level experimental endpoint available |
| Gemini CLI | Google account free tier or Gemini Advanced subscription |
| Mistral Vibe | Subscription coding assistant |

## Running Endpoint Smoke Tests

Via the dashboard UI: navigate to **Endpoint Tests** → click **Run Tests**.

Via CLI:

```bash
uv run python -m app.services.smoke_tests
```

## Project Structure

```
ai-usage-dashboard/
├── app/
│   ├── main.py              # FastAPI app, routes, lifespan
│   ├── config.py            # Pydantic settings (env vars)
│   ├── models.py            # Pydantic data models
│   ├── db.py                # SQLite persistence (aiosqlite)
│   ├── scheduler.py         # APScheduler background refresh
│   ├── providers/
│   │   ├── base.py          # BaseProvider abstract class
│   │   ├── openai.py        # OpenAI adapter
│   │   ├── anthropic.py     # Anthropic adapter
│   │   ├── gemini.py        # Google Gemini adapter
│   │   ├── mistral.py       # Mistral AI adapter
│   │   ├── openrouter.py    # OpenRouter adapter
│   │   └── tool_usage.py    # Codex, Claude Code, Gemini CLI, Mistral Vibe
│   ├── services/
│   │   ├── collector.py     # Orchestrates all providers
│   │   ├── metrics.py       # KPI aggregation
│   │   └── smoke_tests.py   # Endpoint smoke tests
│   ├── templates/
│   │   └── dashboard.html   # Jinja2 HTML template
│   └── static/
│       ├── css/dashboard.css
│       └── js/dashboard.js
├── tests/                   # lightweight pytest checks for metrics/window logic
├── data/                    # SQLite DB (auto-created)
├── .env.example
├── pyproject.toml
├── README.md
└── ENDPOINTS.md
```

## API Reference

See [ENDPOINTS.md](ENDPOINTS.md) for the full list of API endpoints (both dashboard and provider endpoints).

Interactive docs: http://localhost:8000/docs

## Data Model

The database stores:

- **refresh_runs** — each refresh cycle with timestamps and success counts
- **raw_snapshots** — full JSON responses from each provider per run
- **metric_points** — normalized measurements (cost, tokens, requests) per provider/model
- **endpoint_tests** — smoke test results with status codes and latency

## Experimental Endpoints

Set `ENABLE_EXPERIMENTAL=true` in `.env` to unlock community-discovered or access-gated endpoints.
These are never required for baseline functionality and may break without warning.

Important caveats in this version:
- OpenAI usage and billing paths are implemented as best-effort because public coverage is fragmented and account access varies.
- Anthropic usage support is based on researched beta/admin reporting references, but real response schemas may require adapter updates once tested with your credentials.
- Gemini quota collection via Cloud Monitoring is documented but not yet implemented.

See [ENDPOINTS.md](ENDPOINTS.md) for details.
