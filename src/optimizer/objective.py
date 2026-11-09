import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from ..model import params as P
from ..model.geometry import baseline_layout
from ..model.validator import LABELS, check_layout
from ..simulation.runner import build_scene, context, run
from .pso import pso

ROOT = Path(__file__).resolve().parents[2]
FENCE_DEPTH, FENCE_BOX = 9.0, 8.0
PERIODIC = np.array([False] * 8 + [False, False, True] * 2)
W_D, W_T = 0.6, 0.4
J_WORST, LAMBDA_GEOM, LAMBDA_DENS = 10.0, 0.05, 10.0
SEARCH_SEEDS = (1, 2, 3)
SELECT_SEEDS = tuple(range(2001, 2011))
RESTARTS = (11, 12, 13)


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


def evaluate(args):
    layout, seeds, n, service = args
    venue, grid = context()
    scene = build_scene(venue, grid, layout)
    out = [run(layout, n, service, s, scene=scene) for s in seeds]
    return [[r["d_max"], min(r["t95"], P.T_MAX), float(r["dens_map"][scene["walk"]].max()),
             r["left_unserved"]] for r in out]


class Objective:
    def __init__(self, grid, pool, n=P.N_AGENTS, service=P.SERVICE_MEAN, seeds=SEARCH_SEEDS):
        self.grid, self.pool, self.n, self.service, self.seeds = grid, pool, n, service, seeds
        base = np.array(evaluate((baseline_layout(context()[0]), seeds, n, service)))
        self.d_base, self.t_base = base[:, 0].mean(), base[:, 1].mean()

    def score(self, d, t):
        return W_D * d / self.d_base + W_T * t / self.t_base + LAMBDA_DENS * max(0.0, d - P.DENS_LIMIT) ** 2

    def __call__(self, X):
        layouts = [decode(x) for x in X]
        checks = [check_layout(self.grid, lay) for lay in layouts]
        J = [J_WORST + LAMBDA_GEOM * c[1] for c in checks]
        valid = [i for i, c in enumerate(checks) if c[0]]
        jobs = [(layouts[i], self.seeds, self.n, self.service) for i in valid]
        for i, r in zip(valid, self.pool.map(evaluate, jobs)):
            r = np.array(r)
            J[i] = self.score(r[:, 0].mean(), r[:, 1].mean())
        return J


def feasible_samples(grid, lo, hi, rng, k):
    out = []
    while len(out) < k:
        x = lo + rng.random(len(lo)) * (hi - lo)
        if check_layout(grid, decode(x))[0]:
            out.append(x)
    return np.array(out)


def optimize(restarts=RESTARTS, iters=25, full_seed=RESTARTS[-1], workers=None):
    from ..visualization.tables import save
    venue, grid = context()
    lo, hi = bounds(venue)
    logs = ROOT / "results/logs"
    logs.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers or max(1, (os.cpu_count() or 2) - 2)) as pool:
        obj = Objective(grid, pool)
        runs = []
        for seed, patience in [(s, 5) for s in restarts] + [(full_seed, iters + 1)]:
            x0 = feasible_samples(grid, lo, hi, np.random.default_rng(seed), 12)
            g, fg, hist = pso(obj, lo, hi, iters=iters, seed=seed, periodic=PERIODIC, x0=x0, patience=patience)
            name = f"{seed}" if patience == 5 else f"{seed} sin paro"
            (logs / f"pso_reinicio_{name.replace(' ', '_')}.json").write_text(json.dumps(
                {"name": name, "best": g.tolist(), "J": fg, "d_base": obj.d_base, "t_base": obj.t_base,
                 "history": hist}))
            runs.append((name, g, fg, hist))
        sel = Objective(grid, pool, seeds=SELECT_SEEDS)
        finals = list(pool.map(evaluate, [(decode(g), SELECT_SEEDS, P.N_AGENTS, P.SERVICE_MEAN) for _, g, _, _ in runs]))
    rows, best = [], None
    for (name, g, fg, hist), r in zip(runs, finals):
        r = np.array(r)
        js = sel.score(r[:, 0].mean(), r[:, 1].mean())
        bad = 100 * np.mean([np.mean(np.array(h["values"]) >= J_WORST) for h in hist[1:]])
        rows.append([name, round(fg, 4), hist[-1]["iter"], round(hist[-1]["diversity"], 3), round(float(bad), 1),
                     round(js, 4), round(float(r[:, 0].mean()), 3), round(float(r[:, 1].mean()), 1)])
        if "sin paro" not in name and (best is None or js < best[1]):
            best = (name, js, g)
    rows.insert(0, ["Base", 1.0, "", "", "", 1.0, round(sel.d_base, 3), round(sel.t_base, 1)])
    save("pso_reinicios", ["Corrida", "J búsqueda", "Iteraciones", "Diversidad final", "Inválidas (%)",
                           "J selección", "Dmax medio", "T95 medio (s)"], rows)
    layout = decode(best[2])
    (ROOT / "results/layouts").mkdir(parents=True, exist_ok=True)
    (ROOT / "results/layouts/pso.json").write_text(json.dumps(
        {"bars": layout["bars"], "fences": layout["fences"], "x": best[2].tolist(), "restart": best[0],
         "J_select": best[1], "d_base_select": sel.d_base, "t_base_select": sel.t_base}, indent=1))
    objective_table()
    return layout, rows


