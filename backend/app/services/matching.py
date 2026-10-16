"""Match run: open shortfalls x listed near-expiry surplus -> `suggested` transfers (FR-M1..M6).

Uses core.matcher.greedy_match (parity-tested against the simulator). The attempt callback is the prototype's: it
plans without calling anyone (deviation S-05) and drops units that would arrive with less than the 12-h margin,
assuming the simulator's mean 15-min confirmation delay (ASSUMPTION) and the seeded transport time.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.core import groups, margin, matcher
from app.models import MatchRun, Shortfall, Transfer, User
from app.services import audit, shortfalls as sf, stock
from app.services.access import COORDINATOR, MO, Actor, require_role
from app.services.errors import bad_request

IDENTICAL_KEY_OFFSET = 8   # identical-only needs use group key g + 8, whose tier map is {g: 0}


def _tier_of(policy: str) -> dict[int, dict[int, int]]:
    tiers = groups.tier_map(policy)
    for g in range(8):
        tiers[g + IDENTICAL_KEY_OFFSET] = {g: 0}
    return tiers


def run(session: Session, actor: Actor, policy: str, now: datetime, settings: Settings,
        acknowledged_by: str | None = None) -> dict:
    require_role(actor, COORDINATOR)
    if policy not in groups.POLICIES:
        raise bad_request("validation_error", f"policy must be one of {groups.POLICIES}")
    if policy != "strict":
        mo = session.get(User, acknowledged_by) if acknowledged_by else None
        if mo is None or mo.role != MO:
            raise bad_request("acknowledgement_required",
                              f"policy {policy!r} needs a medical officer's acknowledgement (acknowledged_by)")
    tz = settings.tz
    cs = stock.centres(session)
    index = {c.id: n for n, c in enumerate(cs)}
    tiers = _tier_of(policy)
    pending = stock.pending_qty(session)
    open_sf = sf.listing(session, status="open")

    run_row = MatchRun(run_at=now, run_by=actor.user_id, policy=policy, acknowledged_by=acknowledged_by,
                       inputs_digest="", n_suggested=0, notes=[])
    session.add(run_row)
    session.flush()
    created, notes, unmatched, digest_in = [], [], [], []

    for comp in stock.COMPONENTS:
        need_by_key: dict[tuple[int, int], int] = defaultdict(int)
        sf_by_key: dict[tuple[int, int], list[Shortfall]] = defaultdict(list)
        for s in open_sf:
            if s.component != comp or s.count_open <= 0:
                continue
            key = (index[s.centre_id], groups.group_index(s.abo_rh) + (IDENTICAL_KEY_OFFSET if s.identical_only else 0))
            need_by_key[key] += s.count_open
            sf_by_key[key].append(s)
        if not need_by_key:
            continue
        units_by_centre = {c.id: stock.listed_units(session, now, c.id, comp) for c in cs}
        cand: dict[tuple[int, int], list] = {}
        offers: dict[tuple[int, int], int] = {}
        for i, c in enumerate(cs):
            for h in range(8):
                units = stock.offerable_units(units_by_centre[c.id], c, h, now, tz)
                units = units[pending.get((c.id, groups.GROUPS[h], comp), 0):]
                if units:
                    cand[(i, h)] = units
                    offers[(i, h)] = len(units)
        needs = [[n, j, gk] for (j, gk), n in need_by_key.items()]
        digest_in.append(dict(component=comp, needs=sorted(needs), offers=sorted([list(k), v] for k, v in offers.items())))
        allocations = []
        current = {}

        def attempt(key, j, need):
            i, h = key
            req = min(need, offers[key])
            tt = stock.transport_minutes(session, cs[i].id, cs[j].id, settings.default_transport_min)
            ok = [u for u in cand[key] if margin.passes_margin(u.expires_at, now, margin.ASSUMED_CONFIRM_MIN, tt,
                                                               settings.margin_hours)]
            found = min(req, len(ok))
            blocked = min(req, len(cand[key])) - found
            if blocked:
                notes.append(f"{blocked} x {groups.GROUPS[h]} at {cs[i].name} not offered to {cs[j].name}: "
                             f"would arrive with under {settings.margin_hours:g} h left "
                             f"({tt:g} min transport, team-chosen margin)")
            if found:
                taken = set(id(u) for u in ok[:found])
                cand[key] = [u for u in cand[key] if id(u) not in taken]
                offers[key] -= found
                allocations.append((i, h, current["key"], found))
            return found

        # One need at a time in the matcher's own order: identical to a single greedy_match call (needs are
        # processed sequentially over shared offers) but lets each allocation know which need it serves.
        for need in sorted(needs, reverse=True):
            current["key"] = (need[1], need[2])
            matcher.greedy_match([need], offers, tiers, attempt)

        remaining = dict(need_by_key)
        for i, h, nkey, qty in allocations:
            remaining[nkey] -= qty
            take = qty
            for s in sf_by_key[nkey]:
                part = min(take, s.count_open)
                if part > 0:
                    take -= part
                    created.append(_new_transfer(session, actor, run_row, policy, cs[i], cs[nkey[0]], s, h,
                                                 tiers[nkey[1]][h], part, comp, now, settings, tz))
        for (j, gk), n in remaining.items():
            if n > 0:
                g = gk % IDENTICAL_KEY_OFFSET
                pol = "strict (identical only)" if gk >= IDENTICAL_KEY_OFFSET else policy
                unmatched.append(dict(centre=cs[j].id, abo_rh=groups.GROUPS[g], component=comp, open=n,
                                      why=f"no offerable {groups.GROUPS[g]} {comp} unit under {pol} policy "
                                          "that can arrive with the 12-h margin"))

    run_row.notes = sorted(set(notes))
    run_row.n_suggested = len(created)
    run_row.inputs_digest = hashlib.sha256(json.dumps(digest_in, sort_keys=True).encode()).hexdigest()
    audit.record(session, actor, now, "match_run", run_row.id, "create",
                 note=f"policy={policy}; {len(created)} suggested; {len(unmatched)} needs unmatched")
    session.flush()
    return dict(match_run=run_row, transfers=created, unmatched=unmatched, notes=run_row.notes)


def _new_transfer(session, actor, run_row, policy, donor, recipient, s, h, tier, qty, comp, now, settings, tz):
    g = groups.group_index(s.abo_rh)
    bucket = stock.listing_bucket(donor, now, tz)
    band = stock.current_band(session, donor, now, tz)
    tt = stock.transport_minutes(session, donor.id, recipient.id, settings.default_transport_min)
    age = {0: "updated today", 1: "updated yesterday", 2: "updated 2+ days ago"}[bucket]
    kind = "Identical group" if tier == 0 else f"Non-identical (tier {tier}, {policy} policy)"
    reason = (f"{recipient.name} requested {s.count_requested} {s.abo_rh} {comp}. {donor.name} lists {qty} "
              f"{groups.GROUPS[h]} unit(s) expiring within 2 days beyond its own expected use. {kind}. "
              f"Listing {age}; report trust {band}. Transport estimate {tt:g} min.")
    if groups.is_anti_d(g, h):
        reason += " RhD+ unit for an RhD- need: anti-D consideration."
    t = Transfer(match_run_id=run_row.id, shortfall_id=s.id, from_centre=donor.id, to_centre=recipient.id,
                 component=comp, abo_rh_needed=s.abo_rh, abo_rh_offered=groups.GROUPS[h], tier=tier, policy=policy,
                 anti_d_flag=groups.is_anti_d(g, h), qty_requested=qty, listing_bucket=bucket, transport_min=tt,
                 reason=reason, status="suggested", created_at=now, updated_at=now)
    session.add(t)
    s.count_open -= qty
    sf.refresh_status(session, s)
    session.flush()
    audit.record(session, actor, now, "transfer", t.id, "transition", None, "suggested",
                 note=f"match run {run_row.id}: {donor.id} -> {recipient.id} {qty} x {t.abo_rh_offered}")
    return t
