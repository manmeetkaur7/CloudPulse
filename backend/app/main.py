from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.projects import router as projects_router
from app.api.realtime import router as realtime_router
from app.api.telemetry import ingestion_router, router as telemetry_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from sqlalchemy.orm import Session, sessionmaker
from app.realtime.manager import ProjectConnectionManager
from app.infrastructure.redis_service import RedisService

def create_app(session_factory: sessionmaker[Session] | None = None, redis_service: RedisService | None = None) -> FastAPI:
    settings = get_settings()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def forward(message: dict[str, object]) -> None:
            await app.state.connection_manager.broadcast(str(message["project_id"]), message)
        await app.state.redis_service.start(forward)
        yield
        await app.state.redis_service.stop()

    app = FastAPI(title="CloudPulse API", version="0.6.0", lifespan=lifespan)
    app.state.session_factory = session_factory or SessionLocal
    app.state.connection_manager = ProjectConnectionManager()
    app.state.redis_service = redis_service or RedisService(settings.redis_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(projects_router)
    app.include_router(telemetry_router)
    app.include_router(ingestion_router)
    app.include_router(realtime_router)
    return app


app = create_app()
