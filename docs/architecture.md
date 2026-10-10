# CloudPulse architecture

## Current architecture

CloudPulse is a small monorepo with two independently runnable applications:

- `frontend/` is a Next.js App Router application that renders the dashboard.
- `backend/` is a FastAPI application exposing health, project, service, telemetry, and project-summary endpoints.

The browser dashboard reads `NEXT_PUBLIC_API_BASE_URL` and uses a single frontend API client for backend requests. It requests the health endpoint after loading, lets users manage monitored projects and services, sends development telemetry to the API, displays a bounded recent-telemetry list, and renders historical charts. The API permits browser requests from the comma-separated origins configured in `BACKEND_CORS_ORIGINS`, which defaults to the local Next.js origin.

Projects, services, and telemetry events use a `SqlAlchemyRepository` storage boundary. Each request receives one SQLAlchemy session, which commits after a successful request, rolls back on an exception, and always closes. The repository stores data in PostgreSQL using the `DATABASE_URL` environment variable; Alembic is the production schema migration mechanism. This replaces Sprint 2's temporary in-memory runtime storage, so data persists across backend restarts.

Automated tests use an isolated in-memory SQLite database created from the same SQLAlchemy metadata for each test. Runtime configuration remains PostgreSQL with the psycopg driver.

The project summary is calculated from stored events: request count, average request duration, and error rate. The error rate counts explicit error events and requests with a 5xx status exactly once, divided by all request and explicit-error events. A project is `degraded` at or above 10%; otherwise it is `healthy`.

## Historical metrics

`GET /api/v1/projects/{project_id}/metrics` reads telemetry from PostgreSQL for one of four fixed ranges: `15m`, `1h`, `24h`, or `7d` (default `1h`). Optional `service_id` filtering verifies that the service belongs to the project. The response contains UTC-aligned buckets, including empty buckets: 1-minute buckets for `15m`, 5-minute buckets for `1h`, 1-hour buckets for `24h`, and 6-hour buckets for `7d`.

Each bucket includes request count, error count, error-rate percentage, average request latency, and P95 request latency. Request count and latency use request events; errors include explicit error events and 5xx request events, following the summary definition. P95 uses continuous interpolation over the bucket's request durations, equivalent to PostgreSQL `percentile_cont(0.95)`. The current query deliberately retrieves only the selected project's indexed timestamp window and computes the small, bounded bucket set in the application layer so the same behavior remains covered by SQLite unit tests; PostgreSQL remains the source of truth.

The dashboard uses Recharts for responsive request-volume, latency, and error-rate charts. It aborts stale metrics requests when a project or range changes. The existing single project WebSocket is preserved; a matching `telemetry.created` message continues refreshing the summary/recent list and schedules one debounced historical-metrics refresh for a telemetry burst.

## Telemetry ingestion

`POST /api/v1/telemetry/events` accepts external request and error events. `POST /api/v1/telemetry/batch` accepts 1–100 events in one transaction; if any event fails validation, none are stored. Both validate project/service ownership and event fields.

Telemetry stores optional trace IDs, span IDs, HTTP method, and HTTP route alongside the existing timestamp, duration, status, and error message. These are OpenTelemetry-compatible internal concepts only: CloudPulse is not an OTLP receiver or collector in this stage.

## Real-time notifications

The ingestion API persists telemetry first, commits the transaction, then emits one `telemetry.created` WebSocket notification per event to `WS /ws/projects/{project_id}/telemetry`. Batch ingestion emits individual notifications only after the complete batch commits. Dashboard clients use notifications to refetch the PostgreSQL-backed summary and bounded recent-event list.

Redis is optional infrastructure. When configured, ingestion commits to PostgreSQL, invalidates `cloudpulse:project:{project_id}:summary`, then publishes on `cloudpulse:project:{project_id}:telemetry`. Every FastAPI instance subscribes and forwards notifications only to its own local WebSocket connections. Summary cache entries use a 45-second TTL. Cache/pub-sub failures fall back to PostgreSQL and local notifications without rolling back telemetry.

PostgreSQL is the durable source of truth; Redis caching is a short-lived optimization and Redis pub/sub is not a durable event queue. Without Redis, CloudPulse remains functional for one backend instance. Horizontal scaling uses Redis notifications now; durable event streaming may use a separate system later.

No authentication, background processing, or real-time transport exists in this stage.

## Future directions

Future iterations may add richer service metrics, event processing, real-time updates, alerting, OpenTelemetry support, and deployment infrastructure. Technologies such as Redis, Kafka, WebSockets, Docker, Kubernetes, and AI-assisted incident analysis are deliberately not part of the current implementation.
