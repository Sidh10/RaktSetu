"""Transfer workflow: state machine, trust updates, margin, one-hop, audit (FR-T*, FR-M*, FR-L6)."""
from sqlalchemy import func, select

from apihelp import err, ok, run_match, suggestion
from app.models import AuditEvent, Shortfall, TrustCounter, Unit
from app.services import transfers


def T(api, tid, action, user, body=None, **kw):
    return api.as_(user).post(f"/api/transfers/{tid}/{action}", body, **kw)


def to_confirmed(api, frm="C-F", to="C-C", staff="u-staff-f", n=2):
    t = suggestion(run_match(api), frm, to)
    ok(T(api, t["id"], "request-confirmation", "u-coord"))
    return ok(T(api, t["id"], "confirm", staff, {"units_available": n}))


def test_allowed_transitions_match_data_model():
    expected = {("suggested", "confirm_requested"), ("suggested", "cancelled"),
                ("confirm_requested", "confirmed"), ("confirm_requested", "failed"),
                ("confirm_requested", "cancelled"), ("confirmed", "approved"), ("confirmed", "cancelled"),
                ("approved", "dispatched"), ("approved", "cancelled"), ("dispatched", "delivered"),
                ("dispatched", "cancelled")}
    assert transfers.ALLOWED == expected
    assert not any(frm in transfers.TERMINAL for frm, _ in transfers.ALLOWED)


def test_happy_path_and_one_hop(api):
    t = to_confirmed(api)
    assert t["status"] == "confirmed" and t["qty_confirmed"] == 2
    err(T(api, t["id"], "approve", "u-staff-f"), 403, "forbidden_role")       # staff cannot approve
    err(T(api, t["id"], "approve", "u-mo-g"), 404, "not_found")               # other centres cannot see it
    t = ok(T(api, t["id"], "approve", "u-mo-f", {"note": "ok"}))
    assert t["status"] == "approved" and t["approved_by"] == "u-mo-f"
    t = ok(T(api, t["id"], "dispatch", "u-staff-f", {"box_validated": True}))
    assert t["status"] == "dispatched" and all(u["status"] == "in_transit" for u in t["units"])
    err(T(api, t["id"], "deliver", "u-staff-f"), 403, "not_your_centre")      # sender cannot mark delivered
    t = ok(T(api, t["id"], "deliver", "u-staff-c"))
    assert t["status"] == "delivered"
    with api.session() as s:
        moved = s.scalars(select(Unit).where(Unit.centre_id == "C-C", Unit.received_via_transfer.is_(True))).all()
        assert len(moved) == 2 and all(u.status == "listed" for u in moved)
    board = ok(api.as_("u-coord").get("/api/board"))
    c = next(x for x in board["centres"] if x["id"] == "C-C")
    assert c["received"] == 2 and "O+ RDP" not in c["offerable"]                # never offered again


def test_partial_confirmation_updates_trust_and_reopens_need(api):
    with api.session() as s:
        before = s.get(TrustCounter, ("C-G", 2))
        a0, b0 = before.alpha, before.beta
    t = to_confirmed(api, "C-G", "C-A", "u-staff-g", n=1)
    assert t["status"] == "confirmed" and t["qty_confirmed"] == 1
    assert t["result"]["trust"]["bucket"] == 2
    with api.session() as s:
        tc = s.get(TrustCounter, ("C-G", 2))
        assert (tc.alpha, tc.beta) == (a0 + 1, b0 + 1)
        sf = s.scalars(select(Shortfall).where(Shortfall.centre_id == "C-A")).one()
        assert sf.count_open == 1 and sf.status == "open"
        assert s.scalar(select(func.count()).where(Unit.centre_id == "C-G", Unit.status == "not_found")) == 1


def test_zero_confirmation_fails(api):
    with api.session() as s:
        b0 = s.get(TrustCounter, ("C-F", 0)).beta
    t = to_confirmed(api, n=0)
    assert t["status"] == "failed" and t["qty_confirmed"] == 0
    with api.session() as s:
        assert s.get(TrustCounter, ("C-F", 0)).beta == b0 + 2
        assert s.scalars(select(Shortfall).where(Shortfall.centre_id == "C-C")).one().count_open == 3
    err(T(api, t["id"], "approve", "u-mo-f"), 409, "illegal_transition")


def test_confirm_bounds_and_roles(api):
    t = suggestion(run_match(api), "C-F", "C-C")
    err(T(api, t["id"], "confirm", "u-staff-f", {"units_available": 1}), 409, "illegal_transition")  # not requested
    err(T(api, t["id"], "request-confirmation", "u-staff-f"), 403, "forbidden_role")
    ok(T(api, t["id"], "request-confirmation", "u-coord"))
    err(T(api, t["id"], "request-confirmation", "u-coord"), 409, "illegal_transition")
    err(T(api, t["id"], "confirm", "u-staff-f", {"units_available": 3}), 400, "validation_error")
    err(T(api, t["id"], "confirm", "u-staff-c", {"units_available": 1}), 403, "not_your_centre")  # receiver side
    err(T(api, t["id"], "confirm", "u-coord", {"units_available": 1}), 403, "forbidden_role")


