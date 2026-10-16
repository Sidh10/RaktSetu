"""Walk the demo flow through the running API and print each step (SIMULATED DATA, role-played users).

    make seed && make api                       # in one terminal
    .venv/Scripts/python scripts/demo_flow.py   # in another (default http://localhost:8000)

Needs a FRESHLY SEEDED city: it changes the demo data, so run `make seed` before each run.
Steps: board -> strict match -> F->C confirm 2, staff approval refused, MO approves, dispatch, deliver ->
G->A confirm only 1 of 2 (trust learns) -> one-hop check -> public finder (bands only).
"""
from __future__ import annotations

import argparse
import sys

import httpx


NOT_FRESH = ("The demo city is not freshly seeded (transfers already exist), so the scripted flow cannot run.\n"
             "Run `make seed` (or `.venv\\Scripts\\python.exe scripts\\seed_demo.py --reset`; it works while the API is running) and try again.")


class Demo:
    def __init__(self, base):
        self.base = base
        self.c = httpx.Client(base_url=base, timeout=10)

    def call(self, method, url, user=None, body=None, params=None, expect=200):
        try:
            r = self.c.request(method, url, json=body, params=params,
                               headers={"X-Demo-User": user} if user else {})
        except httpx.ConnectError:
            sys.exit(f"Cannot reach the API at {self.base}. Start it first (`make api`, or the uvicorn command in "
                     "the README).")
        if r.status_code != expect:
            sys.exit(f"FAILED {method} {url} as {user}: {r.status_code} {r.text}")
        return r.json()


def main():
    # Windows consoles default to cp1252/cp437, which cannot print "≤", "→" or "·"
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    d = Demo(ap.parse_args().base)
    say = print

    h = d.call("GET", "/api/health")
    if d.call("GET", "/api/transfers", "u-coord"):
        sys.exit(NOT_FRESH)
    say(f"Labels: {' · '.join(h['labels'])} · demo clock {h['now']}")
    say("\n1. Board (coordinator)")
    for c in d.call("GET", "/api/board", "u-coord")["centres"]:
        say(f"   {c['name']:<32} listed {c['listed']:>2}  ≤2 days {c['near_expiry']}  updated {c['updated']:<12} "
            f"trust {c['trust_band']:<6} offers {c['offerable'] or '-'}")

    say("\n2. Run matcher, strict ABO/RhD")
    m = d.call("POST", "/api/match/run", "u-coord", {"policy": "strict"})
    for t in m["suggested"]:
        say(f"   #{t['id']} {t['from_name']} -> {t['to_name']}: {t['qty_requested']} x {t['abo_rh_offered']} "
            f"(sender {t['sender_band']})")
    for n in m["notes"]:
        say(f"   note: {n}")
    for u in m["unmatched_needs"]:
        say(f"   unmatched: {u['centre_name']} still needs {u['open']} x {u['abo_rh']}. {u['why']}.")
    fc = next((t for t in m["suggested"] if t["from_centre"] == "C-F"), None)
    ga = next((t for t in m["suggested"] if t["from_centre"] == "C-G"), None)
    if fc is None or ga is None:
        sys.exit("The matcher did not suggest the scripted F -> C and G -> A transfers. The demo clock has probably "
                 "moved on (units expired) or the data was changed.\n" + NOT_FRESH.split("\n", 1)[1])

    say(f"\n3. Transfer #{fc['id']} F -> C")
    d.call("POST", f"/api/transfers/{fc['id']}/request-confirmation", "u-coord")
    say("   coordinator requested confirmation")
    t = d.call("POST", f"/api/transfers/{fc['id']}/confirm", "u-staff-f", {"units_available": 2})
    say(f"   staff F confirmed 2 -> {t['status']}, reserved {t['qty_confirmed']}")
    e = d.call("POST", f"/api/transfers/{fc['id']}/approve", "u-staff-f", expect=403)
    say(f"   staff F tries to approve -> 403 {e['error']['code']}: {e['error']['message']}")
    t = d.call("POST", f"/api/transfers/{fc['id']}/approve", "u-mo-f", {"note": "ok"})
    say(f"   medical officer F approves -> {t['status']}")
    t = d.call("POST", f"/api/transfers/{fc['id']}/dispatch", "u-staff-f", {"box_validated": True})
    say(f"   staff F dispatches -> {t['status']}; hours left on arrival "
        f"{[u['hours_left_on_arrival'] for u in t['units']]}")
    t = d.call("POST", f"/api/transfers/{fc['id']}/deliver", "u-staff-c")
    say(f"   staff C marks delivered -> {t['status']}")

    say(f"\n4. Transfer #{ga['id']} G -> A (listing 2 days old)")
    d.call("POST", f"/api/transfers/{ga['id']}/request-confirmation", "u-coord")
    t = d.call("POST", f"/api/transfers/{ga['id']}/confirm", "u-staff-g", {"units_available": 1,
                                                                             "note": "only 1 left"})
    tr = t["result"]["trust"]
    say(f"   staff G finds only 1 of 2 -> {t['status']} ({t['qty_confirmed']} reserved); trust G bucket "
        f"{tr['bucket']}: alpha {tr['alpha']:g}, beta {tr['beta']:g}, band {tr['band_before']} -> {tr['band_after']}")
    a = next(s for s in d.call("GET", "/api/shortfalls", "u-coord") if s["centre"] == "C-A")
    say(f"   Centre A shortfall now {a['count_open']} open ({a['status']})")

    say("\n5. One-hop rule")
    c = next(x for x in d.call("GET", "/api/board", "u-coord")["centres"] if x["id"] == "C-C")
    say(f"   Centre C now lists {c['received']} received unit(s); offers {c['offerable'] or 'none'}")

    say("\n6. Public finder, B+ RDP (no login)")
    f = d.call("GET", "/api/public/finder", params={"group": "B+"})
    for r in f["results"]:
        say(f"   {r['centre_name']:<32} {r['band']:<6} listed {r['listed_compatible']}  updated {r['updated']}")
    say(f"   {f['advice']}")

    say("\n7. Audit trail of the F -> C transfer")
    for row in d.call("GET", "/api/audit", "u-coord", params={"entity": "transfer", "entity_id": fc["id"]}):
        say(f"   {row['role']:<16} {str(row['from_state']):<18} -> {row['to_state']:<18} {row['note']}")


if __name__ == "__main__":
    main()
