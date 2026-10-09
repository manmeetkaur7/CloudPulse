from collections.abc import Awaitable, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db_models import Base
from app.main import create_app
from app.repositories import SqlAlchemyRepository


class FakeRedisService:
    def __init__(self, status: str = "connected", fail: bool = False) -> None:
        self._status, self.fail = status, fail
        self.cache: dict[str, dict[str, object]] = {}
        self.published: list[tuple[str, dict[str, object]]] = []
        self.invalidated: list[str] = []
        self.ttls: list[int] = []

    @property
    def status(self) -> str:
        return self._status

    async def start(self, _: Callable[[dict[str, object]], Awaitable[None]]) -> None: pass
    async def stop(self) -> None: pass
    async def publish(self, project_id: str, message: dict[str, object]) -> bool:
        if self.fail: return False
        self.published.append((project_id, message)); return True
    async def get_summary(self, project_id: str) -> dict[str, object] | None:
        return None if self.fail else self.cache.get(project_id)
    async def set_summary(self, project_id: str, summary: dict[str, object]) -> None:
        if not self.fail: self.cache[project_id] = summary; self.ttls.append(45)
    async def invalidate_summary(self, project_id: str) -> None:
        if not self.fail: self.cache.pop(project_id, None); self.invalidated.append(project_id)


@pytest.fixture
def redis_client() -> tuple[TestClient, FakeRedisService]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    fake = FakeRedisService()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    with TestClient(create_app(factory, fake)) as client:
        yield client, fake
    engine.dispose()


def seed(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    project = client.post("/api/projects", json={"name": "Redis"}).json()
    service = client.post(f"/api/projects/{project['id']}/services", json={"name": "api", "environment": "test"}).json()
    return project, service


def test_single_ingestion_publishes_and_invalidates(redis_client: tuple[TestClient, FakeRedisService]) -> None:
    client, fake = redis_client; project, service = seed(client)
    fake.cache[str(project["id"])] = {"total_requests": 0, "average_latency_ms": 0, "error_rate": 0, "status": "healthy"}
    response = client.post("/api/v1/telemetry/events", json={"project_id": project["id"], "service_id": service["id"], "event_type": "request"})
    assert response.status_code == 201
    assert fake.invalidated == [project["id"]]
    assert fake.published[0][0] == project["id"]
    assert fake.published[0][1]["type"] == "telemetry.created"


def test_publish_failure_keeps_persisted_event_and_uses_local_fallback(redis_client: tuple[TestClient, FakeRedisService]) -> None:
    client, fake = redis_client; fake.fail = True; project, service = seed(client)
    response = client.post("/api/v1/telemetry/events", json={"project_id": project["id"], "service_id": service["id"], "event_type": "request"})
    assert response.status_code == 201
    assert len(client.get(f"/api/projects/{project['id']}/telemetry").json()) == 1


def test_batch_failure_publishes_nothing_and_success_publishes_after_commit(redis_client: tuple[TestClient, FakeRedisService]) -> None:
    client, fake = redis_client; project, service = seed(client)
    event = {"project_id": project["id"], "service_id": service["id"], "event_type": "request"}
    assert client.post("/api/v1/telemetry/batch", json={"events": [event, {**event, "service_id": "missing"}]}).status_code == 404
    assert fake.published == []
    assert client.post("/api/v1/telemetry/batch", json={"events": [event, {**event, "event_type": "error"}]}).status_code == 201
    assert len(fake.published) == 2 and fake.invalidated == [project["id"], project["id"]]


def test_summary_cache_hit_miss_ttl_and_failure_fallback(redis_client: tuple[TestClient, FakeRedisService], monkeypatch: pytest.MonkeyPatch) -> None:
    client, fake = redis_client; project, service = seed(client)
    client.post("/api/v1/telemetry/events", json={"project_id": project["id"], "service_id": service["id"], "event_type": "request", "duration_ms": 10})
    first = client.get(f"/api/projects/{project['id']}/summary")
    assert first.status_code == 200 and fake.ttls == [45]
    monkeypatch.setattr(SqlAlchemyRepository, "list_project_events", lambda *_: (_ for _ in ()).throw(AssertionError("cache miss")))
    assert client.get(f"/api/projects/{project['id']}/summary").json() == first.json()


@pytest.mark.parametrize("status", ["connected", "unavailable", "not_configured"])
def test_readiness_reports_redis_status(status: str) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    fake = FakeRedisService(status=status)
    with TestClient(create_app(sessionmaker(bind=engine, class_=Session), fake)) as client:
        assert client.get("/health/ready").json()["redis"] == status
