"""Shortfall requests (needs). Group, component and count only: no patient data (FR-L4)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Shortfall, Transfer
from app.services import audit
from app.services.access import COORDINATOR, MO, STAFF, Actor, require_centre_member
from app.services.errors import bad_request
from app.services.stock import check_component, check_group

NON_TERMINAL = ("suggested", "confirm_requested", "confirmed", "approved", "dispatched")


def create(session: Session, actor: Actor, abo_rh: str, component: str, count: int, now: datetime,
           identical_only: bool = False, centre_id: str | None = None) -> Shortfall:
    """Staff/MO post for their own centre. `centre_id` is used when committing a parsed message: the coordinator
    or that centre's own staff may commit it."""
    if centre_id is None:
        require_centre_member(actor, actor.centre_id or "", (STAFF, MO))
        centre_id = actor.centre_id
    elif actor.role != COORDINATOR:
        require_centre_member(actor, centre_id, (STAFF, MO))
    check_group(abo_rh)
    check_component(component)
    if count < 1:
        raise bad_request("validation_error", "count must be at least 1")
    s = Shortfall(centre_id=centre_id, abo_rh=abo_rh, component=component, identical_only=identical_only,
                  count_requested=count, count_open=count, status="open", created_at=now, created_by=actor.user_id)
    session.add(s)
    session.flush()
    audit.record(session, actor, now, "shortfall", s.id, "create", to_state="open",
                 note=f"{s.centre_id} needs {count} x {abo_rh} {component}")
    return s


def listing(session: Session, status: str | None = None, centre_id: str | None = None) -> list[Shortfall]:
    q = select(Shortfall)
    if status:
        q = q.where(Shortfall.status == status)
    if centre_id:
        q = q.where(Shortfall.centre_id == centre_id)
    return list(session.scalars(q.order_by(Shortfall.created_at, Shortfall.id)))


def reopen(session: Session, s: Shortfall, qty: int) -> None:
    """Return `qty` units of need to the shortfall (failed / partial / cancelled transfer, FR-T8)."""
    if qty > 0:
        s.count_open = min(s.count_requested, s.count_open + qty)
    refresh_status(session, s)


def refresh_status(session: Session, s: Shortfall) -> None:
    if s.count_open > 0:
        s.status = "open"
        return
    active = session.scalar(select(Transfer.id).where(Transfer.shortfall_id == s.id,
                                                      Transfer.status.in_(NON_TERMINAL)).limit(1))
    s.status = "covered" if active else "closed"
