from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    REQUEST = "request"
    ERROR = "error"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class Project(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    environment: str = Field(min_length=1, max_length=60)


class Service(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    created_at: datetime



class TelemetryEventCreate(BaseModel):
    project_id: str = Field(min_length=1)
    service_id: str = Field(min_length=1)
    event_type: EventType
    duration_ms: float | None = Field(default=None, ge=0)
    status_code: int | None = None
    message: str | None = Field(default=None, max_length=1_000)


class TelemetryEvent(TelemetryEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime



class ProjectSummary(BaseModel):
    total_requests: int
    average_latency_ms: float
    error_rate: float
    status: str
