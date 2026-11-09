import json
import os
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from shapely.geometry import Polygon

from ..model import params as P
from ..model.grid import Grid
from .runner import build_scene, make_agents, simulate

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/julich/raw"
BASE_URL = "https://ped.fz-juelich.de/experiments/2006.11.27_Duesseldorf_Casern/data/eg/"
FILES = ["2006bottleneck2_metadata.json", "2006bottleneck2_trajectories_txt.zip"]
FLOWS = ROOT / "data/julich/julich_flows.csv"
FPS, FLOOR, LENGTH, DIST = 25, 7.0, 4.0, 4.0
RANKS = (20, 150)                # personas usadas para medir el flujo estable
TAUS = np.round(np.arange(0.3, 1.001, 0.05), 2)
SEEDS = (1, 2, 3, 4, 5)


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        if not (RAW / f).exists():
            req = urllib.request.Request(BASE_URL + f, headers={"User-Agent": "uvg-cc3074-proyecto2"})
            (RAW / f).write_bytes(urllib.request.urlopen(req, timeout=300).read())


def steady_flow(times):
    t = np.sort(times)
    a, b = RANKS[0], min(RANKS[1], len(t))
    return (b - a) / (t[b - 1] - t[a - 1])


def real_flows():
    download()
    runs = json.loads((RAW / FILES[0]).read_text())["experiment"]["parameters"]
    rows = []
    with zipfile.ZipFile(RAW / FILES[1]) as z:
        for r in runs:
            p = r["parameters"]
            if not (r["run_name"].startswith("b") and r["run_name"][1:].isdigit()):
                continue
            d = np.loadtxt(z.open(f"{r['run_name']}.txt"))
            times = []
            for i in np.unique(d[:, 0]):
                m = d[:, 0] == i
                y, fr = d[m, 3] / 100, d[m, 1]
                k = np.flatnonzero((y[:-1] < 0) & (y[1:] >= 0))
                if len(k):
                    times.append(fr[k[0]] / FPS)
            b = float(p["bottleneck_width"])
            j = steady_flow(times)
            rows.append([r["run_name"], b, int(p["number_participants"]), round(j, 3), round(j / b, 3)])
    FLOWS.parent.mkdir(parents=True, exist_ok=True)
    FLOWS.write_text("corrida,ancho_m,personas,flujo_p_s,flujo_especifico_p_ms\n"
                     + "\n".join(",".join(map(str, r)) for r in rows) + "\n")
    return rows


def bottleneck(b, n, density=2.0):
    depth = n / (density * (FLOOR - 0.6))
    y0 = -DIST - depth - 1
    h = FLOOR / 2
    domain = Polygon([(-h, y0), (h, y0), (h, 0), (b / 2, 0), (b / 2, LENGTH), (-b / 2, LENGTH), (-b / 2, 0), (-h, 0)])
    c = list(domain.exterior.coords)
    walls = np.array([(*c[i], *c[i + 1]) for i in range(len(c) - 1) if not (c[i][1] == c[i + 1][1] == LENGTH)])
    venue = SimpleNamespace(domain=domain, walls=walls, gates=np.array([[b / 2, LENGTH, -b / 2, LENGTH, 0.0, 1.0]]))
    scene = build_scene(venue, Grid(venue), {"bars": [], "fences": []})
    return scene, (-h + 0.3, -DIST - depth, h - 0.3, -DIST)


def sim_flow(args):
    b, n, tau, seed = args
    scene, box = bottleneck(b, n)
    agents = make_agents(scene, n, P.SERVICE_MEAN, seed, box=box, min_dist=0.55)
    res = simulate(scene, agents, tau, t_max=400.0)
    return steady_flow(res["t_exit"][np.isfinite(res["t_exit"])]) / b


def calibrate(taus=TAUS, seeds=SEEDS, workers=None):
    from ..visualization.tables import save
    real = real_flows()
    jobs = [(r[1], r[2], tau, s) for tau in taus for r in real for s in seeds]
    with ProcessPoolExecutor(workers or max(1, (os.cpu_count() or 2) - 2)) as ex:
        js = np.array(list(ex.map(sim_flow, jobs))).reshape(len(taus), len(real), len(seeds))
    real_js = np.array([r[4] for r in real])
    mae = np.abs(js.mean(2) - real_js).mean(1)
    best = int(mae.argmin())
    save("calibracion_tau", ["tau (s)", "MAE (1/(m s))"], [[float(t), round(float(m), 3)] for t, m in zip(taus, mae)])
    save("calibracion_anchos", ["Ancho (m)", "Real (1/(m s))", "Modelo (1/(m s))", "Desv. modelo", "Error abs."],
         [[r[1], r[4], round(float(js[best, i].mean()), 3), round(float(js[best, i].std(ddof=1)), 3),
           round(abs(float(js[best, i].mean()) - r[4]), 3)] for i, r in enumerate(real)])
    out = {"tau": float(taus[best]), "mae": round(float(mae[best]), 4),
           "mape": round(float(100 * np.mean(np.abs(js[best].mean(1) - real_js) / real_js)), 2), "taus": taus.tolist(),
           "mae_by_tau": np.round(mae, 4).tolist(), "widths": [r[1] for r in real], "real": real_js.tolist(),
           "model_mean": np.round(js[best].mean(1), 4).tolist(), "model_sd": np.round(js[best].std(1, ddof=1), 4).tolist()}
    P.CALIBRATION.parent.mkdir(parents=True, exist_ok=True)
    P.CALIBRATION.write_text(json.dumps(out, indent=1))
    P.TAU = out["tau"]
    return out


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=1))
