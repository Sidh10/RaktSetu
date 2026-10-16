"""Public finder ranking and likelihood bands. The finder shows BANDS, never a probability
(docs/CLAIMS_AND_LIMITS.md section 5). Thresholds from sim_v3/bands_v3.py (dashboard badge thresholds).
Ranking ported from the family-search block of raktsetu_sim_v3.py. Parity: P-10 (bands), P-08 (ranking).
"""
from __future__ import annotations

from dataclasses import dataclass

BANDS = (("Low", 0.0, 0.5), ("Medium", 0.5, 0.8), ("High", 0.8, 1.01))
VISIT_TOP_N = 3   # a simulated family visits the top 3 centres


def band(p: float) -> str:
    for name, lo, hi in BANDS:
        if lo <= p < hi:
            return name
    raise ValueError(f"p out of range: {p}")


@dataclass(frozen=True)
class FinderCandidate:
    centre: int          # stable index (ties broken by it, as in the simulator)
    listed: int          # listed compatible units
    p: float             # trust estimate for the centre's current listing-age bucket
    bucket: int


def rank(cands: list[FinderCandidate], mode: str = "trust") -> list[FinderCandidate]:
    """Order by score desc, then centre index. trust: listed * p ; raw: listed. Centres with listed <= 0 dropped."""
    if mode not in ("trust", "raw"):
        raise ValueError(mode)
    keep = [c for c in cands if c.listed > 0]
    return sorted(keep, key=lambda c: (-(c.listed if mode == "raw" else c.listed * c.p), c.centre))
