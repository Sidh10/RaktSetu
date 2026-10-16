"""Transfer state machine (docs/DATA_MODEL.md section 3). Every change goes through `_move`, which checks the
transition, bumps the version and writes an audit row. Routes never set `status` directly.

    suggested -> confirm_requested -> confirmed | failed
    confirmed -> approved (medical officer of the sending centre, ADR-009) -> dispatched -> delivered
    any non-terminal -> cancelled
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.core import finder, margin, trust
from app.models import Shortfall, Transfer, TransferUnit, Unit
from app.services import audit, shortfalls as sf, stock
from app.services.access import COORDINATOR, MO, STAFF, Actor, require_centre_member, require_role
from app.services.errors import bad_request, conflict, not_found

ALLOWED = {
    ("suggested", "confirm_requested"), ("suggested", "cancelled"),
    ("confirm_requested", "confirmed"), ("confirm_requested", "failed"), ("confirm_requested", "cancelled"),
    ("confirmed", "approved"), ("confirmed", "cancelled"),
    ("approved", "dispatched"), ("approved", "cancelled"),
    ("dispatched", "delivered"), ("dispatched", "cancelled"),
}
TERMINAL = ("failed", "delivered", "cancelled")


def get(session: Session, transfer_id: int) -> Transfer:
    t = session.get(Transfer, transfer_id)
    if t is None:
        raise not_found("transfer", transfer_id)
    return t


def visible_to(actor: Actor, t: Transfer) -> bool:
    return actor.role == COORDINATOR or actor.centre_id in (t.from_centre, t.to_centre)


def listing(session: Session, actor: Actor, status: str | None = None, centre: str | None = None) -> list[Transfer]:
    q = select(Transfer)
    if status:
        q = q.where(Transfer.status == status)
    if centre:
        q = q.where((Transfer.from_centre == centre) | (Transfer.to_centre == centre))
    return [t for t in session.scalars(q.order_by(Transfer.id)) if visible_to(actor, t)]


def units_of(session: Session, t: Transfer) -> list[Unit]:
    ids = [tu.unit_id for tu in t.units]
    return list(session.scalars(select(Unit).where(Unit.id.in_(ids)).order_by(Unit.expires_at))) if ids else []


def _check(t: Transfer, to: str, if_match: int | None) -> None:
    """Run before any side effect: stale version or illegal transition -> 409, nothing changed."""
    if if_match is not None and if_match != t.version:
        raise conflict("stale_version", f"transfer {t.id} changed (version {t.version}, you had {if_match})")
    if (t.status, to) not in ALLOWED:
        raise conflict("illegal_transition", f"{t.status} -> {to} is not allowed", status=t.status)


def _move(session, actor, t: Transfer, to: str, now: datetime, if_match: int | None, note: str = "") -> None:
    _check(t, to, if_match)
    frm, t.status = t.status, to
    t.version += 1
    t.updated_at = now
    audit.record(session, actor, now, "transfer", t.id, "transition", frm, to, note)


def _sender(actor: Actor, t: Transfer, roles=(STAFF, MO)) -> None:
    require_centre_member(actor, t.from_centre, roles)


def _shortfall(session, t) -> Shortfall:
    return session.get(Shortfall, t.shortfall_id)


def _release(session, t: Transfer, to_status: str = "listed") -> int:
    units = units_of(session, t)
    for u in units:
        u.status = to_status
    return len(units)


def _margin_split(units, now, transport_min, settings, tconf_min=0.0):
    ok = [u for u in units if margin.passes_margin(u.expires_at, now, tconf_min, transport_min, settings.margin_hours)]
    return ok, [u for u in units if u not in ok]


def _recheck_margin(session, t: Transfer, now, settings, transport_min) -> str:
    """Re-check reserved units; drop failing ones (back to listed, need reopened). 409 if none pass."""
    units = units_of(session, t)
    ok, bad = _margin_split(units, now, transport_min, settings)
    if not ok:
        raise conflict("margin_failed", f"no reserved unit would arrive with {settings.margin_hours:g} h left "
                                        f"({transport_min:g} min transport)", units=[u.id for u in units])
    for u in bad:
        u.status = "listed"
        t.units = [tu for tu in t.units if tu.unit_id != u.id]
    if bad:
        t.qty_confirmed = len(ok)
        sf.reopen(session, _shortfall(session, t), len(bad))
        return f"; {len(bad)} unit(s) dropped by the 12-h margin"
    return ""


def request_confirmation(session, actor, t, now, if_match=None):
    require_role(actor, COORDINATOR)
    _move(session, actor, t, "confirm_requested", now, if_match, "coordinator asked the sending centre to confirm")


def confirm(session, actor, t, units_available: int, now, settings: Settings, note: str = "", if_match=None) -> dict:
    """Sending centre reports how many of the requested units physically exist (FR-T2, FR-T3)."""
    _sender(actor, t)
    _check(t, "confirmed", if_match)
    req = t.qty_requested
    if not 0 <= units_available <= req:
        raise bad_request("validation_error", f"units_available must be between 0 and {req}")
    found = units_available
    # trust: the listing bucket recorded at suggestion time; alpha += found, beta += requested - found
    tc = stock.trust_counter(session, t.from_centre, t.listing_bucket)
    band_before = finder.band(trust.estimate(tc.alpha, tc.beta))
    tc.alpha, tc.beta = trust.after_confirmation(tc.alpha, tc.beta, req, found)
    tc.n_confirmations += 1
    band_after = finder.band(trust.estimate(tc.alpha, tc.beta))
    # listing correction (ADR-011): the units this transfer was matched to are the oldest offerable ones
    donor = stock.get_centre(session, t.from_centre)
    comp_units = stock.listed_units(session, now, t.from_centre, t.component)
    listed = [u for u in comp_units if u.abo_rh == t.abo_rh_offered and not u.received_via_transfer][:req]
    missing = max(0, len(listed) - found)
    for u in listed[:missing]:
        u.status = "not_found"
    present = listed[missing:]
    ok, bad = _margin_split(present, now, t.transport_min, settings)
    ok.sort(key=lambda u: u.expires_at, reverse=True)       # most life left first (MODEL_SPEC_v3.md 4, step 4)
    for u in ok:
        u.status = "reserved"
        t.units.append(TransferUnit(transfer_id=t.id, unit_id=u.id))
    t.qty_confirmed = len(ok)
    to = "confirmed" if ok else "failed"
    msg = f"found {found} of {req}; reserved {len(ok)}"
    if bad:
        msg += f"; {len(bad)} would arrive with under {settings.margin_hours:g} h left"
    if note:
        msg += f"; note: {note}"
    _move(session, actor, t, to, now, if_match, msg)
    sf.reopen(session, _shortfall(session, t), req - len(ok))
    session.flush()
    return dict(status=t.status, qty_confirmed=t.qty_confirmed, margin=dict(passed=len(ok), blocked=len(bad)),
                trust=dict(centre=donor.id, bucket=t.listing_bucket, alpha=tc.alpha, beta=tc.beta,
                           band_before=band_before, band_after=band_after))


def approve(session, actor, t, now, settings: Settings, note: str = "", if_match=None):
    _sender(actor, t, roles=(MO,))
    _check(t, "approved", if_match)
    extra = _recheck_margin(session, t, now, settings, t.transport_min)
    t.approved_by = actor.user_id
    _move(session, actor, t, "approved", now, if_match, (note or "approved") + extra)


def reject(session, actor, t, now, reason: str, if_match=None):
    _sender(actor, t, roles=(MO,))
    if t.status != "confirmed":
        raise conflict("illegal_transition", f"only a confirmed transfer can be rejected (is {t.status})")
    _check(t, "cancelled", if_match)
    _cancel(session, actor, t, now, f"rejected by medical officer: {reason}", if_match)


def dispatch(session, actor, t, now, settings: Settings, box_validated: bool, transport_min: float | None = None,
             if_match=None):
    _sender(actor, t)
    _check(t, "dispatched", if_match)
    if not t.approved_by:
        raise conflict("illegal_transition", "no medical-officer approval recorded")
    if transport_min is not None:
        t.transport_min = transport_min
    extra = _recheck_margin(session, t, now, settings, t.transport_min)
    for u in units_of(session, t):
        u.status = "in_transit"
    t.box_validated = box_validated
    _move(session, actor, t, "dispatched", now, if_match,
          f"validated 20-24 C box: {'yes' if box_validated else 'NOT CONFIRMED'} (recorded, not verified){extra}")


def deliver(session, actor, t, now, if_match=None):
    require_centre_member(actor, t.to_centre)
    _check(t, "delivered", if_match)
    for u in units_of(session, t):
        u.centre_id, u.received_via_transfer, u.status = t.to_centre, True, "listed"   # one-hop flag
    _move(session, actor, t, "delivered", now, if_match, f"{t.qty_confirmed} unit(s) received at {t.to_centre}")
    sf.refresh_status(session, _shortfall(session, t))


def cancel(session, actor, t, now, reason: str, if_match=None):
    require_role(actor, COORDINATOR)
    if not reason:
        raise bad_request("validation_error", "a reason is required to cancel")
    _check(t, "cancelled", if_match)
    _cancel(session, actor, t, now, f"cancelled: {reason}", if_match)


def _cancel(session, actor, t, now, note, if_match):
    _check(t, "cancelled", if_match)
    in_transit = t.status == "dispatched"
    open_qty = t.qty_confirmed if t.qty_confirmed is not None else t.qty_requested
    _release(session, t, "not_found" if in_transit else "listed")   # lost/damaged in transit leaves the listing
    _move(session, actor, t, "cancelled", now, if_match, note)
    sf.reopen(session, _shortfall(session, t), open_qty)
