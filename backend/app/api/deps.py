"""Request dependencies: settings, DB session, demo clock, demo identity (NOT real authentication, ADR-004)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services import clock
from app.services.access import PUBLIC_ACTOR, Actor
from app.services.errors import bad_request


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request):
    session: Session = request.app.state.sessionmaker()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_real_now() -> datetime:
    return datetime.now(timezone.utc)


def get_now(session: Session = Depends(get_session), real_now: datetime = Depends(get_real_now)) -> datetime:
    return clock.now(session, real_now)


def get_actor(session: Session = Depends(get_session),
              x_demo_user: str | None = Header(default=None)) -> Actor:
    if not x_demo_user:
        return PUBLIC_ACTOR
    u = session.get(User, x_demo_user)
    if u is None:
        raise bad_request("unknown_user", f"no demo user {x_demo_user!r}")
    return Actor(u.id, u.role, u.centre_id)


def if_match_version(if_match: str | None = Header(default=None)) -> int | None:
    if if_match in (None, ""):
        return None
    try:
        return int(if_match.strip('"'))
    except ValueError:
        raise bad_request("validation_error", "If-Match must be the transfer version number")
