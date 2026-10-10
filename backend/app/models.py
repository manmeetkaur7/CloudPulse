from datetime import UTC, datetime
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    REQUEST = "request"
    ERROR = "error"


class MetricsTimeRange(str, Enum):
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"


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
    timestamp: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    status_code: int | None = Field(default=None, ge=100, le=599)
    message: str | None = Field(default=None, max_length=1_000)
    trace_id: str | None = None
    span_id: str | None = None
    http_method: str | None = Field(default=None, max_length=10)
    http_route: str | None = Field(default=None, max_length=500)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value.astimezone(UTC)

    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[0-9a-fA-F]{32}", value) is None:
            raise ValueError("trace_id must be a 32-character hexadecimal value")
        return value.lower() if value else value

    @field_validator("span_id")
    @classmethod
    def validate_span_id(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[0-9a-fA-F]{16}", value) is None:
            raise ValueError("span_id must be a 16-character hexadecimal value")
        return value.lower() if value else value

    @field_validator("http_method")
    @classmethod
    def normalize_http_method(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class TelemetryEvent(TelemetryEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime



class ProjectSummary(BaseModel):
    total_requests: int
    average_latency_ms: float
    error_rate: float
    status: str


class MetricsBucket(BaseModel):
    timestamp: datetime
    request_count: int
    error_count: int
    error_rate: float
    average_latency_ms: float
    p95_latency_ms: float


class ProjectMetrics(BaseModel):
    time_range: MetricsTimeRange
    bucket_width_seconds: int
    buckets: list[MetricsBucket]


class TelemetryBatchCreate(BaseModel):
    events: list[TelemetryEventCreate] = Field(min_length=1, max_length=100)


class TelemetryBatchResult(BaseModel):
    accepted_count: int