def objective_table():
    from ..visualization.tables import save
    log = json.loads(next((ROOT / "results/logs").glob("pso_reinicio_*.json")).read_text())
    rows = [["Peso de la densidad", "$w_D$", W_D], ["Peso del tiempo", "$w_T$", W_T],
            ["Densidad base (semillas 1 a 3, p/m2)", "$D_{base}$", round(log["d_base"], 3)],
            ["T95 base (semillas 1 a 3, s)", "$T_{base}$", round(log["t_base"], 1)],
            ["Penalización geométrica (por m2)", "$\\lambda_{geom}$", LAMBDA_GEOM],
            ["Penalización de densidad", "$\\lambda_{dens}$", LAMBDA_DENS],
            ["Valor fijo para montajes inválidos", "$J_{inv}$", J_WORST],
            ["Semillas de búsqueda", "", "1, 2, 3"], ["Semillas de selección", "", "2001 a 2010"],
            ["Semillas de los reinicios del enjambre", "", ", ".join(map(str, RESTARTS))]]
    return save("parametros_objetivo", ["Elemento", "Símbolo", "Valor"], rows)


def load_layout(name="pso"):
    if name == "base":
        return baseline_layout(context()[0])
    d = json.loads((ROOT / f"results/layouts/{name}.json").read_text())
    return {"bars": [tuple(b) for b in d["bars"]], "fences": [tuple(f) for f in d["fences"]]}


def verify_constraints(seeds=SELECT_SEEDS, workers=None):
    from ..visualization.tables import save
    _, grid = context()
    layouts = {"Base": load_layout("base"), "PSO": load_layout("pso")}
    checks = {k: check_layout(grid, v)[2] for k, v in layouts.items()}
    with ProcessPoolExecutor(workers or max(1, (os.cpu_count() or 2) - 2)) as pool:
        dens = {k: np.array([r[0] for r in pool.map(evaluate, [(v, (s,), P.N_AGENTS, P.SERVICE_MEAN) for s in seeds])])
                for k, v in layouts.items()}
    rows = [[f"Violación por {LABELS[k]} (m2)", checks["Base"][k], checks["PSO"][k]] for k in LABELS]
    rows += [["Densidad máxima en celdas transitables (p/m2)", round(float(dens["Base"][:, 2].max()), 3),
              round(float(dens["PSO"][:, 2].max()), 3)],
             [f"Corridas con densidad de hasta {P.DENS_LIMIT} p/m2", f"{int((dens['Base'][:, 2] <= P.DENS_LIMIT).sum())} de {len(seeds)}",
              f"{int((dens['PSO'][:, 2] <= P.DENS_LIMIT).sum())} de {len(seeds)}"]]
    ok = {k: all(v == 0 for v in checks[k].values()) and (dens[k][:, 2] <= P.DENS_LIMIT).all() for k in layouts}
    rows.append(["Cumple todas las restricciones", "sí" if ok["Base"] else "no", "sí" if ok["PSO"] else "no"])
    return save("restricciones", ["Restricción", "Base", "PSO"], rows)


if __name__ == "__main__":
    import sys
    if "--factibilidad" in sys.argv:
        v, g = context()
        save_bounds(v)
        print(feasibility_study(v, g).read_text())
    else:
        layout, rows = optimize()
        print(json.dumps(layout), *rows, sep="\n")
        print(verify_constraints().read_text())
