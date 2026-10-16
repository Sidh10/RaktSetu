"""Unit tests for app.core: edge cases and invariants the parity fixtures do not pin down."""
import random
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core import finder, groups, margin, matcher, stock, trust

IST = timezone(timedelta(hours=5, minutes=30))


# --- groups -------------------------------------------------------------------------------------------------
def test_group_names_roundtrip():
    for g, name in enumerate(groups.GROUPS):
        assert groups.group_index(name) == g and groups.group_name(g) == name
    with pytest.raises(ValueError):
        groups.group_index("O")


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        groups.pref_list(0, "loose")


def test_standard_never_gives_rhd_pos_to_rhd_neg():
    for g in range(1, 8, 2):
        assert all(h % 2 == 1 for h in groups.pref_list(g, "standard"))


def test_anti_d_only_possible_under_relaxed():
    for policy in ("strict", "standard"):
        assert not any(groups.is_anti_d(g, h) for g in range(8) for h in groups.pref_list(g, policy))
    assert any(groups.is_anti_d(g, h) for g in range(8) for h in groups.pref_list(g, "relaxed"))


def test_identical_group_is_always_tier_zero():
    for policy in groups.POLICIES:
        tm = groups.tier_map(policy)
        assert all(tm[g][g] == 0 for g in range(8))


def test_distribution_sums_to_one():
    assert abs(sum(groups.DIST_WEST) - 1.0) < 1e-12


# --- stock --------------------------------------------------------------------------------------------------
def test_received_units_never_offerable():
    units = [[1, True, 0], [2, True, 0], [1, True, 0]]
    assert stock.own_offerable(units, 0, 0.0) == []


def test_offerable_is_oldest_first_and_capped_by_surplus():
    units = [[2, False, 0], [1, False, 0], [5, False, 0], [2, False, 0]]
    # dmean 0 -> every near-expiry unit is surplus
    assert stock.own_offerable(units, 0, 0.0) == [1, 2, 2]
    # large expected use -> nothing spare
    assert stock.own_offerable(units, 0, 10.0) == []


def test_remaining_days_mapping():
    today = date(2026, 10, 16)
    assert stock.remaining_days(date(2026, 10, 16), today) == 1   # expires tonight
    assert stock.remaining_days(date(2026, 10, 17), today) == 2   # tomorrow -> near-expiry
    assert stock.remaining_days(date(2026, 10, 15), today) == 0   # expired


def test_staleness_bucket():
    assert [stock.staleness_bucket(d) for d in (None, 0, 1, 2, 9)] == [2, 0, 1, 2, 2]


def test_par_and_needs():
    par = stock.par_levels(4.0, groups.DIST_WEST)
    assert sum(par) == 5                        # ceil(1.2 * 4.0)
    assert stock.needs_from_par(par, [9] * 8) == [0] * 8


