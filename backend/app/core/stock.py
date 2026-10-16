"""Near-expiry surplus, par levels, listed-stock ageing and listing age.

Ported from sim_v3/raktsetu_sim_v3.py (`surplus_near`, `apportion`, `Centre.own_offerable`, `Centre.view`).
Parity tests: P-03, P-04, P-05. Units are (r, received_flag, group) with r = remaining usable days.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Iterable, Sequence

SHELF = 5   # days a platelet unit is usable (MODEL_SPEC_v3.md section 1)
NEAR = 2    # near-expiry: r <= NEAR (docs/MATCHING_POLICY.md section 3, ADR-010)
PAR_FACTOR = 1.2


def surplus_near(rems: Sequence[int], dmean: float) -> list[int]:
    """Near-expiry units beyond expected own use. `rems` sorted oldest-first; unit k is surplus if k >= dmean*r."""
    out = []
    for k, r in enumerate(rems):
        if r <= NEAR and k >= dmean * r:
            out.append(r)
    return out


def own_offerable(units: Iterable[Sequence], g: int, dmean_g: float) -> list[int]:
    """Remaining lives of the units a centre can offer in group g (oldest first).

    Only near-expiry units that were not received by transfer (one-hop rule), capped by the surplus count.
    `dmean_g` is the centre's expected daily use of group g (d_bar * w_g).
    """
    units = list(units)
    rems = sorted(r for r, f, gg in units if gg == g)
    sur = surplus_near(rems, dmean_g)
    nonrec = sorted(r for r, f, gg in units if not f and gg == g)
    avail = [r for r in nonrec if r <= NEAR]
    return sorted(avail)[:len(sur)]


def apportion(total: int, w: Sequence[float]) -> list[int]:
    """Largest-remainder split of an integer total by shares w (ties -> lower index)."""
    q = [float(x) * total for x in w]
    base = [math.floor(x) for x in q]
    rem = total - sum(base)
    order = sorted(range(len(w)), key=lambda x: (-(q[x] - base[x]), x))
    for x in order[:rem]:
        base[x] += 1
    return base


def par_levels(dmean: float, shares: Sequence[float]) -> list[int]:
    """Par per group: ceil(1.2 * d_bar) apportioned by demand shares (MODEL_SPEC_v3.md section 4)."""
    return apportion(math.ceil(PAR_FACTOR * dmean), shares)


def needs_from_par(par: Sequence[int], stock_by_group: Sequence[int]) -> list[int]:
    return [max(0, p - s) for p, s in zip(par, stock_by_group)]


def listed_view(snap: Iterable[tuple[int, int]], snap_day: int | None, day: int,
                out_since: Sequence[int], ng: int) -> list[list[int]]:
    """Listed remaining lives by group as seen on `day`: last snapshot aged by days since the post,
    minus the oldest units the platform moved out since that post. snap_day None = never posted."""
    out = [[] for _ in range(ng)]
    if snap_day is None:
        return out
    age = day - snap_day
    for r, g in snap:
        if r - age > 0:
            out[g].append(r - age)
    for g in range(ng):
        out[g].sort()
        if out_since[g]:
            out[g] = out[g][out_since[g]:]
    return out


def staleness_bucket(days_since_post: int | None) -> int:
    """Listing-age bucket 0 / 1 / 2+ (capped at 2). Never posted counts as 2."""
    if days_since_post is None:
        return 2
    return min(2, days_since_post)


def remaining_days(expiry_date: date, today: date) -> int:
    """Simulator-style remaining life r for a unit usable through the end of `expiry_date` (local time).

    r = 1 means it expires tonight. r <= 0 means expired. ADR-010 / MATCHING_POLICY.md section 3.
    """
    return (expiry_date - today).days + 1
