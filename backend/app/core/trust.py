"""Beta(2,1) reliability per (centre, listing-age bucket 0/1/2+). No decay, no half-life: every outcome counts
equally (MODEL_SPEC_v3.md section 5). This is the public-finder reliability (alpha_f, beta_f); the prototype
learns from confirmations only (ADR-012). Ported from `attempt()` and the family block of raktsetu_sim_v3.py.
Parity: P-08 (daily ftrust trajectories).
"""
from __future__ import annotations

PRIOR_ALPHA = 2.0
PRIOR_BETA = 1.0
N_BUCKETS = 3


def estimate(alpha: float, beta: float) -> float:
    """Point estimate p = alpha / (alpha + beta)."""
    return alpha / (alpha + beta)


def after_confirmation(alpha: float, beta: float, requested: int, found: int) -> tuple[float, float]:
    """A confirmation found `found` of `requested` listed units: alpha += found, beta += requested - found."""
    if requested < 0 or not 0 <= found <= requested:
        raise ValueError(f"need 0 <= found <= requested, got found={found}, requested={requested}")
    return alpha + found, beta + (requested - found)


def after_visit(alpha: float, beta: float, success: bool) -> tuple[float, float]:
    """Simulator only: a family visit found stock (alpha += 1) or not (beta += 1). Unused by the prototype."""
    return (alpha + 1, beta) if success else (alpha, beta + 1)