# --- margin (P-07: the timestamp form agrees with the simulator form at 09:00) ------------------------------
@pytest.mark.parametrize("r", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tconf", [0.0, 15.0, 59.9, 60.0, 75.0, 140.0])
@pytest.mark.parametrize("tt", [90.0, 180.0])
def test_p07_margin_forms_agree_at_decision_time(r, tconf, tt):
    today = date(2026, 10, 16)
    now = datetime(2026, 10, 16, margin.DECISION_HOUR, tzinfo=IST)
    expiry_day = today + timedelta(days=r - 1)
    expires_at = datetime(expiry_day.year, expiry_day.month, expiry_day.day, tzinfo=IST) + timedelta(days=1)
    assert stock.remaining_days(expiry_day, today) == r
    assert margin.passes_margin(expires_at, now, tconf, tt) == margin.passes_margin_days(r, tconf, tt)


def test_margin_boundary_is_inclusive():
    now = datetime(2026, 10, 16, 9, tzinfo=IST)
    assert margin.passes_margin(now + timedelta(hours=13, minutes=30), now, 0, 90)      # exactly 12 h on arrival
    assert not margin.passes_margin(now + timedelta(hours=13, minutes=29), now, 0, 90)


def test_margin_requires_aware_datetimes():
    with pytest.raises(ValueError):
        margin.passes_margin(datetime(2026, 10, 17), datetime(2026, 10, 16, tzinfo=timezone.utc), 0, 90)


def test_one_day_unit_cannot_make_180_min_trip():
    # RESULTS_v3.md section 6: with 180-min transport no unit with one day left meets the margin
    # "once any call time is added"; with zero call time it arrives with exactly 12 h (inclusive pass).
    assert margin.passes_margin_days(1, 0.0, 180.0)
    assert not any(margin.passes_margin_days(1, tc, 180.0) for tc in (0.1, 5.0, 15.0))


# --- trust --------------------------------------------------------------------------------------------------
def test_prior_estimate():
    assert trust.estimate(trust.PRIOR_ALPHA, trust.PRIOR_BETA) == pytest.approx(2 / 3)


def test_confirmation_update():
    assert trust.after_confirmation(2.0, 1.0, requested=2, found=1) == (3.0, 2.0)
    assert trust.after_confirmation(2.0, 1.0, requested=3, found=0) == (2.0, 4.0)
    for bad in ((2, 3), (2, -1), (-1, 0)):
        with pytest.raises(ValueError):
            trust.after_confirmation(2.0, 1.0, requested=bad[0], found=bad[1])


# --- finder -------------------------------------------------------------------------------------------------
def test_band_boundaries():
    assert [finder.band(p) for p in (0.0, 0.49, 0.5, 0.79, 0.8, 1.0)] == ["Low", "Low", "Medium", "Medium",
                                                                          "High", "High"]
    with pytest.raises(ValueError):
        finder.band(1.5)


def test_rank_modes_and_drop_empty():
    c = [finder.FinderCandidate(0, 4, 0.4, 2), finder.FinderCandidate(1, 3, 0.9, 0),
         finder.FinderCandidate(2, 0, 0.99, 0), finder.FinderCandidate(3, 3, 0.9, 0)]
    assert [x.centre for x in finder.rank(c, "raw")] == [0, 1, 3]
    assert [x.centre for x in finder.rank(c, "trust")] == [1, 3, 0]


# --- matcher plan -------------------------------------------------------------------------------------------
def test_plan_example():
    tiers = groups.tier_map("strict")
    needs = [[3, 2, 0], [2, 0, 4]]                          # C needs 3 O+, A needs 2 B+
    offers = {(5, 0): 2, (6, 4): 2, (7, 0): 1}               # F: 2 O+, G: 2 B+, H: 1 O+
    out = matcher.plan(needs, offers, tiers)
    assert [(a.donor, a.recipient, a.donor_group, a.qty) for a in out] == [(5, 2, 0, 2), (7, 2, 0, 1), (6, 0, 4, 2)]
    assert offers == {(5, 0): 2, (6, 4): 2, (7, 0): 1}      # input not mutated


def test_plan_never_self_supplies_and_respects_offers():
    rng = random.Random(7)
    for _ in range(1000):
        policy = rng.choice(groups.POLICIES)
        tiers = groups.tier_map(policy)
        needs = [[rng.randint(1, 4), rng.randrange(8), rng.randrange(8)] for _ in range(rng.randint(0, 6))]
        offers = {(i, h): rng.randint(1, 4) for i in range(8) for h in range(8) if rng.random() < 0.15}
        out = matcher.plan(needs, offers, tiers)
        used = {}
        for a in out:
            assert a.donor != a.recipient
            assert a.donor_group in tiers[a.recipient_group]
            assert a.tier == tiers[a.recipient_group][a.donor_group]
            if policy == "strict":
                assert a.tier == 0 and a.donor_group == a.recipient_group
            used[(a.donor, a.donor_group)] = used.get((a.donor, a.donor_group), 0) + a.qty
        assert all(used[k] <= offers[k] for k in used)


def test_plan_matches_greedy_with_always_successful_attempts():
    rng = random.Random(11)
    for _ in range(300):
        tiers = groups.tier_map(rng.choice(groups.POLICIES))
        needs = [[rng.randint(1, 4), rng.randrange(8), rng.randrange(8)] for _ in range(rng.randint(0, 6))]
        offers = {(i, h): rng.randint(1, 4) for i in range(8) for h in range(8) if rng.random() < 0.15}
        calls = []
        live = dict(offers)

        def attempt(key, j, need):
            req = min(need, live[key])
            live[key] -= req
            calls.append((key[0], key[1], j, req))
            return req
        matcher.greedy_match(needs, live, tiers, attempt)
        assert calls == [(a.donor, a.donor_group, a.recipient, a.qty) for a in matcher.plan(needs, offers, tiers)]


def test_greedy_one_need_at_a_time_equals_single_call():
    """services/matching.py calls greedy_match per need (to know which need an allocation serves)."""
    rng = random.Random(23)
    for _ in range(300):
        tiers = groups.tier_map(rng.choice(groups.POLICIES))
        needs = [[rng.randint(1, 4), rng.randrange(8), rng.randrange(8)] for _ in range(rng.randint(0, 6))]
        offers = {(i, h): rng.randint(1, 4) for i in range(8) for h in range(8) if rng.random() < 0.15}

        def runner(per_need):
            live, calls = dict(offers), []

            def attempt(key, j, need):
                req = min(need, live[key]) - (1 if live[key] > 2 else 0)   # sometimes partial, like a margin cut
                live[key] -= max(req, 0)
                calls.append((key, j, max(req, 0)))
                return max(req, 0)
            if per_need:
                for n in sorted(needs, reverse=True):
                    matcher.greedy_match([n], live, tiers, attempt)
            else:
                matcher.greedy_match(needs, live, tiers, attempt)
            return calls
        assert runner(True) == runner(False)


def test_env_file_loader_never_overrides_shell(tmp_path, monkeypatch):
    from app.config import load_env_file
    f = tmp_path / ".env"
    f.write_text("# comment\nRAKTSETU_TEST_A=from_file\nRAKTSETU_TEST_B='quoted'\nRAKTSETU_TEST_EMPTY=\nnot a line\n",
                 encoding="utf-8")
    monkeypatch.setenv("RAKTSETU_TEST_A", "from_shell")
    monkeypatch.delenv("RAKTSETU_TEST_B", raising=False)
    monkeypatch.delenv("RAKTSETU_TEST_EMPTY", raising=False)
    assert load_env_file(f) == 1
    import os
    assert os.environ["RAKTSETU_TEST_A"] == "from_shell" and os.environ["RAKTSETU_TEST_B"] == "quoted"
    assert "RAKTSETU_TEST_EMPTY" not in os.environ
    monkeypatch.delenv("RAKTSETU_TEST_B")
    assert load_env_file(tmp_path / "missing.env") == 0
