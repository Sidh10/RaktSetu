"""Greedy matcher (the one behind every reported simulator result; MODEL_SPEC_v3.md section 4).

Needs are processed in descending (need, centre, group) order. For each need, candidate (donor, donor-group) offers
are taken in policy-tier order, then by offered count descending (stable by insertion order = centre index); a
centre never supplies itself. Ported from the `matcher == "greedy"` block of `run()` in raktsetu_sim_v3.py.
Parity: P-08 (whole-run replay). No objective is optimised; it is a heuristic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

OfferKey = tuple[int, int]                      # (donor centre, donor group)
Attempt = Callable[[OfferKey, int, int], int]   # (key, recipient centre, need) -> units moved


def candidate_order(offers: dict[OfferKey, int], tiers: dict[int, int]) -> list[OfferKey]:
    """Offers whose donor group is acceptable, by (tier, -offered). `offers` must be in centre-index order."""
    cand = [x for x in offers if x[1] in tiers]
    cand.sort(key=lambda x: (tiers[x[1]], -offers[x]))
    return cand


def greedy_match(needs: list, offers: dict[OfferKey, int], tier_of: dict[int, dict[int, int]],
                 attempt: Attempt) -> None:
    """Run the greedy loop. `needs` is a list of [need, centre, group]; `attempt` may mutate `offers`
    (a confirmation in the simulator refreshes them) and returns the units it moved."""
    for need, j, g in sorted(needs, reverse=True):
        for key in candidate_order(offers, tier_of[g]):
            if need <= 0:
                break
            if key[0] == j or offers[key] <= 0:
                continue
            need -= attempt(key, j, need)


@dataclass(frozen=True)
class Allocation:
    donor: int
    donor_group: int
    recipient: int
    recipient_group: int
    tier: int
    qty: int


def plan(needs: list, offers: dict[OfferKey, int], tier_of: dict[int, dict[int, int]]) -> list[Allocation]:
    """Suggestions for the prototype: the same greedy loop, assuming every request succeeds in full
    (deviation S-05: confirmations happen later; the coordinator re-runs after a shortfall)."""
    offers = dict(offers)
    out: list[Allocation] = []
    for need, j, g in sorted(needs, reverse=True):
        for key in candidate_order(offers, tier_of[g]):
            if need <= 0:
                break
            if key[0] == j or offers[key] <= 0:
                continue
            req = min(need, offers[key])
            offers[key] -= req
            need -= req
            out.append(Allocation(key[0], key[1], j, g, tier_of[g][key[1]], req))
    return out
