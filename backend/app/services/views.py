"""Read models: coordinator board, public finder (bands only), trust view."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.core import finder, groups, stock as core_stock, trust
from app.models import Transfer, TrustCounter
from app.services import clock, stock

FINDER_ADVICE = "Call before travelling. Bands are estimates from past confirmations, not a guarantee."
# Simulated, held-out seeds, S1: RaktSetu_simulator_and_prototype/sim_v3/results/finder_bands.json (RESULTS_v3.md 11)
FINDER_BAND_NOTE = ("In simulation, centres in the High band had stock on 87% of visits, Medium 71%, Low 54% "
                    "(simulated; sim_v3/results/finder_bands.json, S1).")


def board(session: Session, now: datetime, settings: Settings) -> dict:
    tz = settings.tz
    rows, near_total = [], 0
    pending = stock.pending_qty(session)
    for c in stock.centres(session):
        units = stock.listed_units(session, now, c.id)
        near = [u for u in units if stock.remaining_days(u, now, tz) <= core_stock.NEAR]
        near_total += len(near)
        offerable = {}
        for comp in stock.COMPONENTS:
            cu = [u for u in units if u.component == comp]
            for h in range(8):
                n = len(stock.offerable_units(cu, c, h, now, tz)) - pending.get((c.id, groups.GROUPS[h], comp), 0)
                if n > 0:
                    offerable[f"{groups.GROUPS[h]} {comp}"] = n
        rows.append(dict(id=c.id, name=c.name, kind=c.kind, area=c.area, listed=len(units), near_expiry=len(near),
                         received=sum(u.received_via_transfer for u in units),
                         last_post_at=c.last_post_at, updated=clock.ago_text(c.last_post_at, now),
                         listing_age_bucket=stock.listing_bucket(c, now, tz),
                         trust_band=stock.current_band(session, c, now, tz), offerable=offerable))
    open_states = ("suggested", "confirm_requested", "confirmed", "approved")
    kpis = dict(
        near_expiry_listed=near_total,
        transfers_awaiting_action=session.scalar(select(func.count()).where(Transfer.status.in_(open_states))) or 0,
        centres_fresh_24h=sum(1 for c in stock.centres(session)
                              if c.last_post_at and now - c.last_post_at < timedelta(hours=24)),
        delivered_7d=session.scalar(select(func.count()).where(Transfer.status == "delivered",
                                                               Transfer.updated_at > now - timedelta(days=7))) or 0)
    return dict(as_of=now, centres=rows, kpis=kpis)


def public_finder(session: Session, abo_rh: str, component: str, now: datetime, settings: Settings) -> dict:
    """Centres listing identical-group units, ranked by listed x trust (core.finder.rank). Writes nothing (FR-F5)."""
    g = stock.check_group(abo_rh)
    stock.check_component(component)
    tz = settings.tz
    cs = stock.centres(session)
    cands, by_index = [], {}
    for n, c in enumerate(cs):
        listed = sum(1 for u in stock.listed_units(session, now, c.id, component) if u.abo_rh == abo_rh)
        b = stock.listing_bucket(c, now, tz)
        tc = session.get(TrustCounter, (c.id, b))
        p = trust.estimate(tc.alpha, tc.beta) if tc else trust.estimate(trust.PRIOR_ALPHA, trust.PRIOR_BETA)
        cands.append(finder.FinderCandidate(n, listed, p, b))
        by_index[n] = c
    results = [dict(centre_name=by_index[x.centre].name, area=by_index[x.centre].area,
                    phone=by_index[x.centre].public_phone, listed_compatible=x.listed,
                    updated=clock.ago_text(by_index[x.centre].last_post_at, now), band=finder.band(x.p))
               for x in finder.rank(cands, "trust")]
    return dict(group=groups.GROUPS[g], component=component, results=results, advice=FINDER_ADVICE,
                band_note=FINDER_BAND_NOTE, labels=["simulated data", "not clinically validated"])


def trust_table(session: Session, now: datetime, settings: Settings, centre_id: str | None = None) -> list[dict]:
    tz = settings.tz
    out = []
    for c in stock.centres(session):
        if centre_id and c.id != centre_id:
            continue
        cur = stock.listing_bucket(c, now, tz)
        for b in range(trust.N_BUCKETS):
            tc = stock.trust_counter(session, c.id, b)
            p = trust.estimate(tc.alpha, tc.beta)
            out.append(dict(centre=c.id, name=c.name, bucket=b, current=b == cur, alpha=tc.alpha, beta=tc.beta,
                            p=round(p, 2), band=finder.band(p), seeded_alpha=tc.seeded_alpha,
                            seeded_beta=tc.seeded_beta, n_confirmations=tc.n_confirmations))
    return out

