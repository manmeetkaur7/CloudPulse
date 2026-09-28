from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_repository
from app.models import Project, ProjectCreate, ProjectSummary, Service, ServiceCreate, TelemetryEvent
from app.storage import InMemoryRepository

router = APIRouter(prefix="/api", tags=["projects"])


def require_project(project_id: str, repository: InMemoryRepository) -> None:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, repository: InMemoryRepository = Depends(get_repository)) -> Project:
    return repository.create_project(data)


@router.get("/projects", response_model=list[Project])
def list_projects(repository: InMemoryRepository = Depends(get_repository)) -> list[Project]:
    return repository.list_projects()


@router.post("/projects/{project_id}/services", response_model=Service, status_code=status.HTTP_201_CREATED)
def create_service(project_id: str, data: ServiceCreate, repository: InMemoryRepository = Depends(get_repository)) -> Service:
    require_project(project_id, repository)
    return repository.create_service(project_id, data)


@router.get("/projects/{project_id}/services", response_model=list[Service])
def list_services(project_id: str, repository: InMemoryRepository = Depends(get_repository)) -> list[Service]:
    require_project(project_id, repository)
    return repository.list_services(project_id)


@router.get("/projects/{project_id}/telemetry", response_model=list[TelemetryEvent])
def list_telemetry(project_id: str, limit: int = Query(default=50, ge=1, le=100), repository: InMemoryRepository = Depends(get_repository)) -> list[TelemetryEvent]:
    require_project(project_id, repository)
    return repository.list_events(project_id, limit)


@router.get("/projects/{project_id}/summary", response_model=ProjectSummary)
def project_summary(project_id: str, repository: InMemoryRepository = Depends(get_repository)) -> ProjectSummary:
    require_project(project_id, repository)
    events = repository.list_all_events(project_id)
    requests = [event for event in events if event.event_type == "request"]
    explicit_errors = [event for event in events if event.event_type == "error"]
    durations = [event.duration_ms for event in requests if event.duration_ms is not None]
    errors = sum(1 for event in requests if event.status_code is not None and event.status_code >= 500) + len(explicit_errors)
    population = len(requests) + len(explicit_errors)
    error_rate = round((errors / population * 100) if population else 0, 2)
    average_latency = round((sum(durations) / len(durations)) if durations else 0, 2)
    return ProjectSummary(
        total_requests=len(requests),
        average_latency_ms=average_latency,
        error_rate=error_rate,
        status="degraded" if error_rate >= 10 else "healthy",
    )
