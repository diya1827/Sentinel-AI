"""Database engine and session management (SQLModel).

Defaults to a local SQLite file so the app runs with zero external setup; set
`DATABASE_URL` to a Postgres URL in production. The engine is a process-wide
singleton; `get_session` is the FastAPI dependency handlers use, and `init_db`
creates the tables on startup.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlmodel import Session, SQLModel, create_engine

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_engine() -> Any:
    """Build (once) the SQLModel engine from `DATABASE_URL`."""
    url = get_settings().database_url
    # SQLite needs this to be usable across threads (FastAPI's threadpool).
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def init_db() -> None:
    """Create all tables. Importing the models registers them on the metadata."""
    from app.models import auth_token, user  # noqa: F401 — registers tables

    SQLModel.metadata.create_all(get_engine())
    logger.info("Database initialized (%s)", get_settings().database_url.split("://")[0])


def get_session() -> Iterator[Session]:
    """Yield a DB session scoped to one request; closed automatically."""
    with Session(get_engine()) as session:
        yield session
