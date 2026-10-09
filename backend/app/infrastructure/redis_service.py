import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisService:
    """Optional Redis cache and cross-instance notification transport."""

    def __init__(self, redis_url: str | None) -> None:
        self.redis_url = redis_url
        self.client: Redis | None = None
        self.available = False
        self._subscriber_task: asyncio.Task[None] | None = None

    @property
    def status(self) -> str:
        return "not_configured" if self.redis_url is None else "connected" if self.available else "unavailable"

    async def start(self, on_message: Callable[[dict[str, object]], Awaitable[None]]) -> None:
        if self.redis_url is None:
            return
        self.client = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            await self.client.ping()
            self.available = True
            self._subscriber_task = asyncio.create_task(self._subscribe(on_message))
        except RedisError:
            logger.warning("Redis unavailable; cache and cross-instance notifications are disabled")
            await self.client.aclose()
            self.client = None

    async def stop(self) -> None:
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.aclose()

    async def _subscribe(self, on_message: Callable[[dict[str, object]], Awaitable[None]]) -> None:
        if self.client is None:
            return
        try:
            pubsub = self.client.pubsub()
            await pubsub.psubscribe("cloudpulse:project:*:telemetry")
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    await on_message(json.loads(message["data"]))
        except (RedisError, json.JSONDecodeError):
            self.available = False
            logger.warning("Redis subscriber stopped; local telemetry delivery remains available")

    async def publish(self, project_id: str, message: dict[str, object]) -> bool:
        if not self.client or not self.available:
            return False
        try:
            await self.client.publish(f"cloudpulse:project:{project_id}:telemetry", json.dumps(message))
            return True
        except RedisError:
            self.available = False
            logger.warning("Redis publish failed; telemetry remains persisted")
            return False

    async def get_summary(self, project_id: str) -> dict[str, object] | None:
        if not self.client or not self.available:
            return None
        try:
            value = await self.client.get(f"cloudpulse:project:{project_id}:summary")
            return json.loads(value) if value else None
        except (RedisError, json.JSONDecodeError):
            return None

    async def set_summary(self, project_id: str, summary: dict[str, object]) -> None:
        if self.client and self.available:
            try:
                await self.client.set(f"cloudpulse:project:{project_id}:summary", json.dumps(summary), ex=45)
            except RedisError:
                pass

    async def invalidate_summary(self, project_id: str) -> None:
        if self.client and self.available:
            try:
                await self.client.delete(f"cloudpulse:project:{project_id}:summary")
            except RedisError:
                pass
