"""Roles, privacy, stock posts and the public finder (FR-L*, FR-F*, FR-X1, NFR-4)."""
import json

from sqlalchemy import func, inspect, select

from apihelp import err, ok, run_match
from app.db import Base
from app.models import Unit

IDENTIFYING = {"donor", "patient", "name", "bag", "phone", "dob", "age", "sex", "gender", "ward", "bed", "mrn",
               "aadhaar", "address"}


def test_no_identifying_fields_anywhere():
    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            parts = set(col.name.lower().split("_"))
            hits = parts & IDENTIFYING
            allowed = (table.name == "centre" and col.name in ("name", "public_phone")) or \
                      (table.name == "user" and col.name == "display_name")
            assert not hits or allowed, f"{table.name}.{col.name}"


def test_unit_ids_are_opaque(api):
    with api.session() as s:
        ids = s.scalars(select(Unit.id)).all()
    assert all(i.startswith("U-") and len(i) == 10 for i in ids) and len(set(ids)) == len(ids)


def test_shortfall_rejects_extra_fields_and_wrong_roles(api):
    e = err(api.as_("u-staff-c").post("/api/shortfalls", {"abo_rh": "O+", "count": 1, "patient_name": "X"}),
            400, "validation_error")
    assert any("patient_name" in str(x["loc"]) for x in e["details"]["errors"])
    err(api.as_("u-coord").post("/api/shortfalls", {"abo_rh": "O+", "count": 1}), 403, "forbidden_role")
    err(api.post("/api/shortfalls", {"abo_rh": "O+", "count": 1}), 403, "forbidden_role")
    err(api.as_("u-staff-c").post("/api/shortfalls", {"abo_rh": "O", "count": 1}), 400, "unknown_group")
    assert ok(api.as_("u-staff-c").post("/api/shortfalls", {"abo_rh": "AB-", "count": 1}), 201)["status"] == "open"


def test_stock_post_replaces_listing_but_keeps_received_units(api):
    err(api.as_("u-staff-f").post("/api/centres/C-D/stock-posts", {"units": []}), 403, "not_your_centre")
    err(api.as_("u-coord").post("/api/centres/C-D/stock-posts", {"units": []}), 403, "forbidden_role")
    body = {"units": [{"abo_rh": "B+", "expires_on": "2026-10-18"},
                      {"abo_rh": "O+", "component": "SDP", "expires_at": "2026-10-17T20:00:00+05:30"}]}
    out = ok(api.as_("u-staff-d").post("/api/centres/C-D/stock-posts", body), 201) \
        if False else None   # Centre D has no demo staff user; use Centre H instead
    assert out is None
    out = ok(api.as_("u-staff-h").post("/api/centres/C-H/stock-posts", body), 201)
    assert out == {"stock_post_id": out["stock_post_id"], "listed": 2, "superseded": 3}
    units = ok(api.as_("u-coord").get("/api/centres/C-H/units"))
    assert sorted((u["abo_rh"], u["component"]) for u in units) == [("B+", "RDP"), ("O+", "SDP")]
    board = ok(api.as_("u-coord").get("/api/board"))
    h = next(c for c in board["centres"] if c["id"] == "C-H")
    assert h["updated"] == "under 1 h ago" and h["listing_age_bucket"] == 0
    err(api.as_("u-staff-h").post("/api/centres/C-H/stock-posts",
                                  {"units": [{"abo_rh": "B+", "expires_on": "2026-10-10"}]}), 400, "validation_error")
    err(api.as_("u-staff-h").post("/api/centres/C-H/stock-posts",
                                  {"units": [{"abo_rh": "B+"}]}), 400, "validation_error")


def test_expired_units_drop_out(api):
    before = {c["id"]: c["listed"] for c in ok(api.as_("u-coord").get("/api/board"))["centres"]}
    api.clock.advance(hours=15)                      # past midnight: units with 1 day left have expired
    after = {c["id"]: c["listed"] for c in ok(api.as_("u-coord").get("/api/board"))["centres"]}
    assert after["C-F"] == before["C-F"] - 1 and after["C-H"] == before["C-H"] - 2 and after["C-D"] == before["C-D"] - 1


def test_identity_rules(api):
    err(api.get("/api/board"), 403, "forbidden_role")                   # public cannot see the board
    err(api.as_("nobody").get("/api/board"), 400, "unknown_user")
    assert ok(api.get("/api/me"))["role"] == "public"
    assert "not real authentication" in ok(api.as_("u-mo-f").get("/api/me"))["note"]
    err(api.as_("u-staff-f").post("/api/match/run", {"policy": "strict"}), 403, "forbidden_role")
    err(api.as_("u-staff-f").get("/api/trust"), 403, "forbidden_role")
    rows = ok(api.as_("u-mo-g").get("/api/trust"))["rows"]
    assert {r["centre"] for r in rows} == {"C-G"}


def test_health_carries_labels(api):
    h = ok(api.get("/api/health"))
    assert h["labels"] == ["simulated data", "mock channel", "not clinically validated"] and h["demo_clock"]


def test_finder_bands_only_ranked_and_read_only(api):
    tables = [t.name for t in Base.metadata.sorted_tables]

    def counts():
        with api.session() as s:
            return {t: s.scalar(select(func.count()).select_from(Base.metadata.tables[t])) for t in tables}
    c0 = counts()
    for _ in range(50):
        r = ok(api.get("/api/public/finder", params={"group": "B+"}))
    assert counts() == c0                                               # FR-F5: writes nothing
    for res in r["results"]:
        assert set(res) == {"centre_name", "area", "phone", "listed_compatible", "updated", "band"}
        assert res["band"] in ("High", "Medium", "Low")
        for v in res.values():
            assert not isinstance(v, float) and "%" not in str(v)      # FR-F2: no probability
    names = [x["centre_name"] for x in r["results"]]
    assert names[0].startswith("Centre B") and "Call before travelling" in r["advice"]
    assert "simulated" in r["band_note"] and "finder_bands.json" in r["band_note"]
    err(api.get("/api/public/finder", params={"group": "Z"}), 400, "unknown_group")


def test_audit_access(api):
    t = run_match(api)["suggested"][0]
    rows = ok(api.as_("u-coord").get("/api/audit", params={"entity": "transfer", "entity_id": t["id"]}))
    assert rows and rows[0]["to_state"] == "suggested"
    err(api.as_("u-staff-f").get("/api/audit"), 403, "forbidden_role")
    err(api.as_("u-mo-f").get("/api/audit"), 403, "forbidden_role")
    assert json.dumps(ok(api.as_("u-mo-f").get("/api/audit", params={"entity": "transfer", "entity_id": t["id"]})))
