# AI Usage Dashboard - TODO

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1: API Foundation ✅

### 1.1 Python Project Setup (uv)
- [x] Initialise `api/` directory with `uv init`
- [x] Add dependencies: FastAPI, uvicorn, SQLAlchemy, alembic, psycopg2-binary, pydantic-settings
- [x] Add dev dependencies: pytest, pytest-asyncio, httpx, pytest-cov
- [x] Configure `pyproject.toml` with project metadata and scripts

### 1.2 Database Schema
- [x] `models` table – AI model registry (name, provider, cost_per_input_token, cost_per_output_token)
- [x] `projects` table – project registry (name, team, description)
- [x] `usage_records` table – core data (model_id, project_id, timestamp, input_tokens, output_tokens, latency_ms, success, cost, raw_metadata)
- [x] Alembic migration baseline

### 1.3 REST API Endpoints
- [x] `POST /api/v1/usage` – ingest a usage record
- [x] `GET  /api/v1/usage` – list records (filters: model, project, team, from, to)
- [x] `GET  /api/v1/usage/summary` – aggregated stats (calls, tokens, cost, avg latency)
- [x] `GET  /api/v1/models` – list registered models
- [x] `POST /api/v1/models` – register a model
- [x] `GET  /api/v1/projects` – list projects
- [x] `POST /api/v1/projects` – create a project
- [x] `GET  /health` – liveness probe

### 1.4 Tests
- [x] Pytest setup with SQLite in-memory database for tests
- [x] Tests for all CRUD endpoints
- [x] Tests for summary/aggregation logic
- [x] ≥80% coverage target

### 1.5 Podman Compose Deployment
- [x] `compose.yaml` at repo root (podman-compose / docker-compose compatible)
- [x] Services: `api`, `db` (PostgreSQL 16)
- [x] Named volume for postgres data
- [x] `.env.example` with required environment variables
- [x] Health-check on `db` so `api` waits before starting
- [x] Dockerfile for `api` using uv multi-stage build

### 1.6 GitHub Actions CI
- [x] `.github/workflows/ci.yml` – runs on push and pull_request to `main`
- [x] Jobs: lint (ruff), test (pytest + coverage), build (docker build --no-push)
- [x] Cache uv / pip between runs
- [x] Upload coverage report as artifact
- [x] Stub deploy job (gated on `main` branch + manual approval) for future CD

---

## Phase 2: Frontend Dashboard 🚧

### 2.1 Project Scaffold
- [x] Vite + React 18 scaffold in `frontend/`
- [x] TypeScript config (`tsconfig.json`, `tsconfig.node.json`)
- [x] Tailwind CSS v3 with PostCSS
- [x] ESLint config

### 2.2 Design System & Tailwind Config
- [x] Custom color palette (neo bg `#f0f4f8`, text, accents)
- [x] Neumorphic box-shadow tokens (`shadow-neo`, `shadow-neo-sm`, `shadow-neo-inset`, `shadow-neo-press`)
- [x] Glassmorphic utility classes (`card-glass`, `btn-glass`, `input-glass`)
- [x] Global CSS reset + font setup
- [x] `@layer components` for reusable class combos

### 2.3 UI Primitives (`src/components/ui/`)
- [x] `Button` – variants: `neo` (raised/pressed), `glass`, `ghost`; sizes: `sm`, `md`, `lg`
- [x] `Card` – variants: `neo`, `glass`; with optional title slot
- [x] `Input` – neumorphic inset style; label, error state
- [x] `Select` – same styling as Input; options from array prop
- [x] `Badge` – colour variants for model names / status labels
- [ ] `Skeleton` – loading placeholder shimmer for cards/charts

### 2.4 Layout (`src/components/layout/`)
- [x] `Header` – glassmorphic sticky top bar; app title + filter toggle button
- [x] `Sidebar` – glassmorphic side nav; links: Dashboard, Models, Projects
- [x] `Layout` – wraps page content with sidebar + header; responsive collapse

### 2.5 Dashboard Components (`src/components/dashboard/`)
- [x] `StatCard` – neumorphic; shows label, value, delta (+ trend arrow + colour)
- [x] `ChartCard` – neumorphic container wrapping a Recharts chart; title + optional subtitle
- [x] `FilterPanel` – glassmorphic slide-in side panel; model / project / team / date-range controls
- [ ] `ModelTable` – sortable table of models with per-model stats
- [ ] `ExportButton` – triggers CSV download of current filtered data

### 2.6 Charts (`src/components/charts/`)
- [x] `UsageLineChart` – calls over time (line); x=date, y=count; one series per model
- [x] `CostBarChart` – cost by model (bar); grouped by project optionally
- [x] `TokenPieChart` – input vs output token split (pie / donut)
- [ ] `LatencyChart` – avg latency trend over time (area chart)

### 2.7 API Integration (`src/lib/` + `src/hooks/`)
- [x] `src/lib/api.ts` – fetch wrapper; base URL from `VITE_API_URL` env var
- [x] `src/hooks/useUsageSummary.ts` – TanStack Query hook for `/api/v1/usage/summary`
- [x] `src/hooks/useUsage.ts` – hook for `/api/v1/usage` with filter params
- [x] `src/hooks/useModels.ts` – hook for `/api/v1/models`
- [x] `src/hooks/useProjects.ts` – hook for `/api/v1/projects`
- [ ] `src/hooks/useExport.ts` – fetches data + triggers CSV download via `papaparse`

### 2.8 Pages (`src/pages/`)
- [x] `DashboardPage` – stat cards row + charts grid + filter panel integration
- [ ] `ModelsPage` – list/register models; model detail with usage breakdown
- [ ] `ProjectsPage` – list/create projects; project detail with usage breakdown

### 2.9 Infrastructure
- [x] `frontend/Dockerfile` – multi-stage: Vite build → Nginx serve
- [x] `frontend/nginx.conf` – SPA routing (try_files fallback) + API proxy
- [x] `compose.yaml` updated: add `frontend` service on port 3000
- [ ] `frontend/.env.example` – document `VITE_API_URL`

### 2.10 CI Updates
- [ ] Add `frontend` job to `.github/workflows/ci.yml`: `npm ci`, `npm run lint`, `npm run build`

---

## Phase 3: Alerts & Notifications

- [ ] Threshold configuration API (`POST/GET /api/v1/alerts`)
- [ ] Background worker (ARQ or Celery) for threshold checks
- [ ] Anomaly detection (Z-score baseline)
- [ ] Notification channels (email / webhook)
