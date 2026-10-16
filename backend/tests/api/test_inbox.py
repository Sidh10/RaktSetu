"""Mock channel + parser inbox: drafts never change stock, human check, commit, LLM fallback (FR-P1..P4)."""
import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from sqlalchemy import func, select

from apihelp import err, ok
from app.models import Shortfall, Unit
from app.services import llm_extract

MSG = "Centre H: O+ RDP 2 unit kal expire, B+ 1"


def inbound(api, user="u-staff-h", text=MSG, **kw):
    return ok(api.as_(user).post("/api/channel/mock/inbound", {"channel": "mock_whatsapp", "text": text, **kw}), 201)


def units_at(api, centre):
    with api.session() as s:
        return s.scalar(select(func.count()).where(Unit.centre_id == centre, Unit.status == "listed"))


def test_draft_does_not_change_stock_and_needs_review(api):
    before = units_at(api, "C-H")
    r = inbound(api)
    d = r["draft"]
    assert r["parser"] == "rules" and "mock channel" in r["labels"]
    assert d["centre_id"] == "C-H" and d["payload"]["message_type"] == "stock_post"
    assert d["blocking"] == ["expiry_missing"]                         # B+ 1 has no expiry
    assert units_at(api, "C-H") == before                              # FR-P4
    err(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/commit"), 409, "needs_review")


def test_review_then_commit_adds_units_without_refreshing_listing_age(api):
    d = inbound(api)["draft"]
    before = units_at(api, "C-H")
    items = [{"abo_rh": "O+", "component": "RDP", "count": 2, "expiry_date": "2026-10-17"},
             {"abo_rh": "B+", "component": "RDP", "count": 1, "expiry_date": "2026-10-18"}]
    e = ok(api.as_("u-staff-h").client.patch(f"/api/parser/drafts/{d['id']}", json={"items": items},
                                             headers={"X-Demo-User": "u-staff-h"}))
    assert e["blocking"] == [] and e["payload"]["commit_mode"] == "add"
    out = ok(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/commit"))
    assert out["kind"] == "stock_post" and out["listed"] == 3 and out["superseded"] == 0
    assert units_at(api, "C-H") == before + 3
    board = ok(api.as_("u-coord").get("/api/board"))
    assert next(c for c in board["centres"] if c["id"] == "C-H")["listing_age_bucket"] == 1     # ADR-015
    err(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/commit"), 409, "illegal_transition")


def test_stock_update_replaces_listing(api):
    d = inbound(api, text="Stock update: O+ 2 exp 18/10, B+ 1 exp 19/10")["draft"]
    assert d["payload"]["commit_mode"] == "replace" and d["blocking"] == []
    out = ok(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/commit"))
    assert out["superseded"] == 3 and units_at(api, "C-H") == 3
    board = ok(api.as_("u-coord").get("/api/board"))
    assert next(c for c in board["centres"] if c["id"] == "C-H")["listing_age_bucket"] == 0


def test_shortfall_message_commit_by_coordinator(api):
    d = inbound(api, user="u-coord", text="Need 2 AB+ platelets urgently", centre_id="C-A")["draft"]
    assert d["payload"]["message_type"] == "shortfall" and d["centre_id"] == "C-A"
    out = ok(api.as_("u-coord").post(f"/api/parser/drafts/{d['id']}/commit"))
    with api.session() as s:
        sf = s.get(Shortfall, out["shortfall_ids"][0])
        assert (sf.centre_id, sf.abo_rh, sf.count_requested) == ("C-A", "AB+", 2)


def test_patient_data_blocks_until_redacted(api):
    d = inbound(api, user="u-staff-c", text="Patient Ramesh ward 4 needs 2 O+")["draft"]
    assert "possible_patient_data" in d["blocking"]
    e = ok(api.as_("u-staff-c").client.patch(f"/api/parser/drafts/{d['id']}", json={"patient_data_redacted": True},
                                             headers={"X-Demo-User": "u-staff-c"}))
    assert e["blocking"] == [] and "removed by reviewer" in e["text"]


def test_roles_and_visibility(api):
    err(api.as_("u-staff-f").post("/api/channel/mock/inbound", {"text": MSG, "centre_id": "C-H"}), 403, "not_your_centre")
    err(api.post("/api/channel/mock/inbound", {"text": MSG}), 403, "forbidden_role")
    d = inbound(api)["draft"]
    err(api.as_("u-staff-f").post(f"/api/parser/drafts/{d['id']}/commit"), 404, "not_found")
    assert [x["id"] for x in ok(api.as_("u-staff-f").get("/api/parser/drafts"))] == []
    assert d["id"] in [x["id"] for x in ok(api.as_("u-coord").get("/api/parser/drafts"))]
    err(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/discard", {}), 400, "validation_error")
    assert ok(api.as_("u-staff-h").post(f"/api/parser/drafts/{d['id']}/discard", {"reason": "duplicate"}))["status"] == "discarded"


def test_unknown_sender_blocks(api):
    d = inbound(api, user="u-coord", text="O+ 2 exp 18/10", sender="+91-99999-99999")["draft"]
    assert d["centre_id"] is None and "unknown_sender" in d["blocking"]


def test_other_message_cannot_be_committed(api):
    d = inbound(api, text="Good morning sir")["draft"]
    assert d["payload"]["message_type"] == "other" and "no_items" in d["blocking"]


def test_samples_endpoint(api):
    s = ok(api.as_("u-coord").get("/api/channel/samples"))
    assert len(s["samples"]) >= 5 and "NOT part of the parser accuracy test set" in s["note"]


# --- LLM path with a fake client (no network, no key needed) ----------------------------------------------
class FakeClient:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.messages = self
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        b = self.behaviour
        if isinstance(b, Exception):
            raise b
        stop, text = b
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="thinking", thinking=""),
                                                          SimpleNamespace(type="text", text=text)])


GOOD = json.dumps({"message_type": "stock_post", "items": [
    {"abo_rh": "O+", "component": "RDP", "count": 2, "expiry_kind": "relative_day", "expiry_value": "tomorrow",
     "source_span": "O+ RDP 2 unit kal expire"},
    {"abo_rh": "B+", "component": None, "count": 1, "expiry_kind": "none", "expiry_value": None,
     "source_span": "B+ 1"}]})


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    holder = {}

    def use(behaviour):
        holder["client"] = FakeClient(behaviour)
        monkeypatch.setattr(llm_extract, "client_factory", lambda timeout_s: holder["client"])
        return holder["client"]
    return use


def test_llm_success_dates_resolved_by_code(api, llm):
    c = llm(("end_turn", GOOD))
    d = inbound(api)["draft"]
    assert d["parser"] == "llm" and d["model"] == "claude-opus-5-5"
    items = d["payload"]["items"]
    assert items[0]["expiry"]["resolved_date"] == "2026-10-17"          # resolved by app.core, not the model
    assert "expiry_missing" in items[1]["flags"] and "component_assumed" in items[1]["flags"]
    call = c.calls[0]
    assert call["output_config"]["format"]["type"] == "json_schema" and call["model"] == "claude-opus-5-5"
    assert "Reference date: 2026-10-16" in call["messages"][0]["content"]


REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize("behaviour,reason", [
    (anthropic.APITimeoutError(request=REQ), "timeout"),
    (anthropic.APIConnectionError(request=REQ), "network"),
    (("refusal", ""), "stop_reason refusal"),
    (("max_tokens", '{"message_type": "stock_post", "items": ['), "stop_reason max_tokens"),
    (("end_turn", '{"message_type": "stock_post"}'), "invalid output"),
    (("end_turn", "not json"), "invalid output"),
])
def test_llm_failure_falls_back_to_rules(api, llm, behaviour, reason):
    llm(behaviour)
    d = inbound(api)["draft"]
    assert d["parser"] == "rules"
    assert any(reason in n and "fell back" in n for n in d["payload"]["notes"])
    assert [i["abo_rh"] for i in d["payload"]["items"]] == ["O+", "B+"]


def test_explicit_llm_mode_errors_instead_of_falling_back(api, llm):
    llm(anthropic.APIConnectionError(request=REQ))
    err(api.as_("u-staff-h").post("/api/parser/parse", {"text": MSG, "centre_id": "C-H", "mode": "llm"}),
        502, "llm_unavailable")


def test_no_key_uses_rules_without_calling(api, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm_extract, "client_factory", lambda t: (_ for _ in ()).throw(AssertionError("called")))
    assert inbound(api)["parser"] == "rules"
