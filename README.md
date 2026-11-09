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

## Datos

| Dato | Tipo | Fuente |
| --- | --- | --- |
| Polígono del lote (way 688526225) | Real | OpenStreetMap, consulta Overpass del 8 de noviembre de 2026, licencia ODbL |
| Ventana de 80 x 50 m, posición de portones | Estimación | Elegidas por el autor sobre el polígono real |
| Tamaño de barras y vallas | Estimación | Medidas típicas de mobiliario de eventos |
| Distribución inicial del público y compras | Sintético | Generado con semillas fijas |

En OSM no existe un elemento llamado "Explanada Cayalá". Se usa el lote abierto más grande junto a Cardales de Cayalá, que coincide con la "Explanada Cardales" mencionada por Prensa Libre para los conciertos de noviembre de 2022. Esta identificación es una suposición del autor.

Datos de mapa: colaboradores de OpenStreetMap.

## Uso de inteligencia artificial

El código y los textos de este repositorio se escribieron con ayuda de Claude Code (Anthropic), bajo la dirección y revisión del autor. El autor definió el problema, revisó cada parte antes de integrarla y es responsable de las decisiones finales.
