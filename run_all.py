import argparse

from src.model.data import fetch_osm
from src.model.geometry import Venue
from src.model.grid import Grid
from src.optimizer.objective import feasibility_study, optimize, save_bounds, verify_constraints
from src.optimizer.pso import benchmark
from src.simulation.calibration import calibrate
from src.simulation.checks import summary as verification
from src.simulation.experiments import run_matrix, summarize
from src.simulation.reference import correspondence
from src.visualization import export_web
from src.visualization.figures import (plot_calibration, plot_curves, plot_density_check, plot_heatmap,
                                      plot_layouts, plot_pso_convergence, plot_snapshots, plot_venue, plot_violins)
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
    run_matrix()
    summarize()
    plot_heatmap()
    plot_curves()
    plot_violins()
    correspondence()
    plot_density_check()
    for name, n, service in (("base", 500, 16.4), ("pso", 500, 16.4), ("base", 600, 16.4), ("pso", 600, 16.4),
                             ("base", 500, 24.6), ("pso", 500, 24.6)):
        export_web.save(export_web.export(name, n, 1001, service))


if __name__ == "__main__":
    main()
