# CloudPulse architecture

## Current architecture

CloudPulse is a small monorepo with two independently runnable applications:

- `frontend/` is a Next.js App Router application that renders the dashboard.
- `backend/` is a FastAPI application exposing health, project, service, telemetry, and project-summary endpoints.

The browser dashboard reads `NEXT_PUBLIC_API_BASE_URL` and uses a single frontend API client for backend requests. It requests the health endpoint after loading, lets users manage monitored projects and services, and sends development telemetry to the API. The API permits browser requests from the comma-separated origins configured in `BACKEND_CORS_ORIGINS`, which defaults to the local Next.js origin.

Projects, services, and telemetry events use a `SqlAlchemyRepository` storage boundary. Each request receives one SQLAlchemy session, which commits after a successful request, rolls back on an exception, and always closes. The repository stores data in PostgreSQL using the `DATABASE_URL` environment variable; Alembic is the production schema migration mechanism. This replaces Sprint 2's temporary in-memory runtime storage, so data persists across backend restarts.

Automated tests use an isolated in-memory SQLite database created from the same SQLAlchemy metadata for each test. Runtime configuration remains PostgreSQL with the psycopg driver.

The project summary is calculated from stored events: request count, average request duration, and error rate. The error rate counts explicit error events and requests with a 5xx status exactly once, divided by all request and explicit-error events. A project is `degraded` at or above 10%; otherwise it is `healthy`.

No persistent database, authentication, background processing, or real-time transport exists in this stage.

## Future directions

Future iterations may add richer service metrics, event processing, real-time updates, alerting, OpenTelemetry support, and deployment infrastructure. Technologies such as Redis, Kafka, WebSockets, Docker, Kubernetes, and AI-assisted incident analysis are deliberately not part of the current implementation.
