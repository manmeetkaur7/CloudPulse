from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import ProjectRecord, ServiceRecord, TelemetryEventRecord
from app.models import ProjectCreate, ServiceCreate, TelemetryEventCreate


class SqlAlchemyRepository:
    """Persistence boundary for CloudPulse's PostgreSQL-backed domain data."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_project(self, data: ProjectCreate) -> ProjectRecord:
        project = ProjectRecord(id=str(uuid4()), created_at=datetime.now(UTC), **data.model_dump())
        self.session.add(project)
        self.session.flush()
        return project

    def list_projects(self) -> list[ProjectRecord]:
        return list(self.session.scalars(select(ProjectRecord).order_by(ProjectRecord.created_at)))

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self.session.get(ProjectRecord, project_id)

    def create_service(self, project_id: str, data: ServiceCreate) -> ServiceRecord:
        service = ServiceRecord(id=str(uuid4()), project_id=project_id, created_at=datetime.now(UTC), **data.model_dump())
        self.session.add(service)
        self.session.flush()
        return service

    def get_service(self, service_id: str) -> ServiceRecord | None:
        return self.session.get(ServiceRecord, service_id)

    def list_services(self, project_id: str) -> list[ServiceRecord]:
        statement = select(ServiceRecord).where(ServiceRecord.project_id == project_id).order_by(ServiceRecord.created_at)
        return list(self.session.scalars(statement))

    def create_telemetry_event(self, data: TelemetryEventCreate) -> TelemetryEventRecord:
        event = TelemetryEventRecord(
            id=str(uuid4()),
            timestamp=datetime.now(UTC),
            event_type=data.event_type.value,
            **data.model_dump(exclude={"event_type"}),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_recent_events(self, project_id: str, limit: int) -> list[TelemetryEventRecord]:
        statement = select(TelemetryEventRecord).where(TelemetryEventRecord.project_id == project_id).order_by(TelemetryEventRecord.timestamp.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_project_events(self, project_id: str) -> list[TelemetryEventRecord]:
        statement = select(TelemetryEventRecord).where(TelemetryEventRecord.project_id == project_id)
        return list(self.session.scalars(statement))
