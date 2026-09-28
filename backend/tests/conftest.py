import os

# Application imports create the runtime session factory. Tests replace it with
# isolated SQLite sessions, but this keeps module import independent of a local PostgreSQL server.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
