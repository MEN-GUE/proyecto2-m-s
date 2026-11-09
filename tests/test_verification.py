from src.model import params as P
from src.simulation import checks


def test_conservation():
    r = checks.conservation()
    assert r["max_error"] == 0 and r["all_out"]


def test_no_wall_crossing():
    for r in checks.walls():
        assert r["crossings"] == 0 and r["outside"] == 0
        assert r["min_wall_distance"] >= P.RADIUS_MIN - 1e-6


def test_free_flow_time():
    assert checks.free_flow()["error"] <= 2 * P.DT
