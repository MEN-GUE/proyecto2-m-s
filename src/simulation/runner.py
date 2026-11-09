import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..model import params as P
from ..model.geometry import Venue, layout_segments, service_points
from ..model.grid import H, Grid, dijkstra, inside_polygon
from . import engine

_CTX = {}


def context():
    if not _CTX:
        _CTX["venue"] = Venue()
        _CTX["grid"] = Grid(_CTX["venue"])
    return _CTX["venue"], _CTX["grid"]


def directions(dist):
    nx, ny = dist.shape
    big = np.pad(dist, 1, constant_values=np.inf)
    gx, gy = np.zeros_like(dist), np.zeros_like(dist)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == dj == 0:
                continue
            nb = big[1 + di:1 + di + nx, 1 + dj:1 + dj + ny]
            ln = math.hypot(di, dj)
            with np.errstate(invalid="ignore"):
                w = np.where(np.isfinite(dist) & np.isfinite(nb) & (nb < dist), (dist - nb) / ln, 0.0)
            gx += w * di / ln
            gy += w * dj / ln
    nrm = np.hypot(gx, gy)
    nrm[nrm == 0] = 1.0
    return np.stack([gx / nrm, gy / nrm], -1)


def build_scene(venue, grid, layout):
    od = grid.obstacle_distances(layout)
    clear = grid.wall_d.copy()
    blocked = ~(grid.domain | grid.pocket)
    for i, d in enumerate(od):
        clear = np.minimum(clear, d)
        blocked |= d <= (0 if i < len(layout["bars"]) else 0.15)
    cost = np.where(blocked, np.inf, 1 + 3 * np.clip((P.NAV_CLEAR - clear) / P.NAV_CLEAR, 0, 1))
    fields = [dijkstra(cost, grid.source, H)]
    for cx, cy in layout["bars"]:
        zone = ((grid.x >= cx + P.BAR_W / 2) & (grid.x <= cx + P.BAR_W / 2 + P.QUEUE_ZONE)
                & (np.abs(grid.y - cy) <= P.BAR_H / 2))
        fields.append(dijkstra(cost, zone, H))
    fdist = np.array(fields)
    x0, y0, x1, y1 = venue.domain.bounds
    dx = np.arange(x0, x1, P.DENS_H) + P.DENS_H / 2
    dy = np.arange(y0, y1, P.DENS_H) + P.DENS_H / 2
    DX, DY = np.meshgrid(dx, dy, indexing="ij")
    walk = inside_polygon(DX, DY, np.array(venue.domain.exterior.coords))
    for cx, cy in layout["bars"]:
        walk &= ~((np.abs(DX - cx) <= P.BAR_W / 2) & (np.abs(DY - cy) <= P.BAR_H / 2))
    sp = service_points(layout) if layout["bars"] else np.zeros((0, 2))
    return {"walls": layout_segments(venue, layout), "gates": venue.gates.copy(), "fdist": fdist,
            "fdir": np.array([directions(f) for f in fields]), "sp": sp,
            "qdir": np.tile([1.0, 0.0], (len(sp), 1)),
            "line_field": 1 + np.arange(len(sp)) // P.SERVERS_PER_BAR,
            "nav0": np.array([grid.x0, grid.y0, H]), "dens0": np.array([x0, y0, P.DENS_H]),
            "walk": walk, "domain": np.array(venue.domain.exterior.coords), "layout": layout}


def spawn(scene, n, rng, box=P.SPAWN_BOX, min_dist=0.6):
    x0, y0, x1, y1 = box
    pts = []
    while len(pts) < n:
        c = np.column_stack([rng.uniform(x0, x1, 4 * n), rng.uniform(y0, y1, 4 * n)])
        c = c[inside_polygon(c[:, 0], c[:, 1], scene["domain"])]
        for cx, cy in scene["layout"]["bars"]:
            c = c[(np.abs(c[:, 0] - cx) > P.BAR_W / 2 + 0.3) | (np.abs(c[:, 1] - cy) > P.BAR_H / 2 + 0.3)]
        wd = np.min([np.hypot(*(c - _nearest_pts(c, w)).T) for w in scene["walls"]], axis=0)
        for p in c[wd > 0.5]:
            if len(pts) == n:
                break
            if not pts or np.min(np.hypot(*(np.array(pts) - p).T)) >= min_dist:
                pts.append(p)
    return np.array(pts)


def _nearest_pts(c, w):
    a, b = w[:2], w[2:]
    t = np.clip(((c - a) @ (b - a)) / ((b - a) @ (b - a)), 0, 1)
    return a + t[:, None] * (b - a)


