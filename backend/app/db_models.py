from datetime import datetime

from datetime import UTC

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UtcDateTime(TypeDecorator[datetime]):
    """Keeps SQLite test reads timezone-aware while mapping to PostgreSQL timestamps."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)

    services: Mapped[list["ServiceRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    telemetry_events: Mapped[list["TelemetryEventRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ServiceRecord(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)

    project: Mapped[ProjectRecord] = relationship(back_populates="services")
    telemetry_events: Mapped[list["TelemetryEventRecord"]] = relationship(back_populates="service", cascade="all, delete-orphan")


class TelemetryEventRecord(Base):
    __tablename__ = "telemetry_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('request', 'error')", name="telemetry_events_event_type_check"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="telemetry_events_duration_ms_check"),
        Index("ix_telemetry_events_project_timestamp", "project_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[ProjectRecord] = relationship(back_populates="telemetry_events")
    service: Mapped[ServiceRecord] = relationship(back_populates="telemetry_events")
