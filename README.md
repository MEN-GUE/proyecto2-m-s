# Salida de público al cierre de un concierto en la Explanada Cayalá

Proyecto 2 de CC3074 Modelización y Simulación (UVG, ciclo 2 de 2026).

Se simula la salida de público en la zona sur de la Explanada Cardales de Cayalá (zona 16, Ciudad de Guatemala) al terminar un concierto nocturno. Parte del público pasa por barras cashless antes de salir. Se usa un modelo de fuerzas sociales para el movimiento de cada persona y un enjambre de partículas (PSO) para buscar dónde colocar cuatro barras y dos vallas de modo que baje la densidad máxima y el tiempo de salida.

## Pregunta

¿En qué porcentaje bajan la densidad pico (personas/m2) y el tiempo en que sale el 95 % del público (s) cuando la ubicación de barras y vallas se elige con PSO, frente al montaje tradicional con las barras pegadas al borde oeste?

## Estructura

```
src/model/          geometría del recinto, parámetros y descarga de datos
src/simulation/     motor de fuerzas sociales y corridas
src/optimizer/      PSO y función objetivo
src/visualization/  figuras, tablas y exportación para la web
tests/              pruebas de verificación
data/               datos de entrada (OSM y Jülich)
results/            figuras, tablas y layouts generados
web/                visor en Deno Fresh
report/             informe en LaTeX
```

## Cómo reproducir

Requisitos: Python 3.14 y, para el visor, Deno 2.

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python run_all.py
```

El flujo completo descarga los datos que falten, calibra el modelo con Jülich, corre el PSO con tres reinicios, verifica las restricciones y deja tablas, figuras y corridas para la web en `results/` y `web/static/data/`. Con la opción `--quick` corre una versión corta solo para probar que todo funciona; esa versión sobrescribe los resultados, así que para el informe se usa la corrida completa.

Solo la búsqueda con PSO:

```bash
.venv/bin/python -m src.optimizer.objective
```

Solo la matriz experimental (4 condiciones pedidas y 2 adicionales, 30 réplicas cada una, semillas 1001 a 1030):

```bash
.venv/bin/python -m src.simulation.experiments
```

Pruebas automáticas (conservación de personas, cruce de muros, tiempo en flujo libre, PSO y validador):

```bash
.venv/bin/python -m pytest -q
```

Una corrida suelta exportada para la web:

```bash
.venv/bin/python -m src.visualization.export_web --layout base --n 500 --seed 1001
```

## Visor web

El visor está hecho con Deno Fresh. Reproduce las corridas guardadas en `web/static/data/` y el botón "Simular" lanza una corrida nueva con el Python de `.venv` (se puede cambiar con la variable `PYTHON`).

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

## Datos

| Dato | Tipo | Fuente |
| --- | --- | --- |
| Polígono del lote (way 688526225) | Real | OpenStreetMap, consulta Overpass del 8 de noviembre de 2026, licencia ODbL |
| Ventana de 80 x 50 m, posición de portones | Estimación | Elegidas por el autor sobre el polígono real |
| Tamaño de barras y vallas | Estimación | Medidas típicas de mobiliario de eventos |
| Distribución inicial del público y compras | Sintético | Generado con semillas fijas |
| Trayectorias del experimento "Bottleneck, Caserne" (2006) | Real, público | Archivo de datos de Jülich, DOI 10.34735/ped.2006.2, licencia CC BY 4.0. Se descargan solas en `data/julich/raw/`; el resumen de flujos queda en `data/julich/julich_flows.csv` |

En OSM no existe un elemento llamado "Explanada Cayalá". Se usa el lote abierto más grande junto a Cardales de Cayalá, que coincide con la "Explanada Cardales" mencionada por Prensa Libre para los conciertos de noviembre de 2022. Esta identificación es una suposición del autor.

Datos de mapa: colaboradores de OpenStreetMap.

## Uso de inteligencia artificial

El código y los textos de este repositorio se escribieron con ayuda de Claude Code (Anthropic), bajo la dirección y revisión del autor. El autor definió el problema, revisó cada parte antes de integrarla y es responsable de las decisiones finales.
