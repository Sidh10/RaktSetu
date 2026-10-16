"""SQLAlchemy engine, session factory and a portable UTC datetime type (ADR-001: SQLite default, Postgres optional)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """Stores naive UTC (SQLite has no time zones), always returns aware UTC. Rejects naive input."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime given to the database; use timezone-aware datetimes")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=timezone.utc)


def make_engine(url: str):
    if url.startswith("sqlite"):
        kw = dict(connect_args={"check_same_thread": False})
        if url in ("sqlite://", "sqlite:///:memory:"):
            kw["poolclass"] = StaticPool
        return create_engine(url, **kw)
    return create_engine(url)


def make_sessionmaker(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine) -> None:
    from app import models  # noqa: F401  (register tables)
    Base.metadata.create_all(engine)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
