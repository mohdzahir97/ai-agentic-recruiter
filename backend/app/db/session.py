"""Engine, session factory and the FastAPI session dependency."""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs `check_same_thread=False` because FastAPI serves requests from a
# thread pool; Postgres needs pre-ping so a connection dropped by the server
# (or by a `docker compose restart`) is replaced instead of raising.
_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=not _is_sqlite,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any missing tables.

    A migration tool would be the right answer for a real deployment; for a
    Phase 1 learning project, `create_all` keeps the setup to one command.
    """
    import app.models  # noqa: F401  # side-effect: registers every mapper

    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
