from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.repositories import SqlAlchemyRepository

router = APIRouter()


@router.websocket("/ws/projects/{project_id}/telemetry")
async def project_telemetry_socket(websocket: WebSocket, project_id: str) -> None:
    session = websocket.app.state.session_factory()
    try:
        repository = SqlAlchemyRepository(session)
        if repository.get_project(project_id) is None:
            await websocket.close(code=1008, reason="Project not found")
            return
    finally:
        session.close()

    manager = websocket.app.state.connection_manager
    await manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
