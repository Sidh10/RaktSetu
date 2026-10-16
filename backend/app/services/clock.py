"""Demo clock. The seed stores an anchor (e.g. today 09:00 IST) and the real time it was seeded; the app's
"now" is anchor + real time elapsed since seeding, so the scripted demo behaves the same at any time of day.
Without an anchor, now is the real time. The UI labels the demo clock as simulated."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Meta

ANCHOR_KEY = "demo_clock_anchor"
REAL_AT_KEY = "demo_clock_real_at"


def set_anchor(session: Session, anchor: datetime, real_at: datetime) -> None:
    for k, v in ((ANCHOR_KEY, anchor), (REAL_AT_KEY, real_at)):
        row = session.get(Meta, k) or Meta(key=k, value="")
        row.value = v.astimezone(timezone.utc).isoformat()
        session.add(row)


def now(session: Session, real_now: datetime) -> datetime:
    a, r = session.get(Meta, ANCHOR_KEY), session.get(Meta, REAL_AT_KEY)
    if a is None or r is None:
        return real_now
    return datetime.fromisoformat(a.value) + (real_now - datetime.fromisoformat(r.value))


def is_demo_clock(session: Session) -> bool:
    return session.get(Meta, ANCHOR_KEY) is not None


def local_today(at: datetime, tz: ZoneInfo) -> date:
    return at.astimezone(tz).date()


def end_of_local_day(d: date, tz: ZoneInfo) -> datetime:
    """Expiry instant for a unit usable through local date d (midnight that ends d), in UTC."""
    return datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc) + timedelta(days=1)


def ago_text(then: datetime | None, at: datetime) -> str:
    if then is None:
        return "never"
    h = int((at - then).total_seconds() // 3600)
    if h < 1:
        return "under 1 h ago"
    return f"{h} h ago" if h < 48 else f"{h // 24} days ago"
