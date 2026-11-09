import json
import os
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..model import params as P
from . import calibration as C
from .experiments import load_runs
from .runner import make_agents, simulate

WINDOW = (-2.0, -1.5, 2.0, 0.0)   # zona frente a la entrada del cuello de botella que cubre la cámara
NFPA_LEVEL = 0.005                # m por persona en componentes a nivel (NFPA 101, Tabla 7.3.3.1)
NFPA_MAIN_SHARE = 2 / 3           # salida principal con público de pie (NFPA 101, 12.2.3.6)
SFPE_K, SFPE_A, SFPE_BL = 1.40, 0.266, 0.15


def _cells(dh=P.DENS_H):
    x0, y0, x1, y1 = WINDOW
    xs = np.arange(x0, x1, dh) + dh / 2
    ys = np.arange(y0, y1, dh) + dh / 2
    return np.meshgrid(xs, ys, indexing="ij")


def _peak(points, X, Y):
    s2 = 2 * P.DENS_SIGMA ** 2
    d = np.exp(-((X[..., None] - points[:, 0]) ** 2 + (Y[..., None] - points[:, 1]) ** 2) / s2).sum(-1)
    return d.max() / (np.pi * s2)


def real_density():
    runs = json.loads((C.RAW / C.FILES[0]).read_text())["experiment"]["parameters"]
    X, Y = _cells()
    step = int(C.FPS * P.SAMPLE_DT)
    out = {}
    with zipfile.ZipFile(C.RAW / C.FILES[1]) as z:
        for r in runs:
            if not (r["run_name"].startswith("b") and r["run_name"][1:].isdigit()):
                continue
            d = np.loadtxt(z.open(f"{r['run_name']}.txt"))
            frames = np.unique(d[:, 1])[::step]
            out[float(r["parameters"]["bottleneck_width"])] = max(_peak(d[d[:, 1] == f][:, 2:4] / 100, X, Y)
                                                                  for f in frames)
    return out


def sim_density(args):
    b, n, seed = args
    scene, box = C.bottleneck(b, n)
    x0, y0, h = scene["dens0"]
    nx, ny = scene["walk"].shape
    xc = x0 + h * (np.arange(nx) + 0.5)
    yc = y0 + h * (np.arange(ny) + 0.5)
    XC, YC = np.meshgrid(xc, yc, indexing="ij")
    scene["walk"] = (XC >= WINDOW[0]) & (XC <= WINDOW[2]) & (YC >= WINDOW[1]) & (YC <= WINDOW[3])
    agents = make_agents(scene, n, P.SERVICE_MEAN, seed, box=box, min_dist=0.55)
    return float(simulate(scene, agents, t_max=400.0)["dens"].max())


def density_comparison(seeds=C.SEEDS):
    from ..visualization.tables import save
    real = real_density()
    flows = {float(r[1]): r for r in (l.split(",") for l in C.FLOWS.read_text().splitlines()[1:])}
    jobs = [(b, int(flows[b][2]), s) for b in real for s in seeds]
    with ProcessPoolExecutor(max(1, (os.cpu_count() or 2) - 2)) as ex:
        sim = np.array(list(ex.map(sim_density, jobs))).reshape(len(real), len(seeds))
    rows = [[b, round(real[b], 3), round(float(sim[i].mean()), 3), round(float(sim[i].std(ddof=1)), 3),
             round(float(sim[i].mean() - real[b]), 3)] for i, b in enumerate(real)]
    save("densidad_julich", ["Ancho (m)", "Real (p/m2)", "Modelo (p/m2)", "Desv. modelo", "Modelo - real"], rows)
    return np.array(list(real.values())), sim.mean(1)


def correspondence():
    from ..visualization.tables import save
    cal = json.loads(P.CALIBRATION.read_text())
    real_d, sim_d = density_comparison()
    data = load_runs()
    base, pso = data["Base perimetral"], data["Propuesta PSO"]
    fs_max = SFPE_K / (4 * SFPE_A)
    sfpe = fs_max * (P.GATE_WIDTH - 2 * SFPE_BL) / P.GATE_WIDTH
    width_total = len(P.GATE_X) * P.GATE_WIDTH
    need_total = P.N_AGENTS * NFPA_LEVEL
    need_main = NFPA_MAIN_SHARE * P.N_AGENTS * NFPA_LEVEL

    def change(a, b):
        return [round(b - a, 3), f"{100 * (b - a) / a:+.1f}%"]

    real_js, model_js = np.mean(cal["real"]), np.mean(cal["model_mean"])
    rows = [
        ["Jülich", "Flujo específico estable (p/(m s))", round(real_js, 3), "Real medido", round(model_js, 3), "", "",
         f"{100 * (model_js - real_js) / real_js:+.1f}%"],
        ["Jülich", "Densidad pico frente a la puerta (p/m2)", round(float(real_d.mean()), 3), "Real medido",
         round(float(sim_d.mean()), 3), "", "", f"{100 * (sim_d.mean() - real_d.mean()) / real_d.mean():+.1f}%"],
        ["Cayalá", "Flujo pico por metro de portón (p/(m s))", f"{real_js:.2f} / {sfpe:.2f}", "Jülich / SFPE",
         round(float(base["peak_flow"].mean()), 3), round(float(pso["peak_flow"].mean()), 3),
         *change(base["peak_flow"].mean(), pso["peak_flow"].mean())],
        ["Cayalá", "Densidad pico (p/m2)", "sin medición", "", round(float(base["d_max"].mean()), 3),
         round(float(pso["d_max"].mean()), 3), *change(base["d_max"].mean(), pso["d_max"].mean())],
        ["Cayalá", "T95 (s)", "sin medición", "", round(float(base["t95"].mean()), 1), round(float(pso["t95"].mean()), 1),
         *change(base["t95"].mean(), pso["t95"].mean())],
        ["Cayalá", "Ancho de salida total (m)", f"{need_total:.2f} requerido", "NFPA 101", width_total, width_total,
         0, "+0.0%"],
        ["Cayalá", "Ancho de la salida principal (m)", f"{need_main:.2f} requerido", "NFPA 101", P.GATE_WIDTH,
         P.GATE_WIDTH, 0, "+0.0%"],
    ]
    adjusted_density(real_d.mean() / sim_d.mean(), (real_d / sim_d).min(), (real_d / sim_d).max(), data)
    path = save("correspondencia", ["Escenario", "Métrica", "Referencia", "Tipo de referencia", "Modelo base",
                                    "Modelo PSO", "PSO - base", "Cambio"], rows, align="llrlrrrr")
    return path, {"sfpe_per_m": sfpe, "fs_max": fs_max, "need_total": need_total, "need_main": need_main}


def adjusted_density(k, k_lo, k_hi, data):
    from ..visualization.tables import save
    from .experiments import CONDITIONS
    rows = []
    for c, *_ in CONDITIONS:
        x = data[c]["d_max"]
        rows.append([c, round(float(x.mean()), 2), round(float(k * x.mean()), 2),
                     f"{k_lo * x.mean():.2f} a {k_hi * x.mean():.2f}", round(float(k * x.max()), 2),
                     int((k * x > P.DENS_LIMIT).sum())])
    return save("densidad_ajustada", ["Condición", "Dmax modelo", "Dmax ajustada", "Rango ajustado",
                                      "Máximo ajustado", f"Corridas sobre {P.DENS_LIMIT:.0f}"], rows)


if __name__ == "__main__":
    path, extra = correspondence()
    print(path.read_text())
    print(extra)
    print(open(C.ROOT / "results/tables/densidad_julich.csv").read())
