import argparse
import json
import sys
from pathlib import Path

import numpy as np

from ..model import params as P
from ..model.geometry import fence_line
from ..optimizer.objective import load_layout
from ..simulation.runner import build_scene, context, make_agents, metrics, simulate

ROOT = Path(__file__).resolve().parents[2]
WEB_DATA = ROOT / "web/static/data"


def export(name="base", n=P.N_AGENTS, seed=1001, service_mean=P.SERVICE_MEAN, tau=None):
    venue, grid = context()
    layout = load_layout(name)
    scene = build_scene(venue, grid, layout)
    agents = make_agents(scene, n, service_mean, seed)
    res = simulate(scene, agents, tau, record=True)
    m = metrics(res, n)
    frames = np.where(res["frames"] > -100, np.round(res["frames"] * 10), -1).astype(int)
    r2 = lambda a: np.round(np.asarray(a, float), 2).tolist()
    return {
        "meta": {"layout": name, "n": n, "seed": seed, "service_mean": service_mean, "dt": P.SAMPLE_DT},
        "geometry": {"domain": r2(venue.domain.exterior.coords), "walls": r2(venue.walls),
                     "gates": r2(venue.gates[:, :4]), "bars": r2(layout["bars"]),
                     "fences": [r2(fence_line(*f).coords) for f in layout["fences"]],
                     "service": r2(scene["sp"]), "bar_size": [P.BAR_W, P.BAR_H]},
        "buyer": (agents["line"] >= 0).astype(int).tolist(),
        "frames": frames.reshape(len(frames), -1).tolist(),
        "density": r2(res["dens"]), "evacuated": res["n_out"].tolist(),
        "metrics": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()},
    }


def save(data, path=None):
    m = data["meta"]
    path = Path(path) if path else WEB_DATA / f"{m['layout']}_n{m['n']}_s{m['seed']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")))
    index = sorted(p.stem for p in WEB_DATA.glob("*.json") if p.stem != "index")
    (WEB_DATA / "index.json").write_text(json.dumps(index))
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default="base")
    ap.add_argument("--n", type=int, default=P.N_AGENTS)
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--service", type=float, default=P.SERVICE_MEAN)
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()
    data = export(a.layout, a.n, a.seed, a.service)
    if a.stdout:
        sys.stdout.write(json.dumps(data, separators=(",", ":")))
    else:
        print(save(data))
