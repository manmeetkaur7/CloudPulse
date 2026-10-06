import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db_models import Base
from app.realtime.manager import ProjectConnectionManager


@pytest.fixture
def client() -> TestClient:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    with TestClient(create_app(test_session_factory)) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_project(client: TestClient, name: str = "StreamSphere") -> dict[str, object]:
    response = client.post("/api/projects", json={"name": name, "description": "Movie discovery platform"})
    assert response.status_code == 201
    return response.json()


def create_service(client: TestClient, project_id: str, name: str = "streamsphere-api") -> dict[str, object]:
    response = client.post(f"/api/projects/{project_id}/services", json={"name": name, "environment": "development"})
    assert response.status_code == 201
    return response.json()


def test_project_creation_and_listing(client: TestClient) -> None:
    project = create_project(client)

    response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json()[0]["id"] == project["id"]


def test_service_creation(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))

    response = client.get(f"/api/projects/{project['id']}/services")

    assert response.status_code == 200
    assert response.json() == [service]


def test_service_creation_for_missing_project_returns_404(client: TestClient) -> None:
    response = client.post("/api/projects/missing/services", json={"name": "api", "environment": "development"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_valid_telemetry_ingestion(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))

    response = client.post("/api/telemetry", json={"project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 142, "status_code": 200})

    assert response.status_code == 201
    assert response.json()["duration_ms"] == 142
    assert response.json()["timestamp"]


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"project_id": "missing", "service_id": "missing", "event_type": "request"}, "Project not found"),
        ({"project_id": "{project_id}", "service_id": "missing", "event_type": "request"}, "Service not found"),
    ],
)
def test_telemetry_with_missing_relationships(client: TestClient, payload: dict[str, str], detail: str) -> None:
    project = create_project(client)
    payload["project_id"] = payload["project_id"].format(project_id=project["id"])

    response = client.post("/api/telemetry", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == detail


def test_telemetry_rejects_project_service_mismatch(client: TestClient) -> None:
    first_project = create_project(client, "First")
    second_project = create_project(client, "Second")
    service = create_service(client, str(second_project["id"]))

    response = client.post("/api/telemetry", json={"project_id": first_project["id"], "service_id": service["id"], "event_type": "request"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Service does not belong to project"


def test_telemetry_rejects_invalid_event_type_and_negative_duration(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    base_payload = {"project_id": project["id"], "service_id": service["id"]}

    invalid_type = client.post("/api/telemetry", json={**base_payload, "event_type": "log"})
    negative_duration = client.post("/api/telemetry", json={**base_payload, "event_type": "request", "duration_ms": -1})

    assert invalid_type.status_code == 422
    assert negative_duration.status_code == 422


def test_summary_counts_one_request_and_one_explicit_error(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    base_payload = {"project_id": project["id"], "service_id": service["id"]}
    client.post("/api/telemetry", json={**base_payload, "event_type": "request", "duration_ms": 142, "status_code": 200})
    client.post("/api/telemetry", json={**base_payload, "event_type": "error", "message": "Failure"})

    response = client.get(f"/api/projects/{project['id']}/summary")

    assert response.json() == {"total_requests": 1, "average_latency_ms": 142.0, "error_rate": 50.0, "status": "degraded"}


def test_empty_summary_is_healthy_with_zero_values(client: TestClient) -> None:
    project = create_project(client)

    response = client.get(f"/api/projects/{project['id']}/summary")

    assert response.json() == {"total_requests": 0, "average_latency_ms": 0.0, "error_rate": 0.0, "status": "healthy"}


def test_recent_telemetry_is_bounded(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    payload = {"project_id": project["id"], "service_id": service["id"], "event_type": "request"}
    for _ in range(3):
        assert client.post("/api/telemetry", json=payload).status_code == 201

    response = client.get(f"/api/projects/{project['id']}/telemetry?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_v1_ingestion_accepts_otel_compatible_metadata_and_normalizes_utc(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))

    response = client.post("/api/v1/telemetry/events", json={
        "project_id": project["id"], "service_id": service["id"], "event_type": "request",
        "timestamp": "2026-10-05T12:00:00-07:00", "duration_ms": 142, "status_code": 200,
        "trace_id": "A" * 32, "span_id": "B" * 16, "http_method": "get", "http_route": "/movies/{id}",
    })

    assert response.status_code == 201
    assert response.json()["timestamp"] == "2026-10-05T19:00:00Z"
    assert response.json()["trace_id"] == "a" * 32
    assert response.json()["span_id"] == "b" * 16
    assert response.json()["http_method"] == "GET"


def test_v1_ingestion_rejects_invalid_status_and_naive_timestamp(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    payload = {"project_id": project["id"], "service_id": service["id"], "event_type": "request"}

    invalid_status = client.post("/api/v1/telemetry/events", json={**payload, "status_code": 700})
    naive_timestamp = client.post("/api/v1/telemetry/events", json={**payload, "timestamp": "2026-10-05T12:00:00"})

    assert invalid_status.status_code == 422
    assert naive_timestamp.status_code == 422


def test_v1_batch_ingestion_is_atomic_and_returns_accepted_count(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    valid_event = {"project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 142}
    invalid_event = {"project_id": project["id"], "service_id": "missing", "event_type": "error"}

    failed_response = client.post("/api/v1/telemetry/batch", json={"events": [valid_event, invalid_event]})
    telemetry_after_failure = client.get(f"/api/projects/{project['id']}/telemetry")
    success_response = client.post("/api/v1/telemetry/batch", json={"events": [valid_event, {**valid_event, "event_type": "error"}]})

    assert failed_response.status_code == 404
    assert telemetry_after_failure.json() == []
    assert success_response.status_code == 201
    assert success_response.json() == {"accepted_count": 2}


def test_v1_batch_enforces_size_limit(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    event = {"project_id": project["id"], "service_id": service["id"], "event_type": "request"}

    response = client.post("/api/v1/telemetry/batch", json={"events": [event] * 101})

    assert response.status_code == 422


def test_summary_preserves_two_requests_and_one_error_semantics(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    event = {"project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 142, "status_code": 200}
    client.post("/api/v1/telemetry/batch", json={"events": [event, event, {**event, "event_type": "error", "duration_ms": None}]})

    response = client.get(f"/api/projects/{project['id']}/summary")

    assert response.json() == {"total_requests": 2, "average_latency_ms": 142.0, "error_rate": 33.33, "status": "degraded"}


def test_project_websocket_receives_persisted_ingestion_event(client: TestClient) -> None:
    project = create_project(client)
    service = create_service(client, str(project["id"]))
    payload = {"project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 142}

    with client.websocket_connect(f"/ws/projects/{project['id']}/telemetry") as websocket:
        response = client.post("/api/v1/telemetry/events", json=payload)
        message = websocket.receive_json()

    assert response.status_code == 201
    assert message["type"] == "telemetry.created"
    assert message["project_id"] == project["id"]
    assert message["event"]["id"] == response.json()["id"]


def test_project_websocket_does_not_receive_other_project_events(client: TestClient) -> None:
    class FakeSocket:
        def __init__(self) -> None:
            self.messages: list[dict[str, object]] = []

        async def send_json(self, message: dict[str, object]) -> None:
            self.messages.append(message)

    manager = ProjectConnectionManager()
    first_socket = FakeSocket()
    second_socket = FakeSocket()
    manager._connections["first"].add(first_socket)  # type: ignore[arg-type]
    manager._connections["second"].add(second_socket)  # type: ignore[arg-type]

    asyncio.run(manager.broadcast("second", {"type": "telemetry.created"}))

    assert first_socket.messages == []
    assert second_socket.messages == [{"type": "telemetry.created"}]
