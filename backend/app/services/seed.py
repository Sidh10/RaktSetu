"""Load the fictional demo city (data/seed/demo_city.json). Wipes every table first. SIMULATED DATA only."""
from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core import groups, trust
from app.db import Base
from app.models import Centre, Shortfall, StockPost, TransportEstimate, TrustCounter, Unit, User
from app.services import audit, clock
from app.services.access import Actor

SEED_FILE = Path(__file__).resolve().parents[3] / "data" / "seed" / "demo_city.json"
SEED_ACTOR = Actor("seed", "system")


def default_anchor(real_now: datetime, tz: ZoneInfo, local_time: str = "09:00") -> datetime:
    hh, mm = (int(x) for x in local_time.split(":"))
    return datetime.combine(real_now.astimezone(tz).date(), time(hh, mm), tzinfo=tz)


def wipe(session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())


def load(session: Session, real_now: datetime, tz: ZoneInfo, anchor: datetime | None = None,
         path: Path = SEED_FILE) -> datetime:
    data = json.loads(path.read_text(encoding="utf-8"))
    anchor = anchor or default_anchor(real_now, tz, data["meta"]["anchor_local_time"])
    today = anchor.astimezone(tz).date()
    wipe(session)
    for c in data["centres"]:
        session.add(Centre(id=c["id"], name=c["name"], kind=c["kind"], area=c["area"], public_phone=c["phone"],
                           mock_sender=c.get("mock_sender"),
                           daily_demand_mean=c["daily_demand_mean"], group_demand_shares=list(groups.DIST_WEST),
                           is_simulated=True))
    session.flush()
    for u in data["users"]:
        session.add(User(**u))
    ids = [c["id"] for c in data["centres"]]
    for o in data["transport_overrides"]:
        for a in (ids if o["from"] == "*" else [o["from"]]):
            for b in (ids if o["to"] == "*" else [o["to"]]):
                if a != b:
                    session.merge(TransportEstimate(from_centre=a, to_centre=b, minutes=o["minutes"]))
    for cid, buckets in data["trust_seed"].items():
        for b, (s_, f_) in enumerate(buckets):
            session.add(TrustCounter(centre_id=cid, bucket=b, alpha=trust.PRIOR_ALPHA + s_,
                                     beta=trust.PRIOR_BETA + f_, seeded_alpha=s_, seeded_beta=f_))

    def expiry(r: int) -> datetime:
        return clock.end_of_local_day(today + timedelta(days=r - 1), tz)

    for cid, spec in data["stock"].items():
        posted_at = anchor - timedelta(days=spec["posted_days_ago"], hours=1)
        post = StockPost(centre_id=cid, posted_at=posted_at, posted_by=None, source="seed",
                         unit_count=sum(n for *_, n in spec["units"]))
        session.add(post)
        session.flush()
        for g, comp, r, n in spec["units"]:
            for _ in range(n):
                session.add(Unit(centre_id=cid, stock_post_id=post.id, component=comp, abo_rh=g, expires_at=expiry(r)))
        for g, comp, r, n in spec.get("received_units", []):
            for _ in range(n):
                session.add(Unit(centre_id=cid, component=comp, abo_rh=g, expires_at=expiry(r),
                                 received_via_transfer=True))
        session.get(Centre, cid).last_post_at = posted_at
    for s in data["shortfalls"]:
        session.add(Shortfall(centre_id=s["centre"], abo_rh=s["abo_rh"], component=s["component"],
                              count_requested=s["count"], count_open=s["count"], status="open",
                              created_at=anchor - timedelta(minutes=30), created_by=s["by"]))
    clock.set_anchor(session, anchor, real_now)
    audit.record(session, SEED_ACTOR, anchor, "seed", "demo_city", "create",
                 note=f"fictional demo city loaded; demo clock anchored at {anchor.isoformat()}")
    session.flush()
    return anchor
