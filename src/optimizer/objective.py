import numpy as np

from ..model import params as P
from ..model.validator import LABELS, check_layout
from .pso import pso

FENCE_DEPTH, FENCE_BOX = 9.0, 8.0
PERIODIC = np.array([False] * 8 + [False, False, True] * 2)


def bounds(venue):
    x0, y0, x1, y1 = venue.domain.bounds
    lo = [x0 + P.BAR_W / 2, y0 + P.BAR_H / 2] * 4
    hi = [x1 - P.BAR_W / 2, y1 - P.BAR_H / 2] * 4
    for g in venue.gates:
        c = (g[:2] + g[2:4]) / 2 - FENCE_DEPTH * g[4:]
        lo += [c[0] - FENCE_BOX, c[1] - FENCE_BOX, -np.pi / 2]
        hi += [c[0] + FENCE_BOX, c[1] + FENCE_BOX, np.pi / 2]
    return np.array(lo), np.array(hi)


def decode(x):
    return {"bars": [tuple(b) for b in np.reshape(x[:8], (4, 2))],
            "fences": [tuple(f) for f in np.reshape(x[8:14], (2, 3))]}


def encode(layout):
    return np.concatenate([np.ravel(layout["bars"]), np.ravel(layout["fences"])])


def save_bounds(venue):
    from ..visualization.tables import save
    lo, hi = bounds(venue)
    names = [f"Barra {i} {c} (m)" for i in range(1, 5) for c in "xy"]
    names += [f"Valla {i} {c}" for i in (1, 2) for c in ("x (m)", "y (m)", "ángulo (rad)")]
    return save("limites_pso", ["Variable", "Mínimo", "Máximo"],
                [[n, round(a, 2), round(b, 2)] for n, a, b in zip(names, lo, hi)])


def feasibility_study(venue, grid, n=1000, seed=7):
    from ..visualization.tables import save
    lo, hi = bounds(venue)
    rng = np.random.default_rng(seed)
    kinds = {}
    feasible = 0
    for x in lo + rng.random((n, len(lo))) * (hi - lo):
        ok, _, v = check_layout(grid, decode(x))
        feasible += ok
        for k, val in v.items():
            kinds[k] = kinds.get(k, 0) + (val > 0)
    _, best, hist = pso(lambda X: [check_layout(grid, decode(x))[1] for x in X], lo, hi,
                        seed=seed, periodic=PERIODIC, tol=0, patience=99)
    first = next((h["iter"] for h in hist if h["best"] == 0), None)
    rows = [["Montajes al azar evaluados", n], ["Montajes válidos (%)", round(100 * feasible / n, 1)]]
    rows += [[f"Con violación de {LABELS[k]} (%)", round(100 * c / n, 1)] for k, c in kinds.items()]
    rows += [["Iteración en que PSO halla un montaje válido", first if first is not None else "no"]]
    return save("factibilidad", ["Indicador", "Valor"], rows)


if __name__ == "__main__":
    from ..model.geometry import Venue
    from ..model.grid import Grid
    v = Venue()
    save_bounds(v)
    print(feasibility_study(v, Grid(v)).read_text())
