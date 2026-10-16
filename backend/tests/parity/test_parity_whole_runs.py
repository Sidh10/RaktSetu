"""Golden parity P-08: whole simulator runs replayed through app.core on dev seeds 9000-9004.
Covers greedy order (P-06), the 12-h margin (P-07), Beta trust updates (P-09) and finder ranking (P-10)
in context. Dev-seed numbers are compared for equality only and never reported (PREREGISTRATION_v3.md section 1)."""
import json

import pytest

import golden_common as gc
import sim_harness
from golden_common import load_fixture

pytestmark = pytest.mark.parity

CASES = load_fixture("p08_whole_runs")["cases"]


def _id(c):
    i = c["input"]
    return f"{i['seed']}-{i['scen'][:2]}-{i['arm']}-{i['family']}-{i['groups']}-{i['policy']}-r12{int(i['rule12'])}"


@pytest.mark.parametrize("case", CASES, ids=[_id(c) for c in CASES])
def test_p08_whole_run_identical(sim, case):
    i, exp = case["input"], case["expected"]
    record, callog, visitlog = [], [], []
    m = sim_harness.run(sim, i["seed"], i["days"], sim.SCENARIOS[i["scen"]], i["arm"], record=record,
                        family=i["family"], groups_set=i["groups"], policy=i["policy"], rule12=i["rule12"],
                        q=i.get("q", 0.0), Tt=i.get("Tt", 90.0), callog=callog, visitlog=visitlog)
    got = gc.run_digests(record, callog, visitlog)
    first_bad = next((d for d, (a, b) in enumerate(zip(got["per_day"], exp["per_day"])) if a != b), None)
    assert first_bad is None, f"first divergent day: {first_bad}"
    assert json.loads(gc.canonical(sim.rates(m))) == exp["rates"]
    for key in ("record", "callog", "visitlog", "n_calls", "n_visits"):
        assert got[key] == exp[key], key
