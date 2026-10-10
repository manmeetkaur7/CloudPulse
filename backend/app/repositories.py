from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import and_, func, literal_column, or_, select
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
            timestamp=data.timestamp or datetime.now(UTC),
            event_type=data.event_type.value,
            **data.model_dump(exclude={"event_type", "timestamp"}),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def create_telemetry_events(self, events: list[TelemetryEventCreate]) -> list[TelemetryEventRecord]:
        records = [
            TelemetryEventRecord(
                id=str(uuid4()),
                timestamp=data.timestamp or datetime.now(UTC),
                event_type=data.event_type.value,
                **data.model_dump(exclude={"event_type", "timestamp"}),
            )
            for data in events
        ]
        self.session.add_all(records)
        self.session.flush()
        return records

    def commit(self) -> None:
        self.session.commit()

    def list_recent_events(self, project_id: str, limit: int) -> list[TelemetryEventRecord]:
        statement = select(TelemetryEventRecord).where(TelemetryEventRecord.project_id == project_id).order_by(TelemetryEventRecord.timestamp.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_project_events(self, project_id: str) -> list[TelemetryEventRecord]:
        statement = select(TelemetryEventRecord).where(TelemetryEventRecord.project_id == project_id)
        return list(self.session.scalars(statement))

    def list_historical_events(
        self, project_id: str, start_at: datetime, end_at: datetime, service_id: str | None = None
    ) -> list[TelemetryEventRecord]:
        statement = select(TelemetryEventRecord).where(
            TelemetryEventRecord.project_id == project_id,
            TelemetryEventRecord.timestamp >= start_at,
            TelemetryEventRecord.timestamp < end_at,
        )
        if service_id is not None:
            statement = statement.where(TelemetryEventRecord.service_id == service_id)
        return list(self.session.scalars(statement))

    def aggregate_historical_metrics(
        self, project_id: str, start_at: datetime, end_at: datetime, bucket_width_seconds: int, service_id: str | None = None
    ) -> list[object] | None:
        """Aggregate populated buckets in PostgreSQL; SQLite tests use the portable fallback."""
        if self.session.bind is None or self.session.bind.dialect.name != "postgresql":
            return None
        event = TelemetryEventRecord
        bucket = func.date_bin(
            literal_column(f"INTERVAL '{bucket_width_seconds} seconds'"),
            event.timestamp,
            literal_column("TIMESTAMPTZ '1970-01-01 00:00:00+00'"),
        ).label("timestamp")
        is_request = event.event_type == "request"
        is_explicit_error = event.event_type == "error"
        is_error = or_(is_explicit_error, and_(is_request, event.status_code >= 500))
        statement = select(
            bucket,
            func.count().filter(is_request).label("request_count"),
            func.count().filter(is_explicit_error).label("explicit_error_count"),
            func.count().filter(is_error).label("error_count"),
            func.avg(event.duration_ms).filter(and_(is_request, event.duration_ms.is_not(None))).label("average_latency_ms"),
            func.percentile_cont(0.95).within_group(event.duration_ms).filter(
                and_(is_request, event.duration_ms.is_not(None))
            ).label("p95_latency_ms"),
        ).where(event.project_id == project_id, event.timestamp >= start_at, event.timestamp < end_at)
        if service_id is not None:
            statement = statement.where(event.service_id == service_id)
        return list(self.session.execute(statement.group_by(bucket).order_by(bucket)).mappings())
