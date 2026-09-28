from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.repositories import SqlAlchemyRepository


def get_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_repository(session: Session = Depends(get_session)) -> SqlAlchemyRepository:
    return SqlAlchemyRepository(session)
