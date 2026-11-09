import numpy as np

from . import params as P
from .grid import H

CELL = H * H
FENCE_HALF_THICK = 0.15
LABELS = {"fuera_del_recinto": "fuera del recinto", "traslape": "traslape o paso angosto",
          "radio_de_salida": "radio libre de salida", "zona_de_fila": "zona de fila",
          "area_sin_salida": "área sin salida"}


def footprints(layout, obstacle_d):
    n_bars = len(layout["bars"])
    return [d <= (0 if i < n_bars else FENCE_HALF_THICK) for i, d in enumerate(obstacle_d)]


def check_layout(grid, layout):
    od = grid.obstacle_distances(layout)
    fp = footprints(layout, od)
    v = {}
    v["fuera_del_recinto"] = sum((f & ~grid.domain).sum() for f in fp) * CELL
    v["traslape"] = sum(((od[i] < P.MIN_GAP / 2) & (od[j] < P.MIN_GAP / 2)).sum()
                        for i in range(len(od)) for j in range(i + 1, len(od))) * CELL
    v["radio_de_salida"] = sum((f & (grid.gate_d < P.EXIT_CLEAR_RADIUS)).sum() for f in fp) * CELL
    queue = 0
    for i, (cx, cy) in enumerate(layout["bars"]):
        zone = ((grid.x >= cx + P.BAR_W / 2) & (grid.x <= cx + P.BAR_W / 2 + P.QUEUE_ZONE)
                & (np.abs(grid.y - cy) <= P.BAR_H / 2))
        bad = ~grid.domain | (grid.wall_d < 0.3) | (grid.gate_d < P.EXIT_CLEAR_RADIUS)
        for j, d in enumerate(od):
            if j != i:
                bad |= d < 0.3
        queue += (zone & bad).sum()
    v["zona_de_fila"] = queue * CELL
    free = grid.free(od, P.MIN_GAP / 2)
    dist = grid.distance_to_exit(free)
    v["area_sin_salida"] = (free & grid.domain & np.isinf(dist)).sum() * CELL
    v = {k: float(x) for k, x in v.items()}
    penalty = sum(v.values())
    return penalty == 0, penalty, v


def check_density(density_map, walkable, limit=4.0):
    peak = float(density_map[walkable].max())
    return peak <= limit, peak
