import numpy as np
import pytest

from src.model.geometry import Venue, baseline_layout
from src.model.grid import Grid
from src.model.validator import check_layout


@pytest.fixture(scope="module")
def setup():
    v = Venue()
    return Grid(v), baseline_layout(v)


def with_bar(base, i, xy):
    bars = list(base["bars"])
    bars[i] = xy
    return {"bars": bars, "fences": base["fences"]}


def test_baseline_is_valid(setup):
    grid, base = setup
    ok, penalty, _ = check_layout(grid, base)
    assert ok and penalty == 0


def test_rejects_overlap(setup):
    grid, base = setup
    ok, _, v = check_layout(grid, with_bar(base, 1, base["bars"][0]))
    assert not ok and v["traslape"] > 0


def test_rejects_outside(setup):
    grid, base = setup
    ok, _, v = check_layout(grid, with_bar(base, 0, (79.5, 40.0)))
    assert not ok and v["fuera_del_recinto"] > 0


def test_rejects_exit_radius(setup):
    grid, base = setup
    g = Venue().gates[1]
    c = (g[:2] + g[2:4]) / 2 - 3 * g[4:]
    ok, _, v = check_layout(grid, with_bar(base, 0, tuple(c)))
    assert not ok and v["radio_de_salida"] > 0


def test_rejects_blocked_route(setup):
    grid, base = setup
    corner = {"bars": base["bars"], "fences": [(2.0, 44.0, 0.0), (5.0, 47.0, np.pi / 2)]}
    ok, _, v = check_layout(grid, corner)
    assert not ok and v["area_sin_salida"] > 0
