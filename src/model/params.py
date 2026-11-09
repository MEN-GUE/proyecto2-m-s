import json
from pathlib import Path

import numpy as np

# Recinto (ventana de 80 x 50 m sobre el poligono real de OSM)
WIDTH, HEIGHT = 80.0, 50.0
GATE_WIDTH = 4.0
GATE_X = (24.0, 50.0)            # portones estimados en el borde sur, hacia la rotonda y el acceso de Futeca
EXIT_CLEAR_RADIUS = 5.0
SPAWN_BOX = (2.0, 40.5, 78.0, 49.0)

# Mobiliario (tamanos estimados)
BAR_W, BAR_H = 2.0, 6.0          # barra orientada norte-sur, atiende por su cara este
BASE_BAR_Y = (13.0, 21.5, 30.0, 38.5)   # montaje base: barras pegadas al borde oeste
SERVERS_PER_BAR = 3
SERVER_OFFSETS = (-2.0, 0.0, 2.0)
QUEUE_SPACING = 0.8              # distancia de reposo con A y B de Helbing (2000)
QUEUE_ZONE = 8.0                 # largo libre frente a la cara de servicio
FENCE_LEN = 6.0
MIN_GAP = 1.12                   # ancho libre minimo de paso

# Demanda
N_AGENTS = 500
P_BUY = 0.35
SERVICE_MEAN = 16.4
SERVICE_CV = 0.5
V0_MEAN, V0_SD = 1.34, 0.26
V0_MIN, V0_MAX = V0_MEAN - 2 * V0_SD, V0_MEAN + 2 * V0_SD
RADIUS_MIN, RADIUS_MAX = 0.25, 0.30

# Fuerzas sociales (Helbing, Farkas y Vicsek 2000; Helbing y Molnar 1995)
MASS = 80.0
CALIBRATION = Path(__file__).resolve().parents[2] / "results/calibracion.json"
TAU = json.loads(CALIBRATION.read_text())["tau"] if CALIBRATION.exists() else 0.5   # calibrado con Julich
A_P, B_P = 2000.0, 0.08
A_W, B_W = 2000.0, 0.08
V_CAP = 1.3                      # rapidez maxima = 1.3 v0
DT = 0.05
T_MAX = 900.0
EXIT_MARGIN = 0.3                # se cuenta como evacuado 0.3 m despues del porton
NAV_CLEAR = 0.6                  # holgura preferida al planear rutas
SERVICE_RADIUS = 1.0             # distancia al punto de atencion para empezar a atender
GIVE_UP = 120.0                  # quien no entra a una fila en este tiempo desiste
QUEUE_AVOID = 4.0                # quien va a la salida evita cruzar zonas de fila (costo relativo)
HEAD_WAIT = 20.0                 # si el primero no llega al punto de atencion en este tiempo, se le atiende igual

# Densidad
DENS_H = 0.5
DENS_SIGMA = 0.7                 # Helbing, Johansson y Al-Abideen (2007)
SAMPLE_DT = 0.5
DENS_LIMIT = 4.0


def lognormal_params(mean, cv=SERVICE_CV):
    s2 = np.log(1 + cv**2)
    return np.log(mean) - s2 / 2, np.sqrt(s2)
