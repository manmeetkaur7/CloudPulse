import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db_models import Base


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
