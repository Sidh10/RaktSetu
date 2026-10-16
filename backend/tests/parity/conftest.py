import os

import pytest

import golden_common as gc
from golden_common import load_fixture

_MISSING_SIM = {"dir": None, "skipped": 0}


def _require_sim() -> bool:
    return os.environ.get("RAKTSETU_REQUIRE_SIM", "").lower() in ("1", "true", "yes")


@pytest.fixture(scope="session")
def sim():
    """The read-only simulator module, only for P-08's random draws. Fails if it changed since the fixtures.

    Missing simulator: the whole-run tests are skipped and a warning is printed in the summary, or they FAIL when
    RAKTSETU_REQUIRE_SIM=1 (set by `make test-parity`)."""
    d = gc.sim_dir()
    if not (d / gc.SIM_FILE).exists():
        msg = (f"simulator not found at {d}; put RaktSetu_simulator_and_prototype/ next to raktsetu-app/ "
               "or set RAKTSETU_SIM_DIR to its sim_v3 folder")
        if _require_sim():
            pytest.fail(msg + " (RAKTSETU_REQUIRE_SIM=1)", pytrace=False)
        _MISSING_SIM["dir"] = str(d)
        pytest.skip(msg)
    want = load_fixture("p08_whole_runs")["meta"]["sim_file_sha256"]
    got = gc.sha256_file(d / gc.SIM_FILE)
    if got != want:
        pytest.fail(f"simulator changed since fixtures were generated ({got[:12]} != {want[:12]}); "
                    "investigate before regenerating (CLAUDE.md, golden parity)")
    return gc.load_sim(d)


def pytest_runtest_logreport(report):
    if report.skipped and "test_parity_whole_runs" in report.nodeid:
        _MISSING_SIM["skipped"] += 1


def pytest_terminal_summary(terminalreporter):
    if _MISSING_SIM["skipped"]:
        tr = terminalreporter
        tr.section("WHOLE-RUN PARITY NOT CHECKED", sep="!", red=True, bold=True)
        tr.write_line(f"{_MISSING_SIM['skipped']} whole-run parity tests (P-08) were SKIPPED: the simulator was not "
                      f"found at {_MISSING_SIM['dir']}.", red=True, bold=True)
        tr.write_line("A green run here does NOT show that the prototype reproduces the simulator. Put "
                      "RaktSetu_simulator_and_prototype/ next to raktsetu-app/, or set RAKTSETU_SIM_DIR, and rerun "
                      "(`make test-parity` fails instead of skipping).", red=True)
