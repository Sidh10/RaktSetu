"""12-hour on-arrival margin. TEAM-CHOSEN safety margin, not a regulation
(sim_v3/PREREGISTRATION_v3.md, Amendment 2). Ported from the rule12 branch of `attempt()` in raktsetu_sim_v3.py.
Parity: covered by P-08 (blocked_12h counts); P-07 checks the two forms below agree at 09:00.
"""
from __future__ import annotations

from datetime import datetime, timedelta

MARGIN_HOURS = 12.0
DECISION_HOUR = 9                # simulator decides transfers at 09:00 (PREREGISTRATION_v3.md section 3.4)
ASSUMED_CONFIRM_MIN = 15.0       # ASSUMPTION: simulator's mean confirmation delay
DEFAULT_TRANSPORT_MIN = 90.0     # ASSUMPTION: simulator's base transport time


def hours_left_at_decision(r: int) -> int:
    """Hours left at 09:00 for a unit with remaining life r (expires 24:00 of its last usable day)."""
    return 15 + 24 * (r - 1)


def passes_margin_days(r: int, tconf_min: float, transport_min: float, margin_h: float = MARGIN_HOURS) -> bool:
    """Simulator form: 15 + 24(r-1) - (T_c + T_t)/60 >= margin."""
    lim = (tconf_min + transport_min) / 60.0
    return hours_left_at_decision(r) - lim >= margin_h


def hours_left_on_arrival(expires_at: datetime, now: datetime, tconf_min: float, transport_min: float) -> float:
    arrival = now + timedelta(minutes=tconf_min + transport_min)
    return (expires_at - arrival).total_seconds() / 3600.0


def passes_margin(expires_at: datetime, now: datetime, tconf_min: float, transport_min: float,
                  margin_h: float = MARGIN_HOURS) -> bool:
    """Prototype form on real timestamps. Both datetimes must be timezone-aware."""
    if expires_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("expires_at and now must be timezone-aware")
    return hours_left_on_arrival(expires_at, now, tconf_min, transport_min) >= margin_h
