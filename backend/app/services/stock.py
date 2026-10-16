"""Listed stock: posts, expiry handling, near-expiry offers, listing age, trust lookup.

A stock post replaces the centre's listed units (snapshot semantics, MODEL_SPEC_v3.md section 3). Units received by
transfer are not superseded by a post and are never offered (one-hop rule). Known limitation for Round 2: a centre
cannot remove a received unit except by its expiry.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import finder, groups, stock, trust
from app.models import Centre, StockPost, Transfer, TransportEstimate, TrustCounter, Unit
from app.services import audit
from app.services.access import Actor
from app.services.errors import bad_request, not_found

COMPONENTS = ("RDP", "SDP")
PENDING_STATES = ("suggested", "confirm_requested")


def check_group(abo_rh: str) -> int:
    try:
        return groups.group_index(abo_rh)
    except ValueError:
        raise bad_request("unknown_group", f"unknown ABO/RhD group {abo_rh!r}; use one of {', '.join(groups.GROUPS)}")


def check_component(component: str) -> None:
    if component not in COMPONENTS:
        raise bad_request("validation_error", f"component must be RDP or SDP, got {component!r}")


def get_centre(session: Session, centre_id: str) -> Centre:
    c = session.get(Centre, centre_id)
    if c is None:
        raise not_found("centre", centre_id)
    return c


def centres(session: Session) -> list[Centre]:
    """All centres in stable index order (by id), the matcher's centre index."""
    return list(session.scalars(select(Centre).order_by(Centre.id)))


def expiry_date(u: Unit, tz: ZoneInfo):
    return (u.expires_at.astimezone(tz) - timedelta(microseconds=1)).date()


def remaining_days(u: Unit, now: datetime, tz: ZoneInfo) -> int:
    return stock.remaining_days(expiry_date(u, tz), now.astimezone(tz).date())


def listed_units(session: Session, now: datetime, centre_id: str | None = None,
                 component: str | None = None) -> list[Unit]:
    """Listed, unexpired units (expired units drop out at read time, FR-L7), oldest first."""
    q = select(Unit).where(Unit.status == "listed", Unit.expires_at > now)
    if centre_id:
        q = q.where(Unit.centre_id == centre_id)
    if component:
        q = q.where(Unit.component == component)
    return list(session.scalars(q.order_by(Unit.expires_at, Unit.id)))


def listing_bucket(c: Centre, now: datetime, tz: ZoneInfo) -> int:
    if c.last_post_at is None:
        return stock.staleness_bucket(None)
    days = (now.astimezone(tz).date() - c.last_post_at.astimezone(tz).date()).days
    return stock.staleness_bucket(max(0, days))


def trust_counter(session: Session, centre_id: str, bucket: int) -> TrustCounter:
    tc = session.get(TrustCounter, (centre_id, bucket))
    if tc is None:
        tc = TrustCounter(centre_id=centre_id, bucket=bucket, alpha=trust.PRIOR_ALPHA, beta=trust.PRIOR_BETA)
        session.add(tc)
    return tc


def current_p(session: Session, c: Centre, now: datetime, tz: ZoneInfo) -> tuple[float, int]:
    b = listing_bucket(c, now, tz)
    tc = trust_counter(session, c.id, b)
    return trust.estimate(tc.alpha, tc.beta), b


def current_band(session: Session, c: Centre, now: datetime, tz: ZoneInfo) -> str:
    return finder.band(current_p(session, c, now, tz)[0])


def transport_minutes(session: Session, from_id: str, to_id: str, default: float) -> float:
    te = session.get(TransportEstimate, (from_id, to_id))
    return te.minutes if te else default


def offerable_units(units: list[Unit], c: Centre, g: int, now: datetime, tz: ZoneInfo) -> list[Unit]:
    """The specific units behind core.own_offerable for group g: oldest near-expiry non-received units, capped by
    the centre's surplus beyond its own expected use. `units` = the centre's listed units of one component."""
    tuples = [(remaining_days(u, now, tz), u.received_via_transfer, groups.group_index(u.abo_rh)) for u in units]
    n = len(stock.own_offerable(tuples, g, c.daily_demand_mean * c.group_demand_shares[g]))
    cand = [u for u, (r, f, gg) in zip(units, tuples) if gg == g and not f and r <= stock.NEAR]
    return cand[:n]          # `units` is sorted by expiry, so these are the oldest, as in the simulator


def pending_qty(session: Session) -> dict[tuple[str, str, str], int]:
    """Units promised in suggested / confirm_requested transfers (not yet reserved), by (centre, group, component)."""
    out: dict = defaultdict(int)
    for t in session.scalars(select(Transfer).where(Transfer.status.in_(PENDING_STATES))):
        out[(t.from_centre, t.abo_rh_offered, t.component)] += t.qty_requested
    return out


def _check_items(items: list[dict], now: datetime) -> None:
    for it in items:
        check_group(it["abo_rh"])
        check_component(it["component"])
        if it["expires_at"].tzinfo is None:
            raise bad_request("validation_error", "expires_at must include a time zone")
        if it["expires_at"] <= now:
            raise bad_request("validation_error", f"unit already expired at {it['expires_at'].isoformat()}")


def add_units(session: Session, actor: Actor, centre_id: str, items: list[dict], now: datetime,
              parse_draft_id: int | None = None) -> dict:
    """Add units to the listing without replacing it (a partial update from a message, ADR-015). The centre's
    listing age is NOT refreshed: a partial message does not vouch for the rest of the listing."""
    get_centre(session, centre_id)
    _check_items(items, now)
    post = StockPost(centre_id=centre_id, posted_at=now, posted_by=actor.user_id, source="mock_channel_add",
                     parse_draft_id=parse_draft_id, unit_count=len(items))
    session.add(post)
    session.flush()
    for it in items:
        session.add(Unit(centre_id=centre_id, stock_post_id=post.id, component=it["component"],
                         abo_rh=it["abo_rh"], expires_at=it["expires_at"], received_via_transfer=False))
    audit.record(session, actor, now, "stock_post", post.id, "create",
                 note=f"{centre_id}: {len(items)} units added from a parsed message (listing age unchanged)")
    session.flush()
    return dict(stock_post_id=post.id, listed=len(items), superseded=0)


def post_stock(session: Session, actor: Actor, centre_id: str, items: list[dict], source: str, now: datetime,
               parse_draft_id: int | None = None) -> dict:
    """Replace the centre's listed (non-received) units with `items` [{component, abo_rh, expires_at}]."""
    c = get_centre(session, centre_id)
    _check_items(items, now)
    old = list(session.scalars(select(Unit).where(Unit.centre_id == centre_id, Unit.status == "listed",
                                                  Unit.received_via_transfer.is_(False))))
    for u in old:
        u.status = "superseded"
    post = StockPost(centre_id=centre_id, posted_at=now, posted_by=actor.user_id, source=source,
                     parse_draft_id=parse_draft_id, unit_count=len(items))
    session.add(post)
    session.flush()
    for it in items:
        session.add(Unit(centre_id=centre_id, stock_post_id=post.id, component=it["component"],
                         abo_rh=it["abo_rh"], expires_at=it["expires_at"], received_via_transfer=False))
    c.last_post_at = now
    audit.record(session, actor, now, "stock_post", post.id, "create",
                 note=f"{c.id}: {len(items)} units listed, {len(old)} superseded ({source})")
    session.flush()
    return dict(stock_post_id=post.id, listed=len(items), superseded=len(old))
