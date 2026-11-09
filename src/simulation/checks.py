import math

import numpy as np

from ..model import params as P
from ..model.geometry import baseline_layout
from ..model.grid import inside_polygon, seg_distance
from ..model.validator import check_layout
from .runner import build_scene, context, make_agents, simulate

FENCED = [(16.0, 12.0, math.pi / 2), (70.0, 33.0, 0.0)]


def conservation(n=300, seed=1):
    venue, grid = context()
    scene = build_scene(venue, grid, baseline_layout(venue))
    res = simulate(scene, make_agents(scene, n, P.SERVICE_MEAN, seed))
    return {"max_error": int(np.abs(res["n_in"] + res["n_out"] - n).max()),
            "all_out": bool(res["n_out"][-1] == n and np.isfinite(res["t_exit"]).all())}


def walls(n=500, seed=2):
    venue, grid = context()
    base = baseline_layout(venue)
    out = []
    for name, layout in (("base", base), ("con vallas", {"bars": base["bars"], "fences": FENCED})):
        assert check_layout(grid, layout)[0]
        scene = build_scene(venue, grid, layout)
        res = simulate(scene, make_agents(scene, n, P.SERVICE_MEAN, seed), record=True)
        min_d, outside = np.inf, 0
        for frame in res["frames"]:
            p = frame[frame[:, 0] > -100]
            if len(p) == 0:
                continue
            min_d = min(min_d, seg_distance(p[:, 0], p[:, 1], scene["walls"]).min())
            gate_d = np.min([np.hypot(*(p - (g[:2] + g[2:4]) / 2).T) for g in scene["gates"]], axis=0)
            outside += int((~inside_polygon(p[:, 0], p[:, 1], scene["domain"]) & (gate_d >= 3)).sum())
        out.append({"layout": name, "crossings": int(res["crossings"]), "min_wall_distance": float(min_d),
                    "outside": outside})
    return out


def free_flow(length=60.0, width=20.0, tau=0.5, v0=1.34, x0=5.0):
    walls_ = np.array([[0, 0, length, 0], [0, width, length, width], [0, 0, 0, width]], float)
    xs = -2 + 0.25 * (np.arange(int((length + 4) / 0.25)) + 0.5)
    fdist = np.repeat((length - xs)[:, None], int((width + 4) / 0.25), 1)[None]
    fdir = np.zeros((*fdist.shape, 2))
    fdir[..., 0] = 1.0
    scene = {"walls": walls_, "gates": np.array([[length, 0, length, width, 1, 0]], float), "fdist": fdist,
             "fdir": fdir, "sp": np.zeros((0, 2)), "qdir": np.zeros((0, 2)), "line_field": np.zeros(0, np.int64),
             "nav0": np.array([-2.0, -2.0, 0.25]), "dens0": np.array([0.0, 0.0, 0.5]),
             "walk": np.ones((int(length / 0.5), int(width / 0.5)), bool)}
    agents = {"pos": np.array([[x0, width / 2]]), "v0": np.array([v0]), "rad": np.array([0.25]),
              "line": np.array([-1]), "dur": np.zeros(1)}
    sim = simulate(scene, agents, tau=tau, t_max=100.0)["t_exit"][0]
    dist, lo, hi = length + P.EXIT_MARGIN - x0, 0.0, 100.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if v0 * mid - v0 * tau * (1 - math.exp(-mid / tau)) < dist else (lo, mid)
    return {"simulated": float(sim), "exact": lo, "error": float(abs(sim - lo))}


def summary():
    from ..visualization.tables import save
    c, w, f = conservation(), walls(), free_flow()
    rows = [["Conservación: mayor error en N adentro + N evacuados - N", c["max_error"]],
            ["Conservación: todos salen", "sí" if c["all_out"] else "no"]]
    for r in w:
        rows += [[f"Muros ({r['layout']}): cruces de muro", r["crossings"]],
                 [f"Muros ({r['layout']}): distancia mínima a un muro (m)", round(r["min_wall_distance"], 3)],
                 [f"Muros ({r['layout']}): posiciones fuera del recinto", r["outside"]]]
    rows += [["Flujo libre: tiempo exacto (s)", round(f["exact"], 3)],
             ["Flujo libre: tiempo simulado (s)", round(f["simulated"], 3)],
             ["Flujo libre: diferencia (s)", round(f["error"], 3)]]
    return save("verificacion", ["Prueba", "Resultado"], rows)


if __name__ == "__main__":
    print(summary().read_text())
