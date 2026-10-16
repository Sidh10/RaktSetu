"""Append-only audit log: who, which role, what, from -> to, when, why."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.services.access import Actor


def record(session: Session, actor: Actor, at: datetime, entity: str, entity_id, action: str,
           from_state: str | None = None, to_state: str | None = None, note: str = "") -> AuditEvent:
    ev = AuditEvent(at=at, actor_id=actor.user_id, actor_role=actor.role, entity=entity, entity_id=str(entity_id),
                    action=action, from_state=from_state, to_state=to_state, note=note)
    session.add(ev)
    return ev


def history(session: Session, entity: str | None = None, entity_id=None, limit: int = 200) -> list[AuditEvent]:
    q = select(AuditEvent)
    if entity:
        q = q.where(AuditEvent.entity == entity)
    if entity_id is not None:
        q = q.where(AuditEvent.entity_id == str(entity_id))
    return list(session.scalars(q.order_by(AuditEvent.at, AuditEvent.id).limit(limit)))
