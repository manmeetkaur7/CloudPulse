# CloudPulse

CloudPulse is an application observability platform in its early foundation stage. It currently lets you create monitored projects and services, submit telemetry events, and view calculated project metrics.

## Current status

Implemented: a Next.js dashboard, FastAPI health and project APIs, environment-configured CORS, in-memory projects/services/telemetry, and summary metrics calculated from submitted events.

Planned: persistent storage, richer metrics and dashboards, incidents, alerts, OpenTelemetry integration, event processing, and deployment infrastructure.

## Architecture and stack

- `frontend/`: Next.js, TypeScript, Tailwind CSS, App Router
- `backend/`: FastAPI and Python
- `docs/architecture.md`: current architecture details and future directions

## Current functionality

- Create and list monitored projects.
- Create and list services within a project.
- Submit `request` and `error` telemetry events for a service.
- View a selected project's request count, average request latency, error rate, and deterministic health status.
- Use the dashboard's Development demo controls to submit real test request or error events to its selected project's first service.

The current repository is an in-memory development foundation: projects, services, and telemetry are lost whenever the backend restarts.

### Summary metric rules

- `total_requests` counts events whose type is `request`.
- `average_latency_ms` averages `duration_ms` only among request events that include a duration; it is `0` when none do.
- `error_rate` is `(explicit error events + request events with status code 500 or higher) / (request events + explicit error events) * 100`. A request with a 5xx status is counted once.
- Status is `healthy` below a 10% error rate and `degraded` at or above 10%. This is a deterministic threshold, not anomaly detection.

## Local development

1. Copy `.env.example` to `.env.local` at the repository root, or create `frontend/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. Do not commit either file.
2. In one terminal, create and activate a Python virtual environment, install API dependencies, then run the API:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. In another terminal, install and run the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open `http://localhost:3000`. The dashboard will show API Connected while the backend health endpoint is available.

## Validation

```powershell
cd backend; pytest
cd frontend; npm run lint; npm run build
git diff --check
```
