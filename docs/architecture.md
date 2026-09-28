# CloudPulse architecture

## Current architecture

CloudPulse is a small monorepo with two independently runnable applications:

- `frontend/` is a Next.js App Router application that renders the dashboard.
- `backend/` is a FastAPI application exposing `GET /health`.

The browser dashboard reads `NEXT_PUBLIC_API_BASE_URL` and requests the API health endpoint after it loads. The API permits browser requests from the comma-separated origins configured in `BACKEND_CORS_ORIGINS`, which defaults to the local Next.js origin.

No persistence, authentication, telemetry ingestion, background processing, or real-time transport exists in this stage.

## Future directions

Future iterations may add telemetry ingestion, persistent storage, service metrics, event processing, real-time updates, alerting, OpenTelemetry support, and deployment infrastructure. Technologies such as PostgreSQL, Redis, Kafka, WebSockets, Docker, Kubernetes, and AI-assisted incident analysis are deliberately not part of the current implementation.
