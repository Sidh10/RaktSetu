"""ABO/RhD groups, donor distributions and matching-policy preference lists.

Ported from RaktSetu_simulator_and_prototype/sim_v3/raktsetu_sim_v3.py ("blood groups" section).
Parity tests: P-01 (pref_list), P-02 (distributions). Policy sources: docs/MATCHING_POLICY.md.
NOT clinically validated.
"""
from __future__ import annotations

# group index g = 2*abo + rhneg ; abo: 0=O 1=A 2=B 3=AB ; rhneg: 0=RhD+ 1=RhD-
GROUPS = ("O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-")
ABO_NAMES = ("O", "A", "B", "AB")
POLICIES = ("strict", "standard", "relaxed")


def group_index(name: str) -> int:
    try:
        return GROUPS.index(name)
    except ValueError:
        raise ValueError(f"unknown ABO/RhD group {name!r}") from None


def group_name(g: int) -> str:
    return GROUPS[g]


def abo_rh_distribution(abo_pct, rhneg_pct, rhpos_pct) -> list[float]:
    """Shares of the 8 groups from ABO and RhD marginals, ABO and RhD assumed independent (sim `_dist`)."""
    abo = [float(x) for x in abo_pct]
    total = 0.0
    for x in abo:
        total += x
    abo = [x / total for x in abo]
    rn = rhneg_pct / (rhneg_pct + rhpos_pct)
    w = [0.0] * 8
    for a in range(4):
        w[2 * a] = abo[a] * (1 - rn)
        w[2 * a + 1] = abo[a] * rn
    return w


# Agrawal A et al., Asian J Transfus Sci 2014;8(2):121-5, doi:10.4103/0973-6247.137452, Table 5. Order O, A, B, AB.
DIST_WEST = abo_rh_distribution([36.75, 23.69, 32.74, 6.80], 7.02, 92.97)    # Mumbai blood bank, n=2220
DIST_NORTH = abo_rh_distribution([29.43, 24.53, 34.47, 11.55], 5.19, 94.80)  # Dehradun, n=2042

_ANTIGENS = (frozenset(), frozenset({"A"}), frozenset({"B"}), frozenset({"A", "B"}))
_ANTIBODIES = (frozenset({"A", "B"}), frozenset({"B"}), frozenset({"A"}), frozenset())


def plasma_ok(donor_abo: int, recipient_abo: int) -> bool:
    """Donor plasma compatible with recipient red cells."""
    return not (_ANTIBODIES[donor_abo] & _ANTIGENS[recipient_abo])


# ABO preference orders (SNBTS NATP CLIN 10 003 04 Table 1 / BCSH 2003)
_STD_ABO = {0: [0, 1, 2, 3], 1: [1, 3], 2: [2, 3], 3: [3]}       # identical, then plasma-compatible
_INCOMPAT_ABO = {0: [], 1: [2, 0], 2: [1, 0], 3: [1, 2, 0]}       # relaxed extension, O last


def pref_list(g: int, policy: str) -> list[int]:
    """Ordered donor groups acceptable for recipient group g. Position = tier (0 = identical)."""
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    a, rn = divmod(g, 2)
    if policy == "strict":
        return [g]
    std = _STD_ABO[a]
    if rn == 0:   # RhD+ recipient: all RhD+ options first, RhD- only if no RhD+ fits (conservation)
        out = [2 * x for x in std] + [2 * x + 1 for x in std]
        if policy == "relaxed":
            inc = _INCOMPAT_ABO[a]
            out += [2 * x for x in inc] + [2 * x + 1 for x in inc]
        return out
    out = [2 * x + 1 for x in std]                    # RhD- recipient: RhD- only under standard
    if policy == "relaxed":
        inc = _INCOMPAT_ABO[a]
        out += [2 * x + 1 for x in inc]
        out += [2 * x for x in std + inc]             # RhD+ last -> anti-D flag
    return out


def tier_map(policy: str | None, ng: int = 8) -> dict[int, dict[int, int]]:
    """tier_of[recipient][donor] -> tier. ng=1 is the simulator's single-group mode."""
    prefs = {0: [0]} if ng == 1 else {g: pref_list(g, policy) for g in range(8)}
    return {g: {h: n for n, h in enumerate(prefs[g])} for g in prefs}


def is_anti_d(recipient_g: int, donor_g: int) -> bool:
    """RhD+ unit to an RhD- recipient (only possible under the relaxed policy)."""
    return recipient_g % 2 == 1 and donor_g % 2 == 0


def is_abo_identical(recipient_g: int, donor_g: int) -> bool:
    return recipient_g // 2 == donor_g // 2
