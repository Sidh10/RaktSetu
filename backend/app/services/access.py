"""Demo identity and role checks (ADR-004). NOT real authentication: anyone can claim any demo user."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.errors import forbidden

COORDINATOR, STAFF, MO, PUBLIC = "coordinator", "centre_staff", "medical_officer", "public"
CENTRE_ROLES = (STAFF, MO)


@dataclass(frozen=True)
class Actor:
    user_id: str | None
    role: str
    centre_id: str | None = None


PUBLIC_ACTOR = Actor(None, PUBLIC)


def require_role(actor: Actor, *roles: str) -> None:
    if actor.role not in roles:
        raise forbidden("forbidden_role", f"role {actor.role} may not do this; needs {' or '.join(roles)}")


def require_centre_member(actor: Actor, centre_id: str, roles=CENTRE_ROLES) -> None:
    """Staff/MO acting for their own centre only."""
    require_role(actor, *roles)
    if actor.centre_id != centre_id:
        raise forbidden("not_your_centre", f"user belongs to {actor.centre_id}, not {centre_id}")
