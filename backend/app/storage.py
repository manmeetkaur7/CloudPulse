"""Temporary in-memory storage. All data is lost whenever the API restarts."""

from app.models import Project, ProjectCreate, Service, ServiceCreate, TelemetryEvent, TelemetryEventCreate


class InMemoryRepository:
    """Small repository boundary intended to be replaced by persistent storage later."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._services: dict[str, Service] = {}
        self._events: list[TelemetryEvent] = []

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project.from_create(data)
        self._projects[project.id] = project
        return project

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def create_service(self, project_id: str, data: ServiceCreate) -> Service:
        service = Service.from_create(project_id, data)
        self._services[service.id] = service
        return service

    def get_service(self, service_id: str) -> Service | None:
        return self._services.get(service_id)

    def list_services(self, project_id: str) -> list[Service]:
        return [service for service in self._services.values() if service.project_id == project_id]

    def store_event(self, data: TelemetryEventCreate) -> TelemetryEvent:
        event = TelemetryEvent.from_create(data)
        self._events.append(event)
        return event

    def list_events(self, project_id: str, limit: int) -> list[TelemetryEvent]:
        events = [event for event in self._events if event.project_id == project_id]
        return list(reversed(events[-limit:]))

    def list_all_events(self, project_id: str) -> list[TelemetryEvent]:
        return [event for event in self._events if event.project_id == project_id]
