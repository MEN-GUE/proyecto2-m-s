import argparse

from src.model.data import fetch_osm
from src.model.geometry import Venue
from src.model.grid import Grid
from src.optimizer.objective import feasibility_study, optimize, save_bounds, verify_constraints
from src.optimizer.pso import benchmark
from src.simulation.calibration import calibrate
from src.simulation.checks import summary as verification
from src.visualization import export_web
from src.visualization.figures import (plot_calibration, plot_layouts, plot_pso_convergence, plot_snapshots,
                                      plot_venue)
from src.visualization.tables import model_parameters


def main():
    ap = argparse.ArgumentParser(description="Flujo completo del proyecto")
    ap.add_argument("--quick", action="store_true", help="corrida corta de prueba")
    args = ap.parse_args()
    fetch_osm()
    venue = Venue()
    grid = Grid(venue)
    plot_venue(venue)
    benchmark()
    save_bounds(venue)
    feasibility_study(venue, grid, n=200 if args.quick else 1000)
    calibrate(seeds=(1, 2) if args.quick else (1, 2, 3, 4, 5))
    plot_calibration()
    model_parameters()
    verification()
    plot_snapshots()
    optimize(iters=8 if args.quick else 25)
    verify_constraints()
    plot_pso_convergence()
    plot_layouts()
    for name in ("base", "pso"):
        export_web.save(export_web.export(name))


if __name__ == "__main__":
    main()
