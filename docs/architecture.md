# CloudPulse architecture

## Current architecture

CloudPulse is a small monorepo with two independently runnable applications:

- `frontend/` is a Next.js App Router application that renders the dashboard.
- `backend/` is a FastAPI application exposing health, project, service, telemetry, and project-summary endpoints.

The browser dashboard reads `NEXT_PUBLIC_API_BASE_URL` and uses a single frontend API client for backend requests. It requests the health endpoint after loading, lets users manage monitored projects and services, and sends development telemetry to the API. The API permits browser requests from the comma-separated origins configured in `BACKEND_CORS_ORIGINS`, which defaults to the local Next.js origin.

Projects, services, and telemetry events use a small `InMemoryRepository` storage boundary. This is deliberately temporary: its data disappears when the backend restarts. Keeping route handlers dependent on this repository makes replacing it with persistent storage later straightforward.

The project summary is calculated from stored events: request count, average request duration, and error rate. The error rate counts explicit error events and requests with a 5xx status exactly once, divided by all request and explicit-error events. A project is `degraded` at or above 10%; otherwise it is `healthy`.

No persistent database, authentication, background processing, or real-time transport exists in this stage.

## Future directions

Future iterations may add persistent storage, richer service metrics, event processing, real-time updates, alerting, OpenTelemetry support, and deployment infrastructure. Technologies such as PostgreSQL, Redis, Kafka, WebSockets, Docker, Kubernetes, and AI-assisted incident analysis are deliberately not part of the current implementation.
