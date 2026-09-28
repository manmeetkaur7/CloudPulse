from app.core.database import create_migration_engine


def test_migration_engine_accepts_percent_encoded_database_password() -> None:
    engine = create_migration_engine(
        "postgresql+psycopg://cloudpulse:local%40password@localhost:5432/cloudpulse"
    )

    try:
        assert engine.url.password == "local@password"
    finally:
        engine.dispose()
