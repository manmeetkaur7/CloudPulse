from datetime import UTC, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from test_observability import client, create_project, create_service


def metrics_url(project_id: str) -> str:
    return f"/api/v1/projects/{project_id}/metrics?time_range=15m"


def test_metrics_returns_utc_empty_buckets(client: TestClient) -> None:
    project = create_project(client)

    response = client.get(metrics_url(str(project["id"])))

    assert response.status_code == 200
    payload = response.json()
    assert payload["time_range"] == "15m"
    assert payload["bucket_width_seconds"] == 60
    assert len(payload["buckets"]) == 16
    assert all(bucket["timestamp"].endswith("Z") for bucket in payload["buckets"])
    assert all(
        bucket["request_count"] == bucket["error_count"] == 0
        and bucket["error_rate"] == bucket["average_latency_ms"] == bucket["p95_latency_ms"] == 0
        for bucket in payload["buckets"]
    )


def test_metrics_aggregates_requests_errors_and_continuous_p95(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    timestamp = datetime.now(UTC).isoformat()
    base = {"project_id": project["id"], "service_id": service["id"], "timestamp": timestamp}
    for duration in (100, 200, 300, 400, 500):
        assert client.post("/api/v1/telemetry/events", json={**base, "event_type": "request", "duration_ms": duration, "status_code": 200}).status_code == 201
    assert client.post("/api/v1/telemetry/events", json={**base, "event_type": "request", "duration_ms": 600, "status_code": 503}).status_code == 201
    assert client.post("/api/v1/telemetry/events", json={**base, "event_type": "error"}).status_code == 201

    response = client.get(metrics_url(str(project["id"])))

    assert response.status_code == 200
    populated = next(bucket for bucket in response.json()["buckets"] if bucket["request_count"] == 6)
    assert populated["error_count"] == 2
    assert populated["error_rate"] == round(2 / 7 * 100, 2)
    assert populated["average_latency_ms"] == 350.0
    assert populated["p95_latency_ms"] == 575.0


def test_metrics_normalizes_offset_timestamp_to_utc_bucket(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    now = datetime.now(UTC)
    timestamp = (now - timedelta(minutes=2)).astimezone(timezone(-timedelta(hours=7))).isoformat()
    # The payload is intentionally offset-qualified; the model converts it to UTC before persistence.
    response = client.post("/api/v1/telemetry/events", json={
        "project_id": project["id"], "service_id": service["id"], "event_type": "request",
        "timestamp": timestamp, "duration_ms": 125,
    })

    metrics_response = client.get(metrics_url(str(project["id"])))

    assert response.status_code == 201
    assert response.json()["timestamp"].endswith("Z")
    assert any(bucket["request_count"] == 1 for bucket in metrics_response.json()["buckets"])


def test_metrics_validates_project_service_and_time_range(client: TestClient) -> None:
    first = create_project(client, "First")
    second = create_project(client, "Second")
    second_service = create_service(client, str(second["id"]))

    missing_project = client.get("/api/v1/projects/missing/metrics?time_range=1h")
    missing_service = client.get(f"/api/v1/projects/{first['id']}/metrics?service_id=missing")
    mismatch = client.get(f"/api/v1/projects/{first['id']}/metrics?service_id={second_service['id']}")
    invalid_range = client.get(f"/api/v1/projects/{first['id']}/metrics?time_range=2h")

    assert missing_project.status_code == 404
    assert missing_service.status_code == 404
    assert mismatch.status_code == 422
    assert invalid_range.status_code == 422


def test_metrics_filters_to_requested_service(client: TestClient) -> None:
    project = create_project(client)
    first_service = create_service(client, str(project["id"]), "first")
    second_service = create_service(client, str(project["id"]), "second")
    for service in (first_service, second_service):
        assert client.post("/api/v1/telemetry/events", json={
            "project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 100,
        }).status_code == 201

    response = client.get(f"{metrics_url(str(project['id']))}&service_id={first_service['id']}")

    assert response.status_code == 200
    assert sum(bucket["request_count"] for bucket in response.json()["buckets"]) == 1
