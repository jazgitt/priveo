from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy.types import TypeDecorator

from app.platform.config import get_settings
from app.platform.errors import ApiError


class Base(DeclarativeBase):
    pass


class UtcDateTime(TypeDecorator):
    """A timestamp that is always timezone-aware UTC in Python.

    SQLite (used by the tests) drops the timezone, so it is put back on read.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            raise ValueError("Timestamps must carry a timezone.")
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def sqlalchemy_url(url: str) -> str:
    """Hosts hand out `postgres://` or `postgresql://`. The driver is psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str) -> Engine:
    url = sqlalchemy_url(url)
    if url.startswith("sqlite"):
        # One shared in-memory connection, for the tests.
        return create_engine(url, poolclass=StaticPool,
                             connect_args={"check_same_thread": False})
    # No pool in the API process: the host (Neon, or RDS Proxy) pools, and a
    # serverless function must not hold connections between requests.
    return create_engine(url, poolclass=NullPool)


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise ApiError("not_configured", "The database is not set up.", 503)
    return make_engine(url)


def get_db() -> Iterator[Session]:
    """One session for each request. Services commit their own changes."""
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
