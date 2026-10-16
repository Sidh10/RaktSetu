"""Generate golden parity fixtures from the READ-ONLY simulator (docs/TESTING.md section 2).

    python scripts/gen_golden.py --sim-dir ../RaktSetu_simulator_and_prototype/sim_v3 --out backend/tests/golden

Imports raktsetu_sim_v3.py and bands_v3.py by file path; never writes to the simulator folder.
Whole-run cases use dev seeds 9000-9004 only (never reported: PREREGISTRATION_v3.md section 1).
Fixtures are never hand-edited.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "tests" / "parity"))
import golden_common as gc  # noqa: E402

RNG_SEED = 20261015
DAYS = 180

# Whole-run replay cases (P-08). Keys mirror raktsetu_sim_v3.run() arguments.
RUN_CASES = (
    [dict(seed=s, scen="S1_realistic", arm="E", family="trust", groups="WEST", policy="strict", rule12=True)
     for s in range(9000, 9005)]
    + [dict(seed=s, scen="S2_poor", arm="E", family="trust", groups="WEST", policy="strict", rule12=True)
       for s in range(9000, 9005)]
    + [
        dict(seed=9000, scen="S1_realistic", arm="E", family="trust", groups="WEST", policy="standard", rule12=True),
        dict(seed=9001, scen="S1_realistic", arm="E", family="trust", groups="WEST", policy="relaxed", rule12=True),
        dict(seed=9002, scen="S1_realistic", arm="E", family="naive", groups="WEST", policy="strict", rule12=True),
        dict(seed=9003, scen="S2_poor", arm="C", family="naive", groups="WEST", policy="strict", rule12=True),
        dict(seed=9004, scen="S1_realistic", arm="A", family="naive", groups="WEST", policy="strict", rule12=True),
        dict(seed=9000, scen="S1_realistic", arm="E", family="trust", groups=None, policy="standard", rule12=False),
        dict(seed=9001, scen="S1_realistic", arm="E", family="trust", groups="WEST", policy="strict", rule12=True,
             q=0.3, Tt=180.0),
    ]
)


def meta(sim_dir: Path, sim) -> dict:
    import numpy
    return dict(sim_file_sha256=gc.sha256_file(sim_dir / gc.SIM_FILE),
                bands_file_sha256=gc.sha256_file(sim_dir / gc.BANDS_FILE),
                numpy=numpy.__version__, python=platform.python_version(),
                generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                generator_seed=RNG_SEED, note="SIMULATED; dev seeds only; never hand-edit")


def rand_shares(rng: random.Random, n: int) -> list[float]:
    x = [rng.random() for _ in range(n)]
    s = sum(x)
    return [v / s for v in x]


def p01(sim):
    return [dict(input=dict(g=g, policy=p), expected=sim.pref_list(g, p))
            for p in ("strict", "standard", "relaxed") for g in range(8)]


def p02(sim):
    return [dict(input="DIST_WEST", expected=sim.DIST_WEST.tolist()),
            dict(input="DIST_NORTH", expected=sim.DIST_NORTH.tolist())]


def p03(sim, rng):
    cases = [dict(input=dict(total=math.ceil(1.2 * c[1]), w=sim.DIST_WEST.tolist()),
                  expected=sim.apportion(math.ceil(1.2 * c[1]), sim.DIST_WEST)) for c in sim.CENTRES]
    for _ in range(500):
        n = rng.choice([1, 2, 3, 8])
        w = rand_shares(rng, n)
        total = rng.randint(0, 40)
        cases.append(dict(input=dict(total=total, w=w), expected=sim.apportion(total, w)))
    return cases


def rand_units(rng, n_max=14, ng=8):
    return [[rng.randint(1, 5), rng.random() < 0.25, rng.randrange(ng)] for _ in range(rng.randint(0, n_max))]


def p04(sim, rng):
    cases = []
    for _ in range(1000):
        units = rand_units(rng)
        dmean = rng.choice([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.4, 8.0, 11.5, rng.uniform(0, 12)])
        wd = rand_shares(rng, 8) if rng.random() < 0.5 else sim.DIST_WEST.tolist()
        g = rng.randrange(8)
        c = sim.Centre(dmean, 8, wd)
        c.units = [list(u) for u in units]
        rems = sorted(r for r, f, gg in units if gg == g)
        cases.append(dict(input=dict(units=units, g=g, dmean=dmean, wd=wd),
                          expected=dict(surplus=sim.surplus_near(rems, dmean * wd[g]), offerable=c.own_offerable(g))))
    return cases


def p05(sim, rng):
    cases = []
    for _ in range(300):
        c = sim.Centre(1.0, 8, sim.DIST_WEST.tolist())
        never = rng.random() < 0.1
        snap = [(rng.randint(1, 5), rng.randrange(8)) for _ in range(rng.randint(0, 15))]
        snap_day = None if never else rng.randint(0, 20)
        day = (snap_day or 0) + rng.randint(0, 6)
        out_since = [rng.choice([0, 0, 0, 1, 2]) for _ in range(8)]
        if not never:
            c.snap, c.snap_day, c.out_since = list(snap), snap_day, list(out_since)
        cases.append(dict(input=dict(snap=snap, snap_day=snap_day, day=day, out_since=out_since),
                          expected=c.view(day)))
    return cases


def p10(bands, rng):
    ps = [0.0, 0.4999, 0.5, 0.5001, 0.7999, 0.8, 0.8001, 1.0] + [rng.random() for _ in range(500)]
    out = []
    for p in ps:
        name = next(n for n, lo, hi in bands.BANDS if lo <= p < hi)
        out.append(dict(input=p, expected=name))
    return dict(thresholds=[list(b) for b in bands.BANDS], cases=out)


def p08(sim):
    cases = []
    for spec in RUN_CASES:
        record, callog, visitlog = [], [], []
        kw = {k: v for k, v in spec.items() if k not in ("seed", "scen")}
        m = sim.run(spec["seed"], DAYS, sim.SCENARIOS[spec["scen"]], record=record, callog=callog,
                    visitlog=visitlog, **kw)
        cases.append(dict(input=dict(spec, days=DAYS), expected=dict(
            rates=json.loads(gc.canonical(sim.rates(m))), **gc.run_digests(record, callog, visitlog))))
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-dir", type=Path, default=gc.DEFAULT_SIM_DIR)
    ap.add_argument("--out", type=Path, default=gc.GOLDEN_DIR)
    a = ap.parse_args()
    sim, bands = gc.load_sim(a.sim_dir), gc.load_bands(a.sim_dir)
    rng = random.Random(RNG_SEED)
    md = meta(a.sim_dir, sim)
    a.out.mkdir(parents=True, exist_ok=True)
    fixtures = {"p01_pref_list": p01(sim), "p02_distributions": p02(sim), "p03_apportion": p03(sim, rng),
                "p04_surplus_offerable": p04(sim, rng), "p05_listed_view": p05(sim, rng),
                "p10_bands": p10(bands, rng), "p08_whole_runs": p08(sim)}
    for name, cases in fixtures.items():
        (a.out / f"{name}.json").write_text(json.dumps(dict(meta=md, cases=cases), indent=1), encoding="utf-8")
        n = len(cases["cases"]) if isinstance(cases, dict) else len(cases)
        print(f"{name}: {n} cases")


if __name__ == "__main__":
    main()
