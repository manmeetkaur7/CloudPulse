from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_migration_engine(database_url: str):
    """Create Alembic's engine without passing the URL through ConfigParser."""
    return create_engine(database_url, poolclass=NullPool)


SessionLocal = create_session_factory(get_settings().database_url)
