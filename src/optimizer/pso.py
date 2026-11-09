import numpy as np


def pso(f, lo, hi, n_particles=12, iters=25, w=(0.9, 0.4), c1=1.49, c2=1.49, vmax_frac=0.2,
        tol=1e-3, patience=5, seed=0, periodic=None, x0=None):
    """Minimiza f, que recibe una matriz (n, d) y devuelve n valores."""
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    span = hi - lo
    periodic = np.zeros(len(lo), bool) if periodic is None else np.asarray(periodic)
    vmax = vmax_frac * span
    x = lo + rng.random((n_particles, len(lo))) * span
    if x0 is not None:
        x[:len(x0)] = x0
    v = np.zeros_like(x)
    fx = np.asarray(f(x), float)
    p, fp = x.copy(), fx.copy()
    g, fg = p[fp.argmin()].copy(), fp.min()
    history = [_log(0, x, fx, fg, span)]
    stall = 0
    for k in range(iters):
        wk = w[0] - (w[0] - w[1]) * k / max(iters - 1, 1)
        r1, r2 = rng.random((2, *x.shape))
        v = np.clip(wk * v + c1 * r1 * (p - x) + c2 * r2 * (g - x), -vmax, vmax)
        x = x + v
        x[:, periodic] = lo[periodic] + (x[:, periodic] - lo[periodic]) % span[periodic]
        out = (x < lo) | (x > hi)
        x, v[out] = np.clip(x, lo, hi), 0
        fx = np.asarray(f(x), float)
        better = fx < fp
        p[better], fp[better] = x[better], fx[better]
        gain = fg - fp.min()
        if gain > 0:
            g, fg = p[fp.argmin()].copy(), fp.min()
        stall = stall + 1 if gain < tol else 0
        history.append(_log(k + 1, x, fx, fg, span))
        if stall >= patience:
            break
    return g, fg, history


def _log(k, x, fx, fg, span):
    z = x / span
    return {"iter": k, "best": float(fg), "mean": float(np.mean(fx)),
            "diversity": float(np.linalg.norm(z - z.mean(0), axis=1).mean()),
            "values": fx.tolist(), "positions": x.tolist()}


def rastrigin(x):
    return 10 * x.shape[1] + (x**2 - 10 * np.cos(2 * np.pi * x)).sum(1)


def benchmark(seeds=range(1, 21)):
    from ..visualization.tables import save
    rows = []
    for s in seeds:
        _, best, hist = pso(rastrigin, -5.12 * np.ones(2), 5.12 * np.ones(2), seed=s)
        rows.append([s, round(best, 4), hist[-1]["iter"], round(hist[-1]["diversity"], 4), int(best < 0.01)])
    save("pso_rastrigin", ["Semilla", "Mejor f", "Iteraciones", "Diversidad final", "Óptimo global"], rows)
    b = np.array([r[1] for r in rows])
    summary = [["Corridas", len(rows)], ["Llegan al óptimo global (f menor a 0.01)", int((b < 0.01).sum())],
               ["Mediana del mejor f", round(float(np.median(b)), 3)],
               ["Mediana de iteraciones", int(np.median([r[2] for r in rows]))],
               ["Diversidad final media", round(float(np.mean([r[3] for r in rows])), 3)]]
    return save("pso_rastrigin_resumen", ["Indicador", "Valor"], summary)


if __name__ == "__main__":
    print(benchmark().read_text())
