from datetime import UTC, datetime, timedelta
from math import ceil, floor

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_repository
from app.api.projects import require_project
from app.models import MetricsBucket, MetricsTimeRange, ProjectMetrics
from app.repositories import SqlAlchemyRepository

router = APIRouter(prefix="/api/v1", tags=["metrics"])

TIME_RANGE_CONFIG: dict[MetricsTimeRange, tuple[timedelta, timedelta]] = {
    MetricsTimeRange.FIFTEEN_MINUTES: (timedelta(minutes=15), timedelta(minutes=1)),
    MetricsTimeRange.ONE_HOUR: (timedelta(hours=1), timedelta(minutes=5)),
    MetricsTimeRange.TWENTY_FOUR_HOURS: (timedelta(hours=24), timedelta(hours=1)),
    MetricsTimeRange.SEVEN_DAYS: (timedelta(days=7), timedelta(hours=6)),
}


def percentile_cont(values: list[float], percentile: float) -> float:
    """Continuous percentile interpolation, equivalent to PostgreSQL percentile_cont."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower, upper = floor(rank), ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def bucket_start(timestamp: datetime, width: timedelta) -> datetime:
    seconds = int(width.total_seconds())
    epoch_seconds = int(timestamp.astimezone(UTC).timestamp())
    return datetime.fromtimestamp(epoch_seconds - (epoch_seconds % seconds), UTC)


@router.get("/projects/{project_id}/metrics", response_model=ProjectMetrics)
def project_metrics(
    project_id: str,
    time_range: MetricsTimeRange = Query(default=MetricsTimeRange.ONE_HOUR),
    service_id: str | None = Query(default=None),
    repository: SqlAlchemyRepository = Depends(get_repository),
) -> ProjectMetrics:
    require_project(project_id, repository)
    if service_id is not None:
        service = repository.get_service(service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        if service.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Service does not belong to project")

    range_delta, bucket_width = TIME_RANGE_CONFIG[time_range]
    end_at = datetime.now(UTC)
    start_at = end_at - range_delta
    first_bucket = bucket_start(start_at, bucket_width)
    bucket_count = int(range_delta / bucket_width) + 1
    bucket_events: dict[datetime, list[object]] = {
        first_bucket + index * bucket_width: [] for index in range(bucket_count)
    }
    aggregated = repository.aggregate_historical_metrics(
        project_id, start_at, end_at, int(bucket_width.total_seconds()), service_id
    )
    if aggregated is None:
        for event in repository.list_historical_events(project_id, start_at, end_at, service_id):
            key = bucket_start(event.timestamp, bucket_width)
            if key in bucket_events:
                bucket_events[key].append(event)

    buckets: list[MetricsBucket] = []
    aggregates_by_timestamp = {
        row["timestamp"].astimezone(UTC): row for row in aggregated or []
    }
    for timestamp, events in bucket_events.items():
        aggregate = aggregates_by_timestamp.get(timestamp)
        if aggregate is not None:
            requests = int(aggregate["request_count"])
            explicit_errors = int(aggregate["explicit_error_count"])
            errors = int(aggregate["error_count"])
            population = requests + explicit_errors
            buckets.append(MetricsBucket(
                timestamp=timestamp,
                request_count=requests,
                error_count=errors,
                error_rate=round((errors / population * 100) if population else 0, 2),
                average_latency_ms=round(float(aggregate["average_latency_ms"] or 0), 2),
                p95_latency_ms=round(float(aggregate["p95_latency_ms"] or 0), 2),
            ))
            continue
        requests = [event for event in events if event.event_type == "request"]
        explicit_errors = [event for event in events if event.event_type == "error"]
        durations = [event.duration_ms for event in requests if event.duration_ms is not None]
        errors = len(explicit_errors) + sum(
            1 for event in requests if event.status_code is not None and event.status_code >= 500
        )
        population = len(requests) + len(explicit_errors)
        buckets.append(MetricsBucket(
            timestamp=timestamp,
            request_count=len(requests),
            error_count=errors,
            error_rate=round((errors / population * 100) if population else 0, 2),
            average_latency_ms=round(sum(durations) / len(durations), 2) if durations else 0.0,
            p95_latency_ms=round(percentile_cont(durations, 0.95), 2),
        ))
    return ProjectMetrics(
        time_range=time_range,
        bucket_width_seconds=int(bucket_width.total_seconds()),
        buckets=buckets,
    )
