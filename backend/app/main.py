from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.telemetry import router as telemetry_router
from app.core.config import get_settings
from app.storage import InMemoryRepository

def create_app(repository: InMemoryRepository | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CloudPulse API", version="0.2.0")
    app.state.repository = repository or InMemoryRepository()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(telemetry_router)
    return app


app = create_app()
