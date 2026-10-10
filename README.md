# CloudPulse

CloudPulse is an application observability platform in its early foundation stage. It lets you create monitored projects and services, submit telemetry events, and view calculated project metrics backed by PostgreSQL.

## Current status

Implemented: a Next.js dashboard, FastAPI health and project APIs, PostgreSQL persistence through SQLAlchemy, Alembic migrations, environment-configured CORS, and summary metrics calculated from submitted events.

Planned: persistent storage, richer metrics and dashboards, incidents, alerts, OpenTelemetry integration, event processing, and deployment infrastructure.

## Architecture and stack

- `frontend/`: Next.js, TypeScript, Tailwind CSS, App Router
- `backend/`: FastAPI and Python
- `docs/architecture.md`: current architecture details and future directions

## Current functionality

- Create and list monitored projects.
- Create and list services within a project.
- Submit `request` and `error` telemetry events for a service.
- Ingest external telemetry through versioned single-event and batch endpoints.
- View a selected project's request count, average request latency, error rate, and deterministic health status.
- Explore PostgreSQL-backed historical request volume, average/P95 latency, and error-rate charts for the last 15 minutes, hour, 24 hours, or 7 days.
- Use the dashboard's Development demo controls to submit real test request or error events to its selected project's first service.

Projects, services, and telemetry are stored in PostgreSQL and survive backend restarts once migrations have been applied.

### Summary metric rules

- `total_requests` counts events whose type is `request`.
- `average_latency_ms` averages `duration_ms` only among request events that include a duration; it is `0` when none do.
- `error_rate` is `(explicit error events + request events with status code 500 or higher) / (request events + explicit error events) * 100`. A request with a 5xx status is counted once.
- Status is `healthy` below a 10% error rate and `degraded` at or above 10%. This is a deterministic threshold, not anomaly detection.

### Telemetry ingestion

External applications can submit a single event to `POST /api/v1/telemetry/events` or up to 100 events atomically to `POST /api/v1/telemetry/batch`. Batch validation occurs before any events are written.

```json
{
  "project_id": "project-id",
  "service_id": "service-id",
  "event_type": "request",
  "timestamp": "2026-10-05T19:00:00Z",
  "duration_ms": 142,
  "status_code": 200,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "http_method": "GET",
  "http_route": "/movies/{id}"
}
```

The model uses OpenTelemetry-compatible concepts such as trace/span IDs, service, duration, and HTTP attributes. CloudPulse is **not** an OTLP receiver or collector yet. See [the Python telemetry client example](examples/telemetry-client/README.md) for a runnable external-client demonstration.

### Historical metrics

`GET /api/v1/projects/{project_id}/metrics` returns UTC-aligned metric buckets from PostgreSQL. It accepts `time_range=15m|1h|24h|7d` (default `1h`) and an optional `service_id` belonging to the selected project. Bucket widths are one minute for `15m`, five minutes for `1h`, one hour for `24h`, and six hours for `7d`; empty buckets are included. Each bucket contains `request_count`, `error_count`, `error_rate`, `average_latency_ms`, and `p95_latency_ms`.

P95 uses continuous percentile interpolation, equivalent to PostgreSQL's `percentile_cont(0.95)`. Error classification matches the summary metric rules. The dashboard refetches the selected range after relevant WebSocket telemetry notifications, with a short debounce to avoid one chart request per burst event.

### Real-time dashboard updates

After telemetry is committed to PostgreSQL, CloudPulse broadcasts a `telemetry.created` notification to dashboard clients subscribed to `WS /ws/projects/{project_id}/telemetry`. The dashboard then refetches the summary and recent events from the API; PostgreSQL remains the source of truth. The current connection manager is single-instance only. Horizontal scaling will require shared pub/sub infrastructure such as Redis or another event system, which is not implemented yet.

### Optional Redis support

Set `REDIS_URL=redis://localhost:6379/0` to enable a 45-second project-summary cache and cross-instance real-time notifications. PostgreSQL remains durable source of truth. Without Redis, telemetry still persists and local dashboard clients still receive notifications; summary requests calculate from PostgreSQL. Redis pub/sub is not a durable event queue.

## Local development

1. Install and start PostgreSQL, then create a database and local user. See [PostgreSQL setup](#postgresql-setup).
2. Configure the current PowerShell session with a database URL. Do not commit this value:

   ```powershell
   $env:DATABASE_URL = "postgresql+psycopg://cloudpulse:cloudpulse@localhost:5432/cloudpulse"
   ```

3. Create `frontend/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. Do not commit it.
4. In one terminal, create and activate a Python virtual environment, install API dependencies, apply migrations, then run the API:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

5. In another terminal, install and run the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open `http://localhost:3000`. The dashboard will show API Connected while the backend health endpoint is available.

## PostgreSQL setup

On Windows, first check whether PostgreSQL is installed:

```powershell
psql --version
Get-Service -Name postgresql* -ErrorAction SilentlyContinue
```

If it is not installed, install PostgreSQL using the official Windows installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/). During installation, retain the default port `5432` and set a password for the `postgres` administrator account.

After the service is running, create the local application role and database:

```powershell
psql -U postgres -h localhost -d postgres
```

Then run this SQL at the `psql` prompt, replacing the password before use:

```sql
CREATE USER cloudpulse WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE cloudpulse OWNER cloudpulse;
```

Update the PowerShell `DATABASE_URL` value to use the password you chose, then run `alembic upgrade head` from `backend/`.

## Persistence verification

1. Start PostgreSQL and set `DATABASE_URL` in the backend terminal.
2. Run `alembic upgrade head` and start the API.
3. Create a project, service, and telemetry event in the dashboard.
4. Stop the API with `Ctrl+C`, restart it with the same `DATABASE_URL`, and reload the dashboard.
5. Confirm the project, service, telemetry, and summary still appear.

## Validation

```powershell
cd backend; pytest
cd backend; alembic upgrade head
cd frontend; npm run lint; npm run build
git diff --check
```
