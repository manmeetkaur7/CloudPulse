from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_repository
from app.models import TelemetryEvent, TelemetryEventCreate
from app.storage import InMemoryRepository

router = APIRouter(prefix="/api", tags=["telemetry"])


@router.post("/telemetry", response_model=TelemetryEvent, status_code=status.HTTP_201_CREATED)
def ingest_telemetry(data: TelemetryEventCreate, repository: InMemoryRepository = Depends(get_repository)) -> TelemetryEvent:
    if repository.get_project(data.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    service = repository.get_service(data.service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if service.project_id != data.project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Service does not belong to project")
    return repository.store_event(data)
