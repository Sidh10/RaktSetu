"""Mock channel and parser inbox (ADR-002, docs/PARSER_SPEC.md). MOCK CHANNEL: messages are typed or pasted, nothing
is received from WhatsApp or SMS. Every draft needs a human check; commit is blocked while blocking flags remain."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Centre, InboundMessage, ParseDraft
from app.services import audit, clock, parser, shortfalls, stock
from app.services.access import COORDINATOR, MO, STAFF, Actor, require_centre_member, require_role
from app.services.errors import bad_request, conflict, forbidden, not_found

CHANNELS = ("mock_whatsapp", "mock_sms", "paste")
REDACTED = "[raw text removed by reviewer: possible patient data]"


def _centre_for_sender(session: Session, sender: str) -> Centre | None:
    return session.scalar(select(Centre).where(Centre.mock_sender == sender))


def inbound(session: Session, actor: Actor, channel: str, text: str, now: datetime, settings: Settings,
            sender: str | None = None, centre_id: str | None = None) -> ParseDraft:
    require_role(actor, COORDINATOR, STAFF, MO)
    if channel not in CHANNELS:
        raise bad_request("validation_error", f"channel must be one of {CHANNELS} (all mock)")
    if not text.strip():
        raise bad_request("validation_error", "empty message")
    if centre_id and not sender:
        sender = stock.get_centre(session, centre_id).mock_sender
    if actor.role != COORDINATOR:            # staff can only send as their own centre
        own = stock.get_centre(session, actor.centre_id).mock_sender
        sender = sender or own
        if sender != own:
            raise forbidden("not_your_centre", "staff can only send messages from their own centre's number")
    centre = _centre_for_sender(session, sender) if sender else None
    msg = InboundMessage(received_at=now, channel=channel, sender=sender or "unknown",
                         centre_id=centre.id if centre else None, text=text)
    session.add(msg)
    session.flush()
    payload = parser.parse_message(text, msg.centre_id, now, settings)
    d = ParseDraft(inbound_message_id=msg.id, parser=payload["parser"], model=payload["model"], payload=payload,
                   needs_review_reasons=payload["needs_review"], status="pending")
    session.add(d)
    session.flush()
    audit.record(session, actor, now, "parse_draft", d.id, "create", to_state="pending",
                 note=f"mock channel {channel} from {msg.sender}; parsed by {d.parser}")
    return d


def _get(session: Session, actor: Actor, draft_id: int) -> tuple[ParseDraft, InboundMessage]:
    require_role(actor, COORDINATOR, STAFF, MO)
    d = session.get(ParseDraft, draft_id)
    if d is None:
        raise not_found("draft", draft_id)
    m = session.get(InboundMessage, d.inbound_message_id)
    if actor.role != COORDINATOR and m.centre_id != actor.centre_id:
        raise not_found("draft", draft_id)
    return d, m


def listing(session: Session, actor: Actor, status: str | None = None) -> list[tuple[ParseDraft, InboundMessage]]:
    require_role(actor, COORDINATOR, STAFF, MO)
    q = select(ParseDraft, InboundMessage).join(InboundMessage, ParseDraft.inbound_message_id == InboundMessage.id)
    if status:
        q = q.where(ParseDraft.status == status)
    if actor.role != COORDINATOR:
        q = q.where(InboundMessage.centre_id == actor.centre_id)
    return list(session.execute(q.order_by(ParseDraft.id.desc())).all())


def review(session: Session, actor: Actor, draft_id: int, edits: dict, now: datetime, settings: Settings) -> ParseDraft:
    d, m = _get(session, actor, draft_id)
    if d.status != "pending":
        raise conflict("illegal_transition", f"draft is {d.status}")
    today = now.astimezone(settings.tz).date()
    try:
        payload = parser.rebuild_after_review(d.payload, edits, today)
    except (ValueError, TypeError) as e:
        raise bad_request("validation_error", f"bad edit: {e}")
    if edits.get("patient_data_redacted"):
        m.text = REDACTED
    d.payload, d.needs_review_reasons, d.reviewed_by = payload, payload["needs_review"], actor.user_id
    audit.record(session, actor, now, "parse_draft", d.id, "review", note="reviewer edited the draft")
    return d


def commit(session: Session, actor: Actor, draft_id: int, now: datetime, settings: Settings) -> dict:
    d, m = _get(session, actor, draft_id)
    if d.status != "pending":
        raise conflict("illegal_transition", f"draft is {d.status}")
    p = d.payload
    block = parser.blocking(p)
    if block:
        raise conflict("needs_review", "fix these before committing: " + ", ".join(block), flags=block)
    if p["message_type"] == "other":
        raise conflict("needs_review", "nothing to commit in an 'other' message; discard it instead")
    centre_id = m.centre_id
    if actor.role != COORDINATOR:
        require_centre_member(actor, centre_id)
    if p["message_type"] == "stock_post":
        items = [dict(component=i["component"], abo_rh=i["abo_rh"],
                      expires_at=clock.end_of_local_day(date.fromisoformat(i["expiry"]["resolved_date"]), settings.tz))
                 for i in p["items"] for _ in range(i["count"])]
        if p.get("commit_mode") == "replace":
            out = stock.post_stock(session, actor, centre_id, items, "mock_channel", now, parse_draft_id=d.id)
        else:
            out = stock.add_units(session, actor, centre_id, items, now, parse_draft_id=d.id)
        result = dict(kind="stock_post", mode=p.get("commit_mode", "add"), **out)
    else:
        ids = [shortfalls.create(session, actor, i["abo_rh"], i["component"], i["count"], now, centre_id=centre_id).id
               for i in p["items"]]
        result = dict(kind="shortfall", shortfall_ids=ids)
    d.status, d.reviewed_by = "committed", actor.user_id
    audit.record(session, actor, now, "parse_draft", d.id, "commit", "pending", "committed", note=str(result))
    return result


def discard(session: Session, actor: Actor, draft_id: int, reason: str, now: datetime) -> ParseDraft:
    d, _ = _get(session, actor, draft_id)
    if d.status != "pending":
        raise conflict("illegal_transition", f"draft is {d.status}")
    if not reason:
        raise bad_request("validation_error", "a reason is required")
    d.status, d.reviewed_by = "discarded", actor.user_id
    audit.record(session, actor, now, "parse_draft", d.id, "discard", "pending", "discarded", note=reason)
    return d
