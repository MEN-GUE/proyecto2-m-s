import argparse

from src.model.data import fetch_osm
from src.model.geometry import Venue
from src.model.grid import Grid
from src.optimizer.objective import feasibility_study, save_bounds
from src.optimizer.pso import benchmark
from src.visualization.figures import plot_venue


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


if __name__ == "__main__":
    main()
