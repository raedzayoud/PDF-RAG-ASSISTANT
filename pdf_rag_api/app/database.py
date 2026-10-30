"""Create the PostgreSQL engine and provide short-lived database sessions."""

from collections.abc import Generator  # Type the database dependency used by FastAPI.

from sqlalchemy import create_engine  # Manage pooled connections to PostgreSQL.
from sqlalchemy.orm import Session, sessionmaker  # Create one ORM session per API request.

from app.config import Settings  # Read the database URL from the project's .env file.
from app.db_models import Base  # Metadata containing the ORM table definitions.

# A small immutable settings object provides the connection URL.
settings = Settings()

# pool_pre_ping checks whether a pooled connection is still alive before using it.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# The factory creates a separate database session for each request that needs one.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables() -> None:
    """Create missing tables for this learning project; use migrations in production."""
    Base.metadata.create_all(bind=engine)  # Create chat_sessions and chat_messages if missing.


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it when the request finishes."""
    db = SessionLocal()  # Open this request's database unit of work.
    try:
        yield db  # FastAPI injects the session into an endpoint that depends on get_db.
    finally:
        db.close()  # Return its connection to the pool, even when an error occurs.
