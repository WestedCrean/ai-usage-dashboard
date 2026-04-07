# ENDPOINTS.md — AI Usage Dashboard

Full reference for all endpoints: dashboard API endpoints and provider endpoints used internally.

---

## Dashboard API Endpoints

All endpoints are served locally at `http://localhost:8000` (configurable via `HOST` and `PORT`).

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI (HTML) |
| `GET` | `/health` | Health check — returns `{"status": "ok", "timestamp": "..."}` |
| `GET` | `/api/overview` | Top-level KPI summary (cost, tokens, requests, provider counts) |
| `GET` | `/api/providers` | Per-provider status and latest metrics |
| `GET` | `/api/models` | Per-model token/cost/request breakdown |
| `GET` | `/api/windows` | Usage window summaries with reset times |
| `GET` | `/api/timeseries` | Historical metric data for charts. Query params: `provider`, `kind`, `limit` |
| `GET` | `/api/tests` | Latest endpoint smoke test results |
| `POST` | `/api/tests/run` | Run endpoint smoke tests (returns results immediately) |
| `POST` | `/api/refresh` | Trigger immediate refresh across all providers |
| `GET` | `/api/refresh/status` | Last refresh run info + next scheduled run time |
| `GET` | `/docs` | Interactive OpenAPI documentation (Swagger UI) |
| `GET` | `/redoc` | ReDoc API documentation |

---

## Provider Endpoints

### OpenAI

**Data source:** Best-effort official / access-dependent

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `https://api.openai.com/v1/models` | GET | List available models | Bearer token |
| `https://api.openai.com/v1/usage` | GET | Usage by date range (implemented as a best-effort adapter path) | Bearer token, optional Org header |
| `https://api.openai.com/dashboard/billing/usage` | GET | Dashboard billing usage in cents (legacy/account-dependent path) | Bearer token |

**Required headers:**
```
Authorization: Bearer sk-...
OpenAI-Organization: org-... (optional, improves data quality)
```

**Notes:**
- `/v1/usage` is implemented in the adapter, but public documentation and response shape coverage are inconsistent across accounts.
- `/dashboard/billing/usage` is treated as a best-effort dashboard path; some accounts may not expose it.
- Organization-level access may be required for fuller data; project keys may see limited or no usage detail.

---

### Anthropic

**Data source:** Researched beta/admin reporting; Inferred cost in this build

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `https://api.anthropic.com/v1/models` | GET | List available models | x-api-key |
| `https://api.anthropic.com/v1/usage` | GET | Token usage (beta path assumed by the current adapter) | x-api-key + beta header |
| `https://api.anthropic.com/v1/organizations/usage_report/messages` | GET | Admin usage report reference researched for future adapter hardening | Admin auth requirements vary |

**Required headers:**
```
x-api-key: sk-ant-...
anthropic-version: 2023-06-01
anthropic-beta: usage-2025-01-01
```

**Notes:**
- The current adapter assumes `/v1/usage` works with the listed beta header, but real schemas may differ and should be validated with your key.
- Anthropic admin usage/cost reporting references were researched as fallback guidance for future adapter updates.
- Billing API is not used directly in this build; cost is inferred from public per-token pricing.

---

### Google Gemini

**Data source:** Official (model list); Unavailable (usage/cost)

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `https://generativelanguage.googleapis.com/v1beta/models` | GET | List available models | API key query param |

**Parameters:**
```
?key=AIzaSy...
```

**Notes:**
- Google AI Studio does not expose per-key usage metrics via REST API
- Usage data is available via Google Cloud Console manually
- To get quota metrics programmatically, set `ENABLE_EXPERIMENTAL=true` and `GOOGLE_CLOUD_PROJECT=<project-id>` — Cloud Monitoring API will be queried (not yet implemented in this version)

---

### Mistral AI

**Data source:** Best-effort official

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `https://api.mistral.ai/v1/models` | GET | List available models | Bearer token |
| `https://api.mistral.ai/v1/organization/billing/summary` | GET | Account balance | Bearer token |
| `https://api.mistral.ai/v1/organization/usage` | GET | Token usage detail by model | Bearer token |

**Required headers:**
```
Authorization: Bearer <mistral-key>
```

**Notes:**
- `/v1/organization/usage` is implemented with `start_date` and `end_date` assumptions for monthly collection.
- EUR-denominated balance and spend are stored separately from USD totals in the dashboard.
- Balance (`credits_remaining`) is returned from the billing summary path when available.

---

### OpenRouter

**Data source:** Official

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `https://openrouter.ai/api/v1/models` | GET | List all available models (public) | None required |
| `https://openrouter.ai/api/v1/auth/key` | GET | Key info, credit balance, usage | Bearer token |
| `https://openrouter.ai/api/v1/generation` | GET | Recent generation details (last N requests) | Bearer token |

**Required headers:**
```
Authorization: Bearer sk-or-...
```

**Notes:**
- `/api/v1/auth/key` returns key-level usage, limit, and remaining balance details used by the dashboard.
- `/api/v1/generation` accepts `limit` query param; the current adapter assumes prompt/completion token fields in recent generation payloads.
- No monthly reset window is assumed; usage is treated as cumulative unless a limit is present.

---

## Experimental / Community Endpoints

> **Warning:** These endpoints are NOT officially documented. They may change, break, or disappear at any time. Gate them behind `ENABLE_EXPERIMENTAL=true`. Never rely on them for baseline functionality.

### Claude Code — Analytics Endpoint

| Endpoint | Method | Source | Status |
|---|---|---|---|
| `https://api.claude.ai/api/organizations/usage` | GET | Community-discovered | Unverified |

**Required:**
- `ENABLE_EXPERIMENTAL=true`
- `CLAUDE_CODE_SESSION=<session_cookie_value>`

**Notes:**
- Requires an active Claude Code session cookie (not an API key)
- Response structure is undocumented and may change
- Only tested when both env vars are set

### OpenAI — Organization Completions Usage

| Endpoint | Method | Source | Status |
|---|---|---|---|
| `https://api.openai.com/v1/organization/usage/completions` | GET | Official (access-gated) | Limited availability |

**Required:**
- `ENABLE_EXPERIMENTAL=true`
- `OPENAI_ORG_ID=<org-id>`
- Org-level API key

**Notes:**
- This endpoint is documented but access is gated — not all API keys can query it
- May return 403 if the organization hasn't been granted access

### Gemini CLI — Cloud Monitoring Quotas

| Endpoint | Method | Source | Status |
|---|---|---|---|
| `https://monitoring.googleapis.com/v3/projects/{project}/timeSeries` | GET | Official (GCP) | Requires Cloud billing |

**Required:**
- `ENABLE_EXPERIMENTAL=true`
- `GOOGLE_CLOUD_PROJECT=<project-id>`
- Google Application Default Credentials or service account

**Notes:**
- Not yet implemented in this version
- Would expose quota utilization for `generativelanguage.googleapis.com` metrics

---

## Data Source Labels

Every metric point in the dashboard is labeled with a data source:

| Label | Meaning |
|---|---|
| **Official** | From a documented, public API endpoint |
| **Inferred** | Estimated from token counts × public per-token pricing |
| **Experimental** | From a community-discovered or access-gated endpoint |
| **N/A** | No credential configured, or endpoint returned an error |
