"""The demo script (docs/DEMO_SCRIPT.md) depends on these exact outcomes of the seeded city (FR-X2)."""
from apihelp import ok, run_match


def test_demo_seed_contract(api):
    board = ok(api.as_("u-coord").get("/api/board"))
    bands = {c["id"]: c["trust_band"] for c in board["centres"]}
    assert bands["C-F"] == "High" and bands["C-G"] == "Low" and bands["C-H"] == "Medium"
    assert {c["id"]: c["updated"] for c in board["centres"]}["C-G"] == "2 days ago"
    assert {c["id"]: c["received"] for c in board["centres"]}["C-D"] == 1

    r = run_match(api)
    got = sorted((t["from_centre"], t["to_centre"], t["abo_rh_offered"], t["qty_requested"], t["tier"])
                 for t in r["suggested"])
    assert got == [("C-F", "C-C", "O+", 2, 0), ("C-G", "C-A", "B+", 2, 0)]
    u = r["unmatched_needs"]
    assert u == [dict(centre="C-C", centre_name="Centre C · Cancer hospital", abo_rh="O+", component="RDP", open=1,
                      why=u[0]["why"])]
    assert u[0]["why"][0].isupper() and not u[0]["why"].endswith(".")      # the UI appends the full stop
    assert len(r["notes"]) == 1 and "Centre H" in r["notes"][0] and "12 h" in r["notes"][0]
    bands_on_cards = {t["from_centre"]: t["sender_band"] for t in r["suggested"]}
    assert bands_on_cards == {"C-F": "High", "C-G": "Low"}
