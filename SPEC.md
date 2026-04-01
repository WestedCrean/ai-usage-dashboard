--- title: AI Usage Dashboard Specification version: 0.3 ---

# AI Usage Dashboard

## Overview
The AI Usage Dashboard provides a comprehensive view of AI model usage across projects and teams. It tracks model calls, token consumption, cost, and performance — enabling resource management and cost optimisation.

## Current State (v0.3)
- **Phase 1 complete**: FastAPI backend, PostgreSQL schema, full REST API, tests ≥80% coverage, Podman/Docker Compose deployment, GitHub Actions CI.
- **Phase 2 in progress**: React + Vite frontend with neumorphic/glassmorphic design system.

---

## Features

### 1. Model Usage Tracking
- **Model Calls:** Number of API calls per model.
- **Token Usage:** Total tokens consumed (input / output / combined) per model.
- **Cost:** Total cost incurred per model, calculated from per-token rates.
- **Performance:** Latency (ms) and success rate of model calls.

### 2. User Interface
- **Dashboard:** Visual stat cards + charts for usage metrics.
- **Filters:** Filter by model, project, team, and date range.
- **Reports:** CSV export of usage data.

### 3. Data Collection
- **REST API:** `POST /api/v1/usage` for programmatic ingestion.
- **Manual Input:** (future) Form-based manual entry.

### 4. Alerts and Notifications *(Phase 3)*
- **Threshold Alerts:** Notify when usage exceeds predefined thresholds.
- **Anomaly Detection:** Detect and alert on unusual usage patterns.

---

## Technical Architecture

### Backend (FastAPI)
- **Runtime:** Python 3.11+, `uv` package manager.
- **Database:** PostgreSQL 16 via SQLAlchemy ORM + Alembic migrations.
- **API:** RESTful, versioned under `/api/v1/`.
- **Config:** `pydantic-settings` reading from environment variables.
- **Tests:** pytest with SQLite in-memory, ≥80% coverage.

### Frontend (React + Vite)
- **Framework:** React 18 + TypeScript, Vite build tooling.
- **Styling:** Tailwind CSS v3 with custom neumorphism and glassmorphism design tokens.
- **Charts:** Recharts (React-native, composable).
- **Data Fetching:** TanStack Query (caching, loading/error states).
- **Icons:** Lucide React.

#### Design System
The frontend uses a hybrid visual language:

| Surface type          | Style             | Notes                                   |
|-----------------------|-------------------|-----------------------------------------|
| Stat cards            | Neumorphic raised | Solid bg `#f0f4f8`, dual box-shadow     |
| Chart containers      | Neumorphic raised | Same surface treatment                  |
| Primary buttons       | Neumorphic raised | `active:` state uses inset shadow       |
| Form inputs           | Neumorphic inset  | Recessed — "fill me in"                 |
| Filter side panel     | Glassmorphic      | `backdrop-filter: blur` over bg gradient|
| Modals / overlays     | Glassmorphic      | Blurs content beneath                   |
| Sticky nav/header     | Glassmorphic      | Shows content scrolling underneath      |

**Palette:**
```
Background:    #f0f4f8
Surface:       #e8edf5
Text primary:  #1a2942
Text muted:    #7a8fb5
Accent:        #6366f1 (indigo)
Success:       #10b981
Warning:       #f59e0b
Danger:        #ef4444
```

### Infrastructure
- **Compose:** `compose.yaml` at repo root (Podman / Docker compatible).
- **Services:** `db` (Postgres 16), `api` (FastAPI), `frontend` (Nginx serving Vite build).
- **CI:** GitHub Actions — lint, test, build on push/PR to `main`.

---

## API Endpoints

| Method | Path                    | Description                            |
|--------|-------------------------|----------------------------------------|
| POST   | /api/v1/usage           | Ingest a usage record                  |
| GET    | /api/v1/usage           | List records (filters: model, project, team, from, to) |
| GET    | /api/v1/usage/summary   | Aggregated stats (calls, tokens, cost, avg latency) |
| GET    | /api/v1/models          | List registered models                 |
| POST   | /api/v1/models          | Register a model                       |
| GET    | /api/v1/projects        | List projects                          |
| POST   | /api/v1/projects        | Create a project                       |
| GET    | /health                 | Liveness probe                         |

---

## Implementation Phases

### Phase 1: API Foundation ✅
- Database schema and Alembic migrations.
- Full REST API with FastAPI.
- pytest test suite (≥80% coverage).
- Podman Compose deployment.
- GitHub Actions CI.

### Phase 2: Frontend Dashboard 🚧
- Vite + React scaffold in `frontend/`.
- Tailwind CSS with custom neumorphic / glass design tokens.
- Reusable component library (Button, Card, Input, Badge, Modal).
- Responsive layout (Header, Sidebar, main grid).
- Stat cards wired to `/api/v1/usage/summary`.
- Charts: usage over time, cost by model, token breakdown.
- Filter panel (model, project, team, date range).
- CSV export.

### Phase 3: Alerts & Notifications
- Threshold configuration API.
- Background worker (ARQ / Celery) for threshold checks.
- Anomaly detection (Z-score baseline).
- Notification channels (email / webhook).

---

## Team
- **Project Lead:** Wiktor Flis

## Risks and Mitigation
- **Data Privacy:** Ensure compliance with data privacy regulations.
- **API Downtime:** Implement fallback mechanisms for data collection.
- **backdrop-filter browser support:** CSS fallback (`@supports`) provides opaque background on older browsers.

## Success Metrics
- **Adoption Rate:** Percentage of teams using the dashboard.
- **Cost Savings:** Reduction in AI usage costs.
- **User Satisfaction:** Feedback from dashboard users.
