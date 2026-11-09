import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

from ..model import params as P
from ..optimizer.objective import load_layout
from .runner import run_many

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "results/runs"
SEEDS = tuple(range(1001, 1031))
CONDITIONS = [
    # nombre, montaje, aforo, media de atención, parte del diseño pedido
    ("Base perimetral", "base", 500, 16.4, True),
    ("Propuesta PSO", "pso", 500, 16.4, True),
    ("Sensibilidad sobrecupo", "pso", 600, 16.4, True),
    ("Sensibilidad terminal", "pso", 500, 24.6, True),
    ("Base con sobrecupo", "base", 600, 16.4, False),
    ("Base con terminal lenta", "base", 500, 24.6, False),
]
METRICS = [("d_max", "Densidad pico (p/m2)"), ("t95", "T95 (s)"), ("t_all", "Salida total (s)"),
           ("peak_flow", "Flujo pico (p/(m s))"), ("left_unserved", "Salieron sin comprar")]
SHORT = {"Base perimetral": "Base", "Propuesta PSO": "PSO", "Sensibilidad sobrecupo": "PSO 600",
         "Sensibilidad terminal": "PSO 24.6 s", "Base con sobrecupo": "Base 600", "Base con terminal lenta": "Base 24.6 s"}
PAIRS = [("Base perimetral", "Propuesta PSO"), ("Base con sobrecupo", "Sensibilidad sobrecupo"),
         ("Base con terminal lenta", "Sensibilidad terminal"), ("Propuesta PSO", "Sensibilidad sobrecupo"),
         ("Propuesta PSO", "Sensibilidad terminal")]


def run_matrix(seeds=SEEDS):
    jobs, keys = [], []
    for name, lay, n, service, _ in CONDITIONS:
        layout = load_layout(lay)
        for s in seeds:
            jobs.append((layout, n, service, s, None))
            keys.append((name, s))
    out = run_many(jobs)
    RUNS.mkdir(parents=True, exist_ok=True)
    rows, curves, maps = [], {}, {}
    for (name, s), r in zip(keys, out):
        rows.append([name, s] + [r[k] for k, _ in METRICS] + [r["evacuated"], int(r["conservation"]), r["crossings"]])
        n = dict((c[0], c[2]) for c in CONDITIONS)[name]
        curves.setdefault(name, []).append(np.asarray(r["n_out"]) / n)
        maps.setdefault(name, []).append(r["dens_map"])
    with open(ROOT / "results/tables/experimento_corridas.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["condicion", "semilla"] + [k for k, _ in METRICS]
                                  + ["evacuados", "conservacion_ok", "cruces_de_muro"], *rows])
    length = max(len(c) for v in curves.values() for c in v)
    curve = {k: np.array([np.pad(c, (0, length - len(c)), mode="edge") for c in v]) for k, v in curves.items()}
    np.savez_compressed(RUNS / "experimento.npz", names=list(curve), curves=np.array(list(curve.values())),
                        maps=np.array([np.array(maps[k]).mean(0) for k in curve]),
                        maps_max=np.array([np.array(maps[k]).max(0) for k in curve]))
    return load_runs()


def load_runs():
    with open(ROOT / "results/tables/experimento_corridas.csv") as fh:
        rows = list(csv.DictReader(fh))
    data = {}
    for r in rows:
        data.setdefault(r["condicion"], []).append(r)
    return {k: {m: np.array([float(x[m]) for x in v]) for m in list(v[0])[1:]} for k, v in data.items()}


def ci(x):
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), x.std(ddof=1), h


def summarize(data=None):
    from ..visualization.tables import save
    data = data or load_runs()
    cond_rows = [[name, "Fijo lateral" if lay == "base" else "Optimizado", n, service, len(SEEDS),
                  "sí" if main else "adicional"] for name, lay, n, service, main in CONDITIONS]
    save("condiciones", ["Condición", "Mobiliario", "Aforo", "Media servicio (s)", "Réplicas", "Diseño"], cond_rows)
    rows = []
    for name, *_ in CONDITIONS:
        d = data[name]
        for k, label in METRICS[:2] + METRICS[3:]:
            m, s, h = ci(d[k])
            rows.append([name, label, round(m, 3), round(s, 3), f"[{m - h:.3f}, {m + h:.3f}]"])
    save("resumen_condiciones", ["Condición", "Métrica", "Media", "Desv. est.", "IC 95%"], rows)
    prow = []
    for a, b in PAIRS:
        for k, label in (("d_max", "Dmax (p/m2)"), ("t95", "T95 (s)")):
            x, y = data[a][k], data[b][k]
            dm, _, h = ci(y - x)
            p = stats.ttest_rel(y, x).pvalue
            prow.append([f"{SHORT[b]} vs {SHORT[a]}", label, round(float(x.mean()), 3), round(float(y.mean()), 3),
                         round(float(dm), 3), f"[{dm - h:.3f}, {dm + h:.3f}]",
                         f"{100 * dm / x.mean():+.1f}%", f"{p:.4f}" if p >= 1e-4 else "< 0.0001",
                         round(float(np.corrcoef(x, y)[0, 1]), 2)])
    save("comparaciones", ["B vs A", "Métrica", "Media A", "Media B", "B - A", "IC 95% de B - A", "Cambio",
                           "p (t pareada)", "Corr."], prow)
    total = sum(len(v["conservacion_ok"]) for v in data.values())
    checks = [["Corridas totales", total],
              ["Corridas con conservación exacta", int(sum(v["conservacion_ok"].sum() for v in data.values()))],
              ["Cruces de muro en todas las corridas", int(sum(v["cruces_de_muro"].sum() for v in data.values()))],
              ["Corridas en que no salieron todos", int(sum((v["evacuados"] < max(c[2] for c in CONDITIONS if c[0] == k))
                                                            .sum() for k, v in data.items()))],
              ["Corridas con densidad pico mayor a 4 p/m2", int(sum((v["d_max"] > P.DENS_LIMIT).sum() for v in data.values()))]]
    save("verificacion_experimento", ["Comprobación", "Valor"], checks)
    return rows, prow


if __name__ == "__main__":
    import time
    t = time.time()
    run_matrix()
    summarize()
    print(f"{time.time() - t:.0f} s")
    print(open(ROOT / "results/tables/comparaciones.csv").read())
