# Salida de público al cierre de un concierto en la Explanada Cayalá

Proyecto 2 de CC3074 Modelización y Simulación (UVG, ciclo 2 de 2026).

Autor: Juan Fernando Menéndez Guerra, carné 17444. Trabajo individual aprobado por el docente.

Se simula la salida de público en la zona sur de la Explanada Cayalá (zona 16, Ciudad de Guatemala) al terminar un concierto nocturno. Parte del público pasa por barras cashless antes de salir. Se usa un modelo de fuerzas sociales para el movimiento de cada persona y un enjambre de partículas (PSO) para buscar dónde colocar cuatro barras y dos vallas de modo que baje la densidad máxima y el tiempo de salida.

## Pregunta

¿En qué porcentaje bajan la densidad pico (personas/m2) y el tiempo en que sale el 95 % del público (s) cuando la ubicación de barras y vallas se elige con PSO, frente al montaje tradicional con las barras pegadas al borde oeste?

## Resultados principales

30 réplicas por condición con las semillas 1001 a 1030. Todas las mejoras son simuladas.

| Escenario | Densidad pico, PSO frente a base | T95, PSO frente a base |
| --- | --- | --- |
| 500 personas, atención de 16.4 s | -7.1 % (IC 95 %: -8.2 % a -6.0 %) | -1.4 % (IC 95 %: -2.7 % a -0.2 %) |
| 600 personas | -4.8 % | -1.4 % (en el límite de ser significativo) |
| Atención de 24.6 s | -7.0 % | -1.2 % (no significativo) |

- El modelo se calibró con trayectorias reales de Jülich: tau = 0.5 s, error de flujo del 9 %.
- El modelo reproduce bien el flujo real, pero subestima la densidad real en 34 %.
- El tiempo de salida depende sobre todo de la velocidad de atención en las barras: con atención 50 % más lenta sube 40 %.

## Entregables

| Entregable | Dónde está |
| --- | --- |
| Informe técnico | `report/informe.pdf` (fuente en `report/informe.tex`) |
| Código | `src/`, `run_all.py`, `tests/` |
| Evidencia experimental | `results/tables/` (CSV y LaTeX), `results/figures/`, `results/layouts/pso.json`, `results/logs/`, `results/calibracion.json` |
| Demostración | visor web en `web/` con corridas guardadas en `web/static/data/` |

## Estructura

```
src/model/          geometría del recinto (OSM), parámetros, grilla, validador y descarga de datos
src/simulation/     motor de fuerzas sociales (Numba), corridas, calibración, experimentos y comparación real
src/optimizer/      PSO y función objetivo
src/visualization/  figuras, tablas y exportación para la web
tests/              pruebas de verificación, del PSO y del validador
data/               polígono de OSM y resumen de flujos de Jülich
results/            tablas, figuras, layout ganador y bitácoras del PSO
web/                visor en Deno Fresh
report/             informe en LaTeX
```

## Cómo reproducir

Requisitos: Python 3.14, Deno 2 para el visor y una distribución de LaTeX con `latexmk` y `biber` para el informe. En Windows, cambiar `.venv/bin/python` por `.venv\Scripts\python`.

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python run_all.py
```

El flujo completo tarda unos 5 minutos en una computadora de 20 núcleos. Hace lo siguiente:

1. Descarga los datos que falten.
2. Calibra el modelo con Jülich.
3. Corre el PSO con tres reinicios y verifica las restricciones.
4. Corre la matriz experimental y la comparación con la realidad.
5. Regenera todas las tablas y figuras en `results/` y las corridas del visor en `web/static/data/`.

Con la opción `--quick` corre una versión corta, solo para probar que todo funciona. Esa versión sobrescribe los resultados, así que para el informe se usa la corrida completa.

Pruebas automáticas (conservación de personas, cruce de muros, tiempo en flujo libre, PSO y validador):

```bash
.venv/bin/python -m pytest -q
```

Partes sueltas del flujo:

```bash
.venv/bin/python -m src.optimizer.objective
```

```bash
.venv/bin/python -m src.simulation.experiments
```

```bash
.venv/bin/python -m src.simulation.reference
```

Compilar el informe:

```bash
cd report
```

```bash
latexmk -pdf informe.tex
```

## Visor web

El visor está hecho con Deno Fresh. Reproduce las corridas guardadas en `web/static/data/`, con base y PSO lado a lado, y el botón "Simular" lanza una corrida nueva con el Python de `.venv` (se puede cambiar con la variable `PYTHON`).

```bash
cd web
```

```bash
deno install
```

```bash
deno task dev
```

Luego se abre http://localhost:5173.

Versión compilada, más rápida y sin recarga automática (también desde `web/`):

```bash
deno task build
```

```bash
deno task start
```

Luego se abre http://localhost:8000. La versión compilada copia los datos al compilar, así que después de volver a correr `run_all.py` hay que repetir `deno task build`.

Si el visor queda en blanco o no avanza después de regenerar los resultados, se detiene el servidor con Ctrl+C, se vuelve a iniciar y se recarga la página con Ctrl+Shift+R.

Una corrida suelta para el visor:

```bash
.venv/bin/python -m src.visualization.export_web --layout pso --n 600 --seed 1001
```

## Demostración en el video

Las corridas guardadas sirven de respaldo si falla el entorno. Están la base y el PSO con 500 personas, con 600 personas y con atención de 24.6 s, todas con la semilla 1001. Una forma de grabar el bloque de demostración del video con el visor:

1. Base frente a PSO con 500 personas: mostrar cómo en la base la corriente hacia el portón suroeste pasa pegada a las filas de las barras y cómo en el PSO las vallas separan las corrientes de cada portón.
2. Activar la capa de densidad en el momento de mayor salida (cerca de t = 25 s).
3. Lanzar una corrida nueva con otra semilla para mostrar que el programa corre en vivo.

## Datos

| Dato | Tipo | Fuente |
| --- | --- | --- |
| Polígono de la explanada, "Arena Gallo" (way 1569890595) | Real | OpenStreetMap, consulta a la API del 9 de noviembre de 2026, licencia ODbL |
| Ventana de 80 x 50 m, posición de portones | Estimación | Elegidas por el autor sobre el polígono real, del lado de la rotonda y del acceso de Futeca |
| Tamaño de barras y vallas | Estimación | Medidas típicas de mobiliario de eventos |
| Distribución inicial del público y compras | Sintético | Generado con semillas fijas |
| Trayectorias del experimento "Bottleneck, Caserne" (2006) | Real, público | Archivo de datos de Jülich, DOI 10.34735/ped.2006.2, licencia CC BY 4.0. Se descargan solas en `data/julich/raw/`; el resumen de flujos queda en `data/julich/julich_flows.csv` |

La Explanada Cayalá es el terreno abierto al norte de los campos de Futeca, junto al Bulevar Austriaco. En OSM aparece como "Arena Gallo", agregado al mapa el 20 de octubre de 2026 y etiquetado como zona en construcción. La identificación la hizo el autor, que conoce el lugar. Como es un descampado que se arma distinto en cada evento, la posición de portones, barras y vallas es una estimación.

Datos de mapa: colaboradores de OpenStreetMap. Datos de Jülich: Forschungszentrum Jülich, CC BY 4.0.

## Contribuciones y uso de inteligencia artificial

**Autor.** Juan Fernando Menéndez Guerra definió el problema y el escenario, eligió la técnica, fijó los parámetros del enunciado, revisó cada parte del trabajo antes de aceptarla y decidió qué cambios se integraban.

**Uso de inteligencia artificial.** Parte del código, pruebas, correcciones y aclaraciones.
