"""HTTP routes (docs/API.md). Routes call services only and commit on success."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_actor, get_now, get_session, get_settings, if_match_version
from app.api.schemas import (ConfirmIn, DispatchIn, DraftEditIn, InboundIn, MatchRunIn, NoteIn, ParseIn,
                             ReasonIn, ShortfallIn, StockPostIn)
from app.config import LABELS, Settings
from app.core import margin
from app.models import InboundMessage, Transfer, User
from app.services import audit, clock, inbox, matching, parser, seed, shortfalls, stock, transfers, views
from app.services.access import COORDINATOR, MO, STAFF, Actor, require_centre_member, require_role
from app.services.errors import forbidden, not_found

router = APIRouter(prefix="/api")
INTERNAL = (COORDINATOR, STAFF, MO)


# --- health and demo identity -------------------------------------------------------------------------------
@router.get("/health")
def health(session: Session = Depends(get_session), now: datetime = Depends(get_now),
           settings: Settings = Depends(get_settings)):
    return dict(status="ok", demo_mode=settings.demo_mode, demo_clock=clock.is_demo_clock(session),
                now=now, parser_mode=settings.parser_mode, llm_available=settings.llm_key_present,
                llm_model=settings.llm_model if settings.llm_key_present else None, labels=LABELS)


@router.get("/demo/users")
def demo_users(session: Session = Depends(get_session)):
    users = session.scalars(select(User).order_by(User.role, User.id))
    return [dict(id=u.id, display_name=u.display_name, role=u.role, centre_id=u.centre_id) for u in users]


@router.get("/me")
def me(actor: Actor = Depends(get_actor)):
    return dict(id=actor.user_id, role=actor.role, centre_id=actor.centre_id,
                note="demo user; not real authentication")


# --- centres, board, stock, shortfalls ----------------------------------------------------------------------
@router.get("/centres")
def centres(session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
            now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    return [dict(id=c.id, name=c.name, kind=c.kind, area=c.area, last_post_at=c.last_post_at,
                 listing_age_bucket=stock.listing_bucket(c, now, settings.tz)) for c in stock.centres(session)]


@router.get("/board")
def board(session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
          now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    return dict(views.board(session, now, settings), labels=LABELS)


@router.get("/centres/{centre_id}/units")
def centre_units(centre_id: str, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                 now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    stock.get_centre(session, centre_id)
    return [dict(id=u.id, component=u.component, abo_rh=u.abo_rh, expires_at=u.expires_at,
                 days_left=stock.remaining_days(u, now, settings.tz),
                 hours_left=round((u.expires_at - now).total_seconds() / 3600, 1),
                 received_via_transfer=u.received_via_transfer) for u in stock.listed_units(session, now, centre_id)]


@router.post("/centres/{centre_id}/stock-posts", status_code=201)
def post_stock(centre_id: str, body: StockPostIn, session: Session = Depends(get_session),
               actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
               settings: Settings = Depends(get_settings)):
    require_centre_member(actor, centre_id)
    items = [dict(component=u.component, abo_rh=u.abo_rh,
                  expires_at=u.expires_at or clock.end_of_local_day(u.expires_on, settings.tz)) for u in body.units]
    out = stock.post_stock(session, actor, centre_id, items, "form", now)
    session.commit()
    return out


@router.post("/shortfalls", status_code=201)
def create_shortfall(body: ShortfallIn, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                     now: datetime = Depends(get_now)):
    s = shortfalls.create(session, actor, body.abo_rh, body.component, body.count, now, body.identical_only)
    session.commit()
    return dict(id=s.id, status=s.status, count_open=s.count_open)


@router.get("/shortfalls")
def list_shortfalls(status: str | None = None, session: Session = Depends(get_session),
                    actor: Actor = Depends(get_actor)):
    require_role(actor, *INTERNAL)
    centre = None if actor.role == COORDINATOR else actor.centre_id
    return [dict(id=s.id, centre=s.centre_id, abo_rh=s.abo_rh, component=s.component,
                 identical_only=s.identical_only, count_requested=s.count_requested, count_open=s.count_open,
                 status=s.status, created_at=s.created_at) for s in shortfalls.listing(session, status, centre)]


# --- matching -----------------------------------------------------------------------------------------------
@router.post("/match/run")
def match_run(body: MatchRunIn, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
              now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    out = matching.run(session, actor, body.policy, now, settings, body.acknowledged_by)
    session.commit()
    return dict(match_run_id=out["match_run"].id, policy=body.policy,
                suggested=[_transfer(session, t, now, settings) for t in out["transfers"]],
                unmatched_needs=out["unmatched"], notes=out["notes"])


# --- transfers ----------------------------------------------------------------------------------------------
def _load(session, actor, transfer_id) -> Transfer:
    t = transfers.get(session, transfer_id)
    if actor.role != COORDINATOR and not transfers.visible_to(actor, t):
        raise not_found("transfer", transfer_id)
    return t


def _transfer(session: Session, t: Transfer, now: datetime, settings: Settings) -> dict:
    tz = settings.tz
    donor, recip = stock.get_centre(session, t.from_centre), stock.get_centre(session, t.to_centre)
    units = [dict(id=u.id, expires_at=u.expires_at, status=u.status,
                  hours_left_on_arrival=round(margin.hours_left_on_arrival(u.expires_at, now, 0, t.transport_min), 1))
             for u in transfers.units_of(session, t)]
    return dict(id=t.id, status=t.status, version=t.version, from_centre=t.from_centre, from_name=donor.name,
                to_centre=t.to_centre, to_name=recip.name, component=t.component, abo_rh_needed=t.abo_rh_needed,
                abo_rh_offered=t.abo_rh_offered, tier=t.tier, policy=t.policy, anti_d_flag=t.anti_d_flag,
                qty_requested=t.qty_requested, qty_confirmed=t.qty_confirmed, listing_bucket=t.listing_bucket,
                sender_band=stock.current_band(session, donor, now, tz), transport_min=t.transport_min,
                reason=t.reason, approved_by=t.approved_by, box_validated=t.box_validated, units=units,
                created_at=t.created_at, updated_at=t.updated_at)


@router.get("/transfers")
def list_transfers(status: str | None = None, centre: str | None = None, session: Session = Depends(get_session),
                   actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
                   settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    return [_transfer(session, t, now, settings) for t in transfers.listing(session, actor, status, centre)]


@router.get("/transfers/{transfer_id}")
def get_transfer(transfer_id: int, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                 now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    t = _load(session, actor, transfer_id)
    hist = [dict(at=e.at, actor=e.actor_id, role=e.actor_role, from_state=e.from_state, to_state=e.to_state,
                 note=e.note) for e in audit.history(session, "transfer", t.id)]
    return dict(_transfer(session, t, now, settings), audit=hist)


def _act(session, actor, transfer_id, now, settings, fn, *args, **kw):
    require_role(actor, *INTERNAL)
    t = _load(session, actor, transfer_id)
    extra = fn(session, actor, t, *args, **kw)
    session.commit()
    out = _transfer(session, t, now, settings)
    if isinstance(extra, dict):
        out["result"] = extra
    return out


@router.post("/transfers/{transfer_id}/request-confirmation")
def request_confirmation(transfer_id: int, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                         now: datetime = Depends(get_now), settings: Settings = Depends(get_settings),
                         if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.request_confirmation, now, if_match=if_match)


@router.post("/transfers/{transfer_id}/confirm")
def confirm(transfer_id: int, body: ConfirmIn, session: Session = Depends(get_session),
            actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
            settings: Settings = Depends(get_settings), if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.confirm, body.units_available, now, settings,
                body.note, if_match=if_match)


@router.post("/transfers/{transfer_id}/approve")
def approve(transfer_id: int, body: NoteIn = NoteIn(), session: Session = Depends(get_session),
            actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
            settings: Settings = Depends(get_settings), if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.approve, now, settings, body.note,
                if_match=if_match)


@router.post("/transfers/{transfer_id}/reject")
def reject(transfer_id: int, body: ReasonIn, session: Session = Depends(get_session),
           actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
           settings: Settings = Depends(get_settings), if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.reject, now, body.reason, if_match=if_match)


@router.post("/transfers/{transfer_id}/dispatch")
def dispatch(transfer_id: int, body: DispatchIn = DispatchIn(), session: Session = Depends(get_session),
             actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
             settings: Settings = Depends(get_settings), if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.dispatch, now, settings, body.box_validated,
                body.transport_min, if_match=if_match)


@router.post("/transfers/{transfer_id}/deliver")
def deliver(transfer_id: int, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
            now: datetime = Depends(get_now), settings: Settings = Depends(get_settings),
            if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.deliver, now, if_match=if_match)


@router.post("/transfers/{transfer_id}/cancel")
def cancel(transfer_id: int, body: ReasonIn, session: Session = Depends(get_session),
           actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
           settings: Settings = Depends(get_settings), if_match: int | None = Depends(if_match_version)):
    return _act(session, actor, transfer_id, now, settings, transfers.cancel, now, body.reason, if_match=if_match)


# --- trust, finder, audit -----------------------------------------------------------------------------------
@router.get("/trust")
def trust_view(session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
               now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    require_role(actor, COORDINATOR, MO)
    rows = views.trust_table(session, now, settings, None if actor.role == COORDINATOR else actor.centre_id)
    return dict(rows=rows, note="Model estimate on simulated history; Beta(2,1) prior per centre and listing age "
                                "(0, 1, 2+ days). Not shown to the public, which sees bands only.")


@router.get("/public/finder")
def public_finder(group: str = Query(...), component: str = "RDP", session: Session = Depends(get_session),
                  now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    return views.public_finder(session, group, component, now, settings)


@router.get("/audit")
def audit_log(entity: str | None = None, entity_id: str | None = None, session: Session = Depends(get_session),
              actor: Actor = Depends(get_actor)):
    require_role(actor, COORDINATOR, MO)
    if actor.role == MO:
        if entity != "transfer" or entity_id is None:
            raise forbidden("forbidden_role", "medical officers can view the audit trail of their own transfers")
        _load(session, actor, int(entity_id))
    return [dict(at=e.at, actor=e.actor_id, role=e.actor_role, entity=e.entity, entity_id=e.entity_id,
                 action=e.action, from_state=e.from_state, to_state=e.to_state, note=e.note)
            for e in audit.history(session, entity, entity_id)]


# --- mock channel and parser inbox (Stage 4) ----------------------------------------------------------------
MOCK_LABELS = ["mock channel", "simulated data", "human check required"]


def _draft(d, m) -> dict:

    return dict(id=d.id, status=d.status, parser=d.parser, model=d.model, channel=m.channel, sender=m.sender,
                centre_id=m.centre_id, received_at=m.received_at, text=m.text, payload=d.payload,
                needs_review=d.payload["needs_review"], blocking=parser.blocking(d.payload), reviewed_by=d.reviewed_by,
                labels=MOCK_LABELS)


@router.get("/channel/samples")
def channel_samples(actor: Actor = Depends(get_actor)):
    require_role(actor, *INTERNAL)

    data = json.loads(seed.SEED_FILE.read_text(encoding="utf-8"))
    return dict(note=data.get("mock_messages_note", ""), samples=data.get("mock_messages", []))


@router.post("/channel/mock/inbound", status_code=201)
def mock_inbound(body: InboundIn, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                 now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    d = inbox.inbound(session, actor, body.channel, body.text, now, settings, body.sender, body.centre_id)
    session.commit()

    return dict(inbound_message_id=d.inbound_message_id, parse_draft_id=d.id, parser=d.parser,
                needs_review=d.payload["needs_review"], draft=_draft(d, session.get(InboundMessage, d.inbound_message_id)),
                labels=MOCK_LABELS)


@router.post("/parser/parse")
def parse_dry_run(body: ParseIn, actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
                  settings: Settings = Depends(get_settings)):
    require_role(actor, *INTERNAL)
    return dict(payload=parser.parse_message(body.text, body.centre_id, now, settings, body.mode), saved=False)


@router.get("/parser/drafts")
def list_drafts(status: str | None = None, session: Session = Depends(get_session), actor: Actor = Depends(get_actor)):
    return [_draft(d, m) for d, m in inbox.listing(session, actor, status)]


@router.patch("/parser/drafts/{draft_id}")
def edit_draft(draft_id: int, body: DraftEditIn, session: Session = Depends(get_session),
               actor: Actor = Depends(get_actor), now: datetime = Depends(get_now),
               settings: Settings = Depends(get_settings)):
    edits = body.model_dump(exclude_none=True)
    if body.items is not None:
        edits["items"] = [dict(i.model_dump(), expiry_date=i.expiry_date.isoformat() if i.expiry_date else None)
                          for i in body.items]
    d = inbox.review(session, actor, draft_id, edits, now, settings)
    session.commit()

    return _draft(d, session.get(InboundMessage, d.inbound_message_id))


@router.post("/parser/drafts/{draft_id}/commit")
def commit_draft(draft_id: int, session: Session = Depends(get_session), actor: Actor = Depends(get_actor),
                 now: datetime = Depends(get_now), settings: Settings = Depends(get_settings)):
    out = inbox.commit(session, actor, draft_id, now, settings)
    session.commit()
    return out


@router.post("/parser/drafts/{draft_id}/discard")
def discard_draft(draft_id: int, body: ReasonIn, session: Session = Depends(get_session),
                  actor: Actor = Depends(get_actor), now: datetime = Depends(get_now)):
    d = inbox.discard(session, actor, draft_id, body.reason, now)
    session.commit()
    return dict(id=d.id, status=d.status)
