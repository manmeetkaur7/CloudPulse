from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    REQUEST = "request"
    ERROR = "error"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class Project(ProjectCreate):
    id: str
    created_at: datetime

    @classmethod
    def from_create(cls, data: ProjectCreate) -> "Project":
        return cls(id=str(uuid4()), created_at=datetime.now(UTC), **data.model_dump())


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    environment: str = Field(min_length=1, max_length=60)


class Service(ServiceCreate):
    id: str
    project_id: str
    created_at: datetime

    @classmethod
    def from_create(cls, project_id: str, data: ServiceCreate) -> "Service":
        return cls(id=str(uuid4()), project_id=project_id, created_at=datetime.now(UTC), **data.model_dump())


class TelemetryEventCreate(BaseModel):
    project_id: str = Field(min_length=1)
    service_id: str = Field(min_length=1)
    event_type: EventType
    duration_ms: float | None = Field(default=None, ge=0)
    status_code: int | None = None
    message: str | None = Field(default=None, max_length=1_000)


class TelemetryEvent(TelemetryEventCreate):
    id: str
    timestamp: datetime

    @classmethod
    def from_create(cls, data: TelemetryEventCreate) -> "TelemetryEvent":
        return cls(id=str(uuid4()), timestamp=datetime.now(UTC), **data.model_dump())


class ProjectSummary(BaseModel):
    total_requests: int
    average_latency_ms: float
    error_rate: float
    status: str
