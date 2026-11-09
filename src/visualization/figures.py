import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from ..model import params as P
from ..model.data import OSM_WAY
from ..model.geometry import Venue, baseline_layout, bar_box, fence_line, service_points

FIG_DIR = Path(__file__).resolve().parents[2] / "results/figures"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "figure.dpi": 150})


def draw_layout(ax, venue, layout, label=True, floor=True):
    if floor:
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
    a1.fill(*venue.lot.exterior.xy, color="#cfe3f3", label=f"Arena Gallo, OSM (way {OSM_WAY})")
    a1.add_patch(Rectangle((0, 0), P.WIDTH, P.HEIGHT, fill=False, ls="--", color="r", label="Ventana 80 x 50 m"))
    a1.set_aspect("equal")
    a1.set_title("Polígono real y zona modelada")
    a1.set_xlabel("x (m)")
    a1.set_ylabel("y (m)")
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8)
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


def plot_density_check(name="fig_densidad_julich.png"):
    rows = csv_rows("densidad_julich")
    b = [float(r[0]) for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(b, [float(r[1]) for r in rows], "o", color="k", label="Jülich 2006 (medido)")
    ax.errorbar(b, [float(r[2]) for r in rows], yerr=[float(r[3]) for r in rows], fmt="s--", color="#d95f02",
                capsize=3, label="Modelo calibrado (media y 1 desv.)")
    ax.axhline(P.DENS_LIMIT, color="#7570b3", ls=":", label="Límite seguro (4 p/m2)")
    ax.set_xlabel("Ancho del cuello de botella b (m)")
    ax.set_ylabel("Densidad pico frente a la puerta (personas/m2)")
    ax.set_title("Densidad pico real y simulada con el mismo método de medición")
    ax.set_ylim(0, 6)
    ax.legend(fontsize=8, loc="lower left")
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


def _experiment():
    import numpy as np
    d = np.load(FIG_DIR.parent / "runs/experimento.npz")
    return list(d["names"]), d


def plot_heatmap(name="fig_mapa_densidad.png"):
    import numpy as np
    from ..optimizer.objective import load_layout
    venue = Venue()
    names, d = _experiment()
    x0, y0, x1, y1 = venue.domain.bounds
    pair = [("Base perimetral", "base"), ("Propuesta PSO", "pso")]
    maps = [np.where(d["maps"][names.index(k)] > 0, d["maps"][names.index(k)], np.nan) for k, _ in pair]
    vmax = max(np.nanmax(m) for m in maps)
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, (k, lay), m in zip(axs, pair, maps):
        im = ax.imshow(m.T, origin="lower", extent=(x0, x0 + m.shape[0] * P.DENS_H, y0, y0 + m.shape[1] * P.DENS_H),
                       cmap="YlOrRd", vmin=0, vmax=vmax)
        draw_layout(ax, venue, load_layout(lay), label=False, floor=False)
        ax.set_title(f"{k}: pico medio {np.nanmax(m):.2f} p/m2")
        ax.set_xlim(-2, P.WIDTH + 2)
        ax.set_ylim(-2, P.HEIGHT + 2)
    fig.colorbar(im, ax=axs, label="Densidad máxima por celda (personas/m2)", shrink=0.9)
    fig.suptitle("Densidad máxima en cada punto del recinto, promedio de 30 réplicas (el límite seguro es 4 p/m2)")
    fig.savefig(FIG_DIR / name, bbox_inches="tight")
    plt.close(fig)
    return FIG_DIR / name


def plot_curves(name="fig_curvas_desalojo.png"):
    import numpy as np
    from ..simulation.experiments import CONDITIONS
    names, d = _experiment()
    t = np.arange(d["curves"].shape[2]) * P.SAMPLE_DT
    fig, ax = plt.subplots(figsize=(9, 5))
    for (k, *_rest, main), color in zip(CONDITIONS, ["#555555", "#d95f02", "#7570b3", "#1b9e77", "#999999", "#bbbbbb"]):
        if not main:
            continue
        c = 100 * d["curves"][names.index(k)]
        m, sd = c.mean(0), c.std(0, ddof=1)
        ax.plot(t, m, color=color, label=k)
        ax.fill_between(t, np.clip(m - sd, 0, 100), np.clip(m + sd, 0, 100), color=color, alpha=0.2)
    ax.axhline(95, color="k", ls=":", lw=1)
    ax.text(5, 96.5, "95 % evacuado", fontsize=8)
    ax.set_xlabel("Tiempo desde el cierre (s)")
    ax.set_ylabel("Personas evacuadas (% del aforo)")
    ax.set_title("Curvas de desalojo: media y banda de una desviación estándar (30 réplicas)")
    ax.set_xlim(0, t[-1])
    ax.set_ylim(0, 101)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / name)
    plt.close(fig)
    return FIG_DIR / name


def plot_violins(name="fig_violines.png"):
    from ..simulation.experiments import CONDITIONS, load_runs
    data = load_runs()
    labels = [c[0] for c in CONDITIONS]
    colors = ["#999999" if c[1] == "base" else "#d95f02" for c in CONDITIONS]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, (k, title) in zip(axs, (("d_max", "Densidad pico (personas/m2)"), ("t95", "T95 (s)"))):
        parts = ax.violinplot([data[c][k] for c in labels], showmeans=True)
        for body, col in zip(parts["bodies"], colors):
            body.set_facecolor(col)
            body.set_alpha(0.6)
        for key in ("cmeans", "cmins", "cmaxes", "cbars"):
            parts[key].set_color("k")
            parts[key].set_linewidth(0.8)
        ax.set_xticks(range(1, len(labels) + 1), [textwrap.fill(lab, 12, break_long_words=False) for lab in labels], fontsize=8)
        ax.set_ylabel(title)
        ax.set_title(f"{title} por condición (30 réplicas)")
    axs[0].plot([], [], "s", color="#999999", label="Montaje base")
    axs[0].plot([], [], "s", color="#d95f02", label="Montaje PSO")
    axs[0].legend(fontsize=8)
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
