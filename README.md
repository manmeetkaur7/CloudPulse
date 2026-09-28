# CloudPulse

CloudPulse is an application observability platform in its foundation stage. It currently provides a responsive dashboard shell and a health endpoint for verifying API connectivity.

## Current status

Implemented: a Next.js dashboard, a FastAPI `GET /health` endpoint, environment-configured CORS, and a browser health check displayed in the dashboard.

Planned: telemetry ingestion, service metrics, dashboards, incidents, alerts, OpenTelemetry integration, event processing, and deployment infrastructure.

## Architecture and stack

- `frontend/`: Next.js, TypeScript, Tailwind CSS, App Router
- `backend/`: FastAPI and Python
- `docs/architecture.md`: current architecture details and future directions

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
