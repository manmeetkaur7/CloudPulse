from collections import defaultdict

from fastapi import WebSocket


class ProjectConnectionManager:
    """In-process WebSocket subscriptions grouped by monitored project."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[project_id].add(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(project_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(project_id, None)

    async def broadcast(self, project_id: str, message: dict[str, object]) -> None:
        for websocket in list(self._connections.get(project_id, set())):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(project_id, websocket)
