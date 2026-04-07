# ENDPOINTS.md — AI Usage Dashboard

Reference for both dashboard API endpoints and provider endpoints used or researched by the app.

## Dashboard API endpoints

Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `GET` | `/health` | Health check |
| `GET` | `/api/overview` | KPI summary |
| `GET` | `/api/providers` | Provider cards for configured providers only |
| `GET` | `/api/models` | Model breakdown |
| `GET` | `/api/windows` | Usage windows for configured providers only |
| `GET` | `/api/timeseries` | Historical metric points for charts |
| `GET` | `/api/subscriptions` | Subscription usage, limits, and estimated savings |
| `GET` | `/api/tests` | Latest smoke test results |
| `POST` | `/api/tests/run` | Run smoke tests now |
| `POST` | `/api/refresh` | Trigger refresh now |
| `GET` | `/api/refresh/status` | Refresh freshness and next-run info |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

## Smoke test status rules

| Status | Meaning |
|---|---|
| `pass` | HTTP status under 400 and JSON parsed successfully |
| `fail` | HTTP/network/parsing failure |
| `skipped` | Provider not configured |

## Official and best-effort provider endpoints

### OpenAI

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `https://api.openai.com/v1/models` | GET | Model list | Bearer token | Used in smoke tests |
| `https://api.openai.com/v1/usage` | GET | Usage by date range | Bearer token | Best-effort, access varies |
| `https://api.openai.com/dashboard/billing/usage` | GET | Legacy dashboard billing usage | Browser/session or account-dependent | Best-effort, fragile |
| `https://api.openai.com/v1/organization/usage/completions` | GET | Organization usage | Org-level access | Official but access-gated |
| `https://api.openai.com/v1/organization/costs` | GET | Organization costs | Org-level access | Official usage dashboard companion |

### Anthropic

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `https://api.anthropic.com/v1/models` | GET | Model list | `x-api-key` | Used in smoke tests |
| `https://api.anthropic.com/v1/usage` | GET | Beta usage path | `x-api-key` + beta header | Best-effort, response may vary |
| `https://api.anthropic.com/v1/organizations/usage_report/messages` | GET | Official admin usage report | Admin API key | Official admin endpoint |
| `https://api.anthropic.com/v1/organizations/cost_report` | GET | Official admin cost report | Admin API key | Official admin endpoint |
| `https://api.anthropic.com/v1/organizations/me` | GET | Current organization | Admin API key | Useful for org discovery |

### Gemini

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `https://generativelanguage.googleapis.com/v1beta/models` | GET | Model list | API key | Used in smoke tests |
| `https://monitoring.googleapis.com/v3/projects/{project}/timeSeries` | GET | Quota metrics | GCP auth | Researched, not implemented |

### Mistral

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `https://api.mistral.ai/v1/models` | GET | Model list | Bearer token | Used in smoke tests |
| `https://api.mistral.ai/v1/organization/billing/summary` | GET | Balance and billing summary | Bearer token | Used by adapter |
| `https://api.mistral.ai/v1/organization/usage` | GET | Usage by model/date | Bearer token | Best-effort official usage path |

### OpenRouter

| Endpoint | Method | Purpose | Auth | Notes |
|---|---|---|---|---|
| `https://openrouter.ai/api/v1/models` | GET | Public model list | None | Public |
| `https://openrouter.ai/api/v1/auth/key` | GET | Key info, credits, usage | Bearer token | Used in smoke tests and adapter |
| `https://openrouter.ai/api/v1/generation` | GET | Recent generation details | Bearer token | Used for token breakdown assumptions |

## Hidden and experimental endpoints

These are session-based and should be treated as experimental.

### Claude Code

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `https://claude.ai/api/organizations` | GET | Discover organizations from web session | Claude session cookie |
| `https://claude.ai/api/organizations/{org_id}/usage` | GET | Claude Code usage / utilization | Claude session cookie |

Notes:
- Requires `ENABLE_EXPERIMENTAL=true`
- Requires `CLAUDE_CODE_SESSION`
- May also use `CLAUDE_CODE_ORG_ID`
- Community references indicate org discovery via web-session endpoints

Example shape observed from user-provided sample:
- `five_hour.utilization`
- `seven_day.utilization`
- `extra_usage.monthly_limit`
- `extra_usage.used_credits`

### Mistral Vibe

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `https://console.mistral.ai/api/billing/v2/vibe-usage` | GET | Vibe usage, quota, reset window | Mistral console session cookie |

Notes:
- Requires `ENABLE_EXPERIMENTAL=true`
- Requires `MISTRAL_VIBE_SESSION`
- Parses `usage_percentage`, `reset_at`, `start_date`, `end_date`, and per-model token groups

### OpenAI legacy dashboard billing

| Endpoint | Method | Purpose | Auth |
|---|---|---|---|
| `https://api.openai.com/dashboard/billing/usage` | GET | Legacy dashboard billing | Often browser-session dependent |

Notes:
- Community reports indicate this may require a browser session token instead of a standard API key
- Treat as legacy and unreliable

## Current UX constraints

- `/api/providers` and `/api/windows` hide providers without configured credentials.
- `/api/tests/run` currently covers configured API providers and marks missing ones as `skipped`.
- `/api/subscriptions` can still show config-driven subscription cards even when usage is unavailable.
- `/api/timeseries` may still include placeholder tool points if refresh collected them; this is a remaining consistency gap.

## Research references

- [Anthropic Usage & Cost Admin API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api)
- [Anthropic Organizations API](https://platform.claude.com/docs/en/api/admin/organizations)
- [OpenAI legacy billing endpoint discussion](https://community.openai.com/t/v1-dashboard-billing-usage-is-not-work/305887)
- [OpenAI usage dashboard legacy walkthrough](https://community.appsmith.com/tutorial/tracking-your-openai-api-costs-hidden-endpoint-custom-app)
- [Mistral Vibe product context](https://mistral.ai/news/mistral-vibe-2-0)
- [Community Claude session/org reference](https://github.com/st1vms/unofficial-claude-api)
