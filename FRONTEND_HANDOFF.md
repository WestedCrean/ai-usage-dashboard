# Frontend Handoff

Base URL: `http://localhost:8000`

OpenAPI files:
- `openapi.json`
- `openapi.yaml`

## Core dashboard mapping

- Overview KPI cards: `GET /api/overview`
- Provider cards/table: `GET /api/providers`
- Model breakdown: `GET /api/models`
- Usage windows / limits: `GET /api/windows`
- Time series charts: `GET /api/timeseries`
- Subscriptions cards and savings section: `GET /api/subscriptions`
- Endpoint smoke test history: `GET /api/tests`
- Trigger smoke tests: `POST /api/tests/run`
- Trigger manual refresh: `POST /api/refresh`
- Refresh badge / freshness state: `GET /api/refresh/status`
- Health check: `GET /health`

## Suggested frontend polling

- Poll `GET /api/refresh/status` every 15-30s for freshness badge updates
- Refresh all dashboard datasets after `POST /api/refresh` returns
- Re-fetch `/api/tests` after `POST /api/tests/run`
- Re-fetch `/api/subscriptions` after `POST /api/refresh` if subscription/tool usage depends on latest collected metrics

## Subscriptions section

Use `GET /api/subscriptions` to render a dedicated subscriptions area for:
- Claude Code
- OpenAI Codex
- Mistral Vibe

### Top-level summary cards

Render from the top-level response fields:
- `total_subscription_cost`
- `total_api_equivalent`
- `total_estimated_savings`
- `generated_at`
- `caveats`

Suggested cards:
- Total Subscription Cost
- API Equivalent Cost
- Estimated Savings

### Per-tool subscription cards

Render one card per item in `tools`.

Important fields per tool:
- `tool_id`
- `display_name`
- `plan_name`
- `window_label`
- `used`
- `limit`
- `unit`
- `percent_used`
- `reset_at`
- `source`
- `api_equivalent_cost`
- `subscription_price`
- `estimated_savings`
- `notes`

Suggested card layout:
- Header: tool name + optional plan badge
- Usage row: `used / limit` with a progress bar when both are present
- Window metadata: current billing/usage window and reset time
- Cost comparison block:
  - Subscription price
  - Equivalent API cost
  - Savings
- Footer: source badge + notes/caveats

## UI behavior recommendations

- Show a progress bar only if both `used` and `limit` are present
- If `used` or `limit` is missing, show a clear empty state like “No usage data available”
- If `estimated_savings` is null, do not show a fake zero; show “Unavailable” or muted placeholder text
- Treat `notes` as important explanatory copy, not optional metadata
- Render `caveats` as a separate warning/info block below the subscription cards

## Notes for UI design

- Some providers can legitimately return no metrics when not configured
- Metric source labels matter: `official`, `inferred`, `experimental`, `unavailable`
- Currency is not always USD at provider level; Mistral values may be EUR and should not be merged visually into USD spend totals unless converted
- Gemini may have little or no usage data depending on configured credentials and feature support
- Subscription prices and API-equivalent cost assumptions are config-driven in parts of the system
- For Claude Code, Codex, and Mistral Vibe, public usage visibility may be partial or unavailable; the UI should be comfortable with missing usage, missing limits, and inferred savings
