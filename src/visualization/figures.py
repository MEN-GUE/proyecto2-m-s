from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from ..model import params as P
from ..model.geometry import Venue, baseline_layout, bar_box, fence_line, service_points

FIG_DIR = Path(__file__).resolve().parents[2] / "results/figures"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "figure.dpi": 150})


def draw_layout(ax, venue, layout, label=True):
    ax.fill(*venue.domain.exterior.xy, color="#f2f2f2", zorder=0)
    for s in venue.walls:
        ax.plot(s[[0, 2]], s[[1, 3]], color="k", lw=1.5)
    for i, g in enumerate(venue.gates):
        ax.plot(g[[0, 2]], g[[1, 3]], color="#1a9850", lw=4, label="Portón (4 m)" if i == 0 and label else None)
    for i, (cx, cy) in enumerate(layout["bars"]):
        ax.fill(*bar_box(cx, cy).exterior.xy, color="#d95f02", label="Barra cashless" if i == 0 and label else None)
    for i, f in enumerate(layout["fences"]):
        ax.plot(*fence_line(*f).xy, color="#7570b3", lw=3, label="Valla encauzadora" if i == 0 and label else None)
    sp = service_points(layout)
    ax.plot(sp[:, 0], sp[:, 1], "v", ms=3, color="#d95f02")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")


def plot_venue(venue=None, name="fig_recinto.png"):
    venue = venue or Venue()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1, 1.6]})
    a1.fill(*venue.lot.exterior.xy, color="#cfe3f3", label="Lote OSM (way 688526225)")
    a1.add_patch(Rectangle((0, 0), P.WIDTH, P.HEIGHT, fill=False, ls="--", color="r", label="Ventana 80 x 50 m"))
    a1.set_aspect("equal")
    a1.set_title("Polígono real y zona modelada")
    a1.set_xlabel("x (m)")
    a1.set_ylabel("y (m)")
    a1.legend(loc="upper left", fontsize=8)
    draw_layout(a2, venue, baseline_layout(venue))
    x0, y0, x1, y1 = P.SPAWN_BOX
    a2.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, alpha=0.15, color="#2c7bb6", label="Zona inicial del público"))
    a2.set_title("Dominio y montaje base (barras en el borde oeste)")
    a2.legend(loc="lower right", fontsize=8)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def plot_snapshots(layout=None, n=500, seed=1001, times=(0, 20, 45, 150), name="fig_instantaneas.png"):
    from ..simulation.runner import build_scene, context, make_agents, simulate
    venue, grid = context()
    layout = layout or baseline_layout(venue)
    scene = build_scene(venue, grid, layout)
    agents = make_agents(scene, n, P.SERVICE_MEAN, seed)
    frames = simulate(scene, agents, record=True)["frames"]
    buy = agents["line"] >= 0
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
    for ax, t in zip(axs.flat, times):
        draw_layout(ax, venue, layout, label=False)
        p = frames[min(int(t / P.SAMPLE_DT), len(frames) - 1)]
        inside = p[:, 0] > -100
        ax.scatter(*p[inside & ~buy].T, s=4, c="#2c7bb6", label="Va directo a un portón")
        ax.scatter(*p[inside & buy].T, s=4, c="#d7191c", label="Pasa por una barra")
        ax.set_title(f"t = {t} s, personas adentro: {inside.sum()}")
        ax.set_xlim(-2, P.WIDTH + 2)
        ax.set_ylim(-2, P.HEIGHT + 2)
    axs[0, 0].legend(loc="lower right", fontsize=8, markerscale=3)
    fig.suptitle(f"Montaje base, {n} personas, semilla {seed}")
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def plot_calibration(name="fig_calibracion.png"):
    import json
    c = json.loads(P.CALIBRATION.read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.plot(c["widths"], c["real"], "o", color="k", label="Jülich 2006 (medido)")
    a1.errorbar(c["widths"], c["model_mean"], yerr=c["model_sd"], fmt="s--", color="#d95f02", capsize=3,
                label=f"Modelo, $\\tau$ = {c['tau']} s (media y 1 desv.)")
    a1.set_xlabel("Ancho del cuello de botella b (m)")
    a1.set_ylabel("Flujo específico Js (personas/(m s))")
    a1.set_title("Flujo específico real y simulado")
    a1.set_ylim(1.0, 2.8)
    a1.legend(fontsize=8)
    a2.plot(c["taus"], c["mae_by_tau"], "o-", color="#2c7bb6")
    a2.axvline(c["tau"], ls=":", color="k")
    a2.set_xlabel("Tiempo de relajación $\\tau$ (s)")
    a2.set_ylabel("MAE (personas/(m s))")
    a2.set_title(f"Error absoluto medio, mínimo {c['mae']:.3f} en $\\tau$ = {c['tau']} s")
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def _pso_logs():
    import json
    logs = sorted((FIG_DIR.parent / "logs").glob("pso_reinicio_*.json"))
    return [json.loads(f.read_text()) for f in logs]


def plot_pso_convergence(name="fig_pso_convergencia.png"):
    import numpy as np
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    for d in _pso_logs():
        it = [h["iter"] for h in d["history"]]
        ls = "--" if "sin paro" in d["name"] else "-"
        axs[0].plot(it, [h["best"] for h in d["history"]], ls, marker="o", ms=3, label=f"Reinicio {d['name']}")
        axs[1].plot(it, [100 * np.mean(np.array(h["values"]) >= 10) for h in d["history"]], ls, marker="o", ms=3)
        axs[2].plot(it, [h["diversity"] for h in d["history"]], ls, marker="o", ms=3)
    axs[0].axhline(1, color="k", ls=":", label="Base (J = 1)")
    for ax, t, y in zip(axs, ("Mejor J del enjambre", "Partículas inválidas", "Diversidad del enjambre"),
                        ("J (3 semillas)", "Inválidas (%)", "Distancia media al centro (rango = 1)")):
        ax.set_title(t)
        ax.set_xlabel("Iteración")
        ax.set_ylabel(y)
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def plot_layouts(name="fig_layouts.png"):
    import json
    from ..optimizer.objective import decode
    venue = Venue()
    rows = {r[0]: r for r in csv_rows("pso_reinicios")}
    items = [("Base", baseline_layout(venue))]
    items += [(d["name"], decode(d["best"])) for d in _pso_logs() if "sin paro" not in d["name"]]
    win = json.loads((FIG_DIR.parent / "layouts/pso.json").read_text())["restart"]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
    for ax, (nm, lay) in zip(axs.flat, items):
        draw_layout(ax, venue, lay, label=nm == "Base")
        title = "Montaje base" if nm == "Base" else f"Reinicio {nm}" + (" (ganador)" if nm == win else "")
        ax.set_title(f"{title}, J con 10 semillas = {float(rows[nm][5]):.3f}")
        ax.set_xlim(-2, P.WIDTH + 2)
        ax.set_ylim(-2, P.HEIGHT + 2)
    axs[0, 0].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def csv_rows(table):
    import csv
    with open(FIG_DIR.parent / "tables" / f"{table}.csv") as fh:
        return list(csv.reader(fh))[1:]


if __name__ == "__main__":
    print(plot_venue(), plot_snapshots())
