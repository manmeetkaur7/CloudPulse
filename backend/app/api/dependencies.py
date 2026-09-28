from fastapi import Request

from app.storage import InMemoryRepository


def get_repository(request: Request) -> InMemoryRepository:
    return request.app.state.repository
