from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.telemetry import router as telemetry_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from sqlalchemy.orm import Session, sessionmaker

def create_app(session_factory: sessionmaker[Session] | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CloudPulse API", version="0.3.0")
    app.state.session_factory = session_factory or SessionLocal

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
