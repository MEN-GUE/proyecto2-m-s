import argparse

from src.model.data import fetch_osm
from src.visualization.figures import plot_venue


def main():
    ap = argparse.ArgumentParser(description="Flujo completo del proyecto")
    ap.add_argument("--quick", action="store_true", help="corrida corta de prueba")
    args = ap.parse_args()
    fetch_osm()
    plot_venue()


if __name__ == "__main__":
    main()