def make_agents(scene, n, service_mean, seed, box=P.SPAWN_BOX, min_dist=0.6):
    rng = [np.random.default_rng([seed, k]) for k in range(4)]
    v0 = rng[0].normal(P.V0_MEAN, P.V0_SD, 4 * n)
    v0 = v0[(v0 >= P.V0_MIN) & (v0 <= P.V0_MAX)][:n]
    rad = rng[0].uniform(P.RADIUS_MIN, P.RADIUS_MAX, n)
    buy = rng[1].random(n) < P.P_BUY
    mu, s = P.lognormal_params(service_mean)
    dur = rng[1].lognormal(mu, s, n)
    pos = spawn(scene, n, rng[2], box, min_dist)
    line = np.full(n, -1)
    sp = scene["sp"]
    if len(sp):
        k = P.SERVERS_PER_BAR
        load = np.zeros(len(sp), int)
        for i in rng[3].permutation(np.flatnonzero(buy)):
            bar_load = load.reshape(-1, k).sum(1)
            bar_d = np.hypot(*(sp.reshape(-1, k, 2).mean(1) - pos[i]).T)
            b = min(np.flatnonzero(bar_load == bar_load.min()), key=lambda j: bar_d[j])
            lines = range(b * k, b * k + k)
            l = min(lines, key=lambda j: (load[j], np.hypot(*(sp[j] - pos[i]))))
            line[i] = l
            load[l] += 1
    return {"pos": pos, "v0": v0, "rad": rad, "line": line, "dur": dur}


def simulate(scene, agents, tau=None, record=False, t_max=P.T_MAX):
    tau = P.TAU if tau is None else tau
    prm = np.array([tau, P.A_P, P.B_P, P.A_W, P.B_W, P.MASS, P.DT, t_max, P.V_CAP, P.DENS_SIGMA, P.SAMPLE_DT,
                    P.QUEUE_SPACING, P.EXIT_MARGIN, P.SERVICE_RADIUS, P.GIVE_UP])
    n = len(agents["pos"])
    frames = np.zeros((int(t_max / P.SAMPLE_DT) + 3 if record else 0, n, 2))
    out = engine.simulate(agents["pos"], agents["v0"], agents["rad"], agents["line"], agents["dur"],
                          scene["walls"], scene["gates"], scene["fdist"], scene["fdir"],
                          scene["line_field"], scene["sp"], scene["qdir"], scene["nav0"], scene["dens0"],
                          scene["walk"], prm, frames)
    keys = ["t_exit", "gate", "unserved", "dens", "n_in", "n_out", "dens_map", "crossings", "t_end"]
    res = dict(zip(keys, out))
    if record:
        res["frames"] = frames[:len(res["dens"])]
    return res


def metrics(res, n, gate_width=P.GATE_WIDTH, window=10.0):
    t = np.sort(np.where(np.isnan(res["t_exit"]), np.inf, res["t_exit"]))
    flows = []
    for g in np.unique(res["gate"][res["gate"] >= 0]):
        te = np.sort(res["t_exit"][res["gate"] == g])
        cnt = np.searchsorted(te, te + window) - np.arange(len(te))
        flows.append(cnt.max() / window / gate_width)
    return {"d_max": float(res["dens"].max()), "t95": float(t[math.ceil(0.95 * n) - 1]),
            "t_all": float(t[-1]), "evacuated": int(np.isfinite(t).sum()),
            "conservation": bool(np.all(res["n_in"] + res["n_out"] == n)),
            "crossings": int(res["crossings"]), "peak_flow": float(max(flows, default=0.0)),
            "left_unserved": int(res["unserved"])}


def run(layout, n=P.N_AGENTS, service_mean=P.SERVICE_MEAN, seed=1001, tau=None, record=False, scene=None):
    if scene is None:
        venue, grid = context()
        scene = build_scene(venue, grid, layout)
    agents = make_agents(scene, n, service_mean, seed)
    res = simulate(scene, agents, tau, record)
    res.update(metrics(res, n))
    return res


def _job(args):
    layout, n, service_mean, seed, tau = args
    r = run(layout, n, service_mean, seed, tau)
    return {k: r[k] for k in ("d_max", "t95", "t_all", "evacuated", "conservation", "crossings",
                              "peak_flow", "left_unserved", "dens", "n_out", "dens_map")} | {"seed": seed}


def run_many(jobs, workers=None):
    workers = workers or max(1, (os.cpu_count() or 2) - 2)
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_job, jobs))
