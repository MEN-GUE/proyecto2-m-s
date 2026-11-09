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


if __name__ == "__main__":
    print(plot_venue(), plot_snapshots())
