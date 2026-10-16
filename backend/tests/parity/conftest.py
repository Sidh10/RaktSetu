import pytest

import golden_common as gc
from golden_common import load_fixture


@pytest.fixture(scope="session")
def sim():
    """The read-only simulator module, only for P-08's random draws. Fails if it changed since the fixtures."""
    d = gc.sim_dir()
    if not (d / gc.SIM_FILE).exists():
        pytest.skip(f"simulator not found at {d}; set RAKTSETU_SIM_DIR")
    want = load_fixture("p08_whole_runs")["meta"]["sim_file_sha256"]
    got = gc.sha256_file(d / gc.SIM_FILE)
    if got != want:
        pytest.fail(f"simulator changed since fixtures were generated ({got[:12]} != {want[:12]}); "
                    "investigate before regenerating (CLAUDE.md, golden parity)")
    return gc.load_sim(d)
