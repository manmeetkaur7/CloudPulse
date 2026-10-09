from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "cloudpulse-api"}


@router.get("/health/ready")
def readiness_check(request: Request) -> dict[str, str]:
    return {"status": "ready", "service": "cloudpulse-api", "redis": request.app.state.redis_service.status}
