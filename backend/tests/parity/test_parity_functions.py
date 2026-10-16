"""Golden parity, function level: P-01, P-02, P-03, P-04, P-05, P-10 (docs/TESTING.md section 2).
These need only the committed fixtures, not the simulator."""
import pytest

from app.core import finder, groups, stock
from golden_common import load_fixture

pytestmark = pytest.mark.parity


def test_p01_pref_list():
    for c in load_fixture("p01_pref_list")["cases"]:
        assert groups.pref_list(c["input"]["g"], c["input"]["policy"]) == c["expected"], c["input"]


def test_p02_distributions_exact():
    exp = {c["input"]: c["expected"] for c in load_fixture("p02_distributions")["cases"]}
    assert groups.DIST_WEST == exp["DIST_WEST"]
    assert groups.DIST_NORTH == exp["DIST_NORTH"]


def test_p03_apportion():
    for c in load_fixture("p03_apportion")["cases"]:
        assert stock.apportion(c["input"]["total"], c["input"]["w"]) == c["expected"], c["input"]


def test_p04_surplus_and_offerable():
    for c in load_fixture("p04_surplus_offerable")["cases"]:
        i = c["input"]
        dmean_g = i["dmean"] * i["wd"][i["g"]]
        rems = sorted(r for r, f, g in i["units"] if g == i["g"])
        assert stock.surplus_near(rems, dmean_g) == c["expected"]["surplus"], i
        assert stock.own_offerable(i["units"], i["g"], dmean_g) == c["expected"]["offerable"], i


def test_p05_listed_view():
    for c in load_fixture("p05_listed_view")["cases"]:
        i = c["input"]
        snap = [tuple(x) for x in i["snap"]]
        assert stock.listed_view(snap, i["snap_day"], i["day"], i["out_since"], 8) == c["expected"], i


def test_p10_band_thresholds_and_cases():
    fx = load_fixture("p10_bands")["cases"]
    assert [list(b) for b in finder.BANDS] == fx["thresholds"]
    for c in fx["cases"]:
        assert finder.band(c["input"]) == c["expected"], c["input"]