def test_no_dispatch_without_approval(api):
    t = to_confirmed(api)
    err(T(api, t["id"], "dispatch", "u-staff-f", {"box_validated": True}), 409, "illegal_transition")


def test_margin_rechecked_at_dispatch(api):
    t = to_confirmed(api)
    ok(T(api, t["id"], "approve", "u-mo-f"))
    api.clock.advance(hours=14)                     # 23:00: the unit expiring tonight now fails the margin
    t = ok(T(api, t["id"], "dispatch", "u-staff-f", {"box_validated": True}))
    assert t["status"] == "dispatched" and t["qty_confirmed"] == 1
    with api.session() as s:
        assert s.scalars(select(Shortfall).where(Shortfall.centre_id == "C-C")).one().count_open == 2


def test_margin_blocks_dispatch_entirely(api):
    t = to_confirmed(api)
    ok(T(api, t["id"], "approve", "u-mo-f"))
    api.clock.advance(hours=38)                     # next day 23:00: nothing can arrive with 12 h left
    err(T(api, t["id"], "dispatch", "u-staff-f", {"box_validated": True}), 409, "margin_failed")


def test_reject_and_cancel_release_units(api):
    t = to_confirmed(api)
    err(T(api, t["id"], "reject", "u-mo-f", {}), 400, "validation_error")    # reason required
    t = ok(T(api, t["id"], "reject", "u-mo-f", {"reason": "box unavailable"}))
    assert t["status"] == "cancelled"
    with api.session() as s:
        assert s.scalar(select(func.count()).where(Unit.status == "reserved")) == 0
        assert s.scalars(select(Shortfall).where(Shortfall.centre_id == "C-C")).one().count_open == 3
    g = next(x for x in ok(api.as_("u-coord").get("/api/transfers", params={"status": "suggested"}))
             if x["from_centre"] == "C-G")             # suggested by the first run, not repeated by later runs
    err(T(api, g["id"], "cancel", "u-staff-g", {"reason": "x"}), 403, "forbidden_role")
    assert ok(T(api, g["id"], "cancel", "u-coord", {"reason": "duplicate"}))["status"] == "cancelled"
    err(T(api, g["id"], "cancel", "u-coord", {"reason": "again"}), 409, "illegal_transition")


def test_stale_version_rejected(api):
    t = suggestion(run_match(api), "C-F", "C-C")
    err(T(api, t["id"], "request-confirmation", "u-coord", headers={"If-Match": "99"}), 409, "stale_version")
    ok(T(api, t["id"], "request-confirmation", "u-coord", headers={"If-Match": str(t["version"])}))


def test_every_transition_audited(api):
    t = to_confirmed(api)
    ok(T(api, t["id"], "approve", "u-mo-f"))
    ok(T(api, t["id"], "dispatch", "u-staff-f", {"box_validated": True}))
    ok(T(api, t["id"], "deliver", "u-staff-c"))
    with api.session() as s:
        rows = s.scalars(select(AuditEvent).where(AuditEvent.entity == "transfer",
                                                  AuditEvent.entity_id == str(t["id"])).order_by(AuditEvent.id)).all()
    assert [r.to_state for r in rows] == ["suggested", "confirm_requested", "confirmed", "approved", "dispatched",
                                          "delivered"]
    assert [r.actor_role for r in rows[1:]] == ["coordinator", "centre_staff", "medical_officer", "centre_staff",
                                                "centre_staff"]


def test_rerun_does_not_duplicate_and_reopened_need_is_rematched(api):
    first = suggestion(run_match(api), "C-F", "C-C")
    assert run_match(api)["suggested"] == []        # needs already covered by pending suggestions
    ok(T(api, first["id"], "cancel", "u-coord", {"reason": "test re-run"}))
    again = suggestion(run_match(api), "C-F", "C-C")
    assert again["id"] != first["id"] and again["qty_requested"] == 2


def test_suggestion_has_reason(api):
    t = suggestion(run_match(api), "C-F", "C-C")
    assert "Centre C" in t["reason"] and "Identical group" in t["reason"] and "High" in t["reason"]


def test_relaxed_needs_acknowledgement_and_flags_anti_d(api):
    err(api.as_("u-coord").post("/api/match/run", {"policy": "relaxed"}), 400, "acknowledgement_required")
    # more O+ near expiry at F, and an O- need at A that only RhD+ stock can meet
    units = [{"abo_rh": "O+", "component": "RDP", "expires_on": "2026-10-17"} for _ in range(6)]
    ok(api.as_("u-staff-f").post("/api/centres/C-F/stock-posts", {"units": units}), 201)
    ok(api.as_("u-staff-a").post("/api/shortfalls", {"abo_rh": "O-", "count": 1}), 201)
    strict = run_match(api)
    assert not any(t["anti_d_flag"] for t in strict["suggested"])
    for t in strict["suggested"]:
        ok(T(api, t["id"], "cancel", "u-coord", {"reason": "re-run relaxed"}))
    relaxed = run_match(api, "relaxed", acknowledged_by="u-mo-a")
    flagged = [t for t in relaxed["suggested"] if t["anti_d_flag"]]
    assert flagged and flagged[0]["abo_rh_needed"] == "O-" and flagged[0]["abo_rh_offered"] == "O+"
    assert "anti-D" in flagged[0]["reason"]
