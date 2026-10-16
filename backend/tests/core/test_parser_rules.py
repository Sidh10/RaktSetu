"""Rule-based parser on the formats in docs/PARSER_SPEC.md section 3 (all synthetic). These are unit tests written
alongside the rules; they are NOT accuracy evidence (that comes from the frozen, partly hand-written test split)."""
from datetime import date

import pytest

from app.core.parser_rules import BLOCKING, parse, resolve_expiry

TODAY = date(2026, 10, 16)   # a Friday


def rows(text, letter="h"):
    r = parse(text, TODAY, letter)
    return r, [(i.abo_rh, i.component, i.count, i.expiry and i.expiry.resolved_date.isoformat()) for i in r.items]


@pytest.mark.parametrize("text,mtype,expected", [
    ("O+ RDP x4 exp 17/10", "stock_post", [("O+", "RDP", 4, "2026-10-17")]),
    ("Platelets available: B+ 3 (expire tomorrow), O+ 2 (expire 18 Oct)", "stock_post",
     [("B+", None, 3, "2026-10-17"), ("O+", None, 2, "2026-10-18")]),
    ("Centre H: O+ RDP 2 unit kal expire, B+ 1", "stock_post", [("O+", "RDP", 2, "2026-10-17"), ("B+", "RDP", 1, None)]),
    ("aaj 2 O pos platelet bacha hai, kal tak", "stock_post", [("O+", None, 2, "2026-10-17")]),
    ("Need 3 O+ platelets urgently", "shortfall", [("O+", None, 3, None)]),
    ("humko 2 B neg SDP chahiye", "shortfall", [("B-", "SDP", 2, None)]),
    ("Stock update — A+ 1, AB+ 1, O- nil", "stock_post", [("A+", None, 1, None), ("AB+", None, 1, None)]),
    ("Good morning sir", "other", []),
    ("O+ve 2 and B-ve 1 all expire 18/10", "stock_post", [("O+", None, 2, "2026-10-18"), ("B-", None, 1, "2026-10-18")]),
    ("do O+ aur teen B+ hai, sab parso tak", "stock_post", [("O+", None, 2, "2026-10-18"), ("B+", None, 3, "2026-10-18")]),
    ("AB negative apheresis 1 exp 20 oct", "stock_post", [("AB-", "SDP", 1, "2026-10-20")]),
])
def test_spec_formats(text, mtype, expected):
    r, got = rows(text)
    assert r.message_type == mtype
    assert got == expected


def test_flags():
    r, _ = rows("Centre H: O+ RDP 2 unit kal expire, B+ 1")
    assert r.items[0].flags == ["expiry_relative"] and r.items[1].flags == ["expiry_missing"]
    r, _ = rows("O platelets 2 exp tomorrow")
    assert r.items[0].abo_rh is None and "unknown_group" in r.items[0].flags        # never guessed
    r, _ = rows("Patient Ramesh ward 4 needs 2 O+")
    assert "possible_patient_data" in r.flags
    r, _ = rows("Centre C has O+ 2 exp 18/10", letter="h")
    assert "centre_mismatch" in r.flags
    r, _ = rows("O+ 2 exp 10/10")
    assert "expiry_in_past" in r.items[0].flags
    assert {"unknown_group", "count_missing", "expiry_missing", "possible_patient_data"} <= BLOCKING


def test_nil_rows_dropped_with_note():
    r, got = rows("O- nil, B+ 2 exp 18/10")
    assert got == [("B+", None, 2, "2026-10-18")] and "nil" in r.notes[0]


def test_resolve_expiry_never_invents_dates():
    assert resolve_expiry("relative_day", "tomorrow", TODAY).resolved_date == date(2026, 10, 17)
    assert resolve_expiry("weekday", "sunday", TODAY).resolved_date == date(2026, 10, 18)
    assert resolve_expiry("absolute_date", "2026-10-19", TODAY).resolved_date == date(2026, 10, 19)
    assert resolve_expiry("relative_day", "next week", TODAY) is None
    assert resolve_expiry("absolute_date", "19 Oct", TODAY) is None
    assert resolve_expiry("none", None, TODAY) is None


@pytest.mark.parametrize("word,expected", [("monday", "2026-10-19"), ("Tuesday", "2026-10-20"), ("wednesday", "2026-10-21"),
                                           ("Thursday", "2026-10-22"), ("friday", "2026-10-16"), ("SATURDAY", "2026-10-17"),
                                           ("sunday", "2026-10-18"), ("wed", "2026-10-21"), ("sat", "2026-10-17")])
def test_every_weekday_name(word, expected):
    """Regression: 'wednesday' and 'saturday' were not matched before 16 Oct (found by the eval preview)."""
    _, got = rows(f"O+ 1 exp {word}")
    assert got == [("O+", None, 1, expected)]
