from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_repository
from app.models import TelemetryBatchCreate, TelemetryBatchResult, TelemetryEvent, TelemetryEventCreate
from app.repositories import SqlAlchemyRepository

router = APIRouter(prefix="/api", tags=["telemetry"])
ingestion_router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry ingestion"])


def validate_relationships(data: TelemetryEventCreate, repository: SqlAlchemyRepository) -> None:
    if repository.get_project(data.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    service = repository.get_service(data.service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if service.project_id != data.project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Service does not belong to project")


async def notify_created(request: Request, event: TelemetryEvent) -> None:
    await request.app.state.connection_manager.broadcast(event.project_id, {
        "type": "telemetry.created",
        "project_id": event.project_id,
        "event": event.model_dump(mode="json"),
    })


@router.post("/telemetry", response_model=TelemetryEvent, status_code=status.HTTP_201_CREATED)
def ingest_telemetry(data: TelemetryEventCreate, repository: SqlAlchemyRepository = Depends(get_repository)) -> TelemetryEvent:
    validate_relationships(data, repository)
    return repository.create_telemetry_event(data)


@ingestion_router.post("/events", response_model=TelemetryEvent, status_code=status.HTTP_201_CREATED)
async def ingest_event(data: TelemetryEventCreate, request: Request, repository: SqlAlchemyRepository = Depends(get_repository)) -> TelemetryEvent:
    validate_relationships(data, repository)
    event = TelemetryEvent.model_validate(repository.create_telemetry_event(data))
    repository.commit()
    await notify_created(request, event)
    return event


@ingestion_router.post("/batch", response_model=TelemetryBatchResult, status_code=status.HTTP_201_CREATED)
async def ingest_batch(data: TelemetryBatchCreate, request: Request, repository: SqlAlchemyRepository = Depends(get_repository)) -> TelemetryBatchResult:
    for event in data.events:
        validate_relationships(event, repository)
    events = [TelemetryEvent.model_validate(event) for event in repository.create_telemetry_events(data.events)]
    repository.commit()
    for event in events:
        await notify_created(request, event)
    return TelemetryBatchResult(accepted_count=len(data.events))
