# AI Usage Dashboard - TODO

## Status Legend
- [ ] Not started
- [x] Done

---

## Phase 1: API Foundation (Current Focus)

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

## Phase 2: Frontend Dashboard (Future)
- [ ] React + Vite scaffold in `frontend/`
- [ ] Chart.js / Recharts integration
- [ ] Filter controls (model, project, team, date range)
- [ ] Export to CSV

## Phase 3: Alerts & Notifications (Future)
- [ ] Threshold configuration API
- [ ] Background worker (ARQ or Celery) for threshold checks
- [ ] Anomaly detection (Z-score baseline)
- [ ] Notification channels (email / webhook)
