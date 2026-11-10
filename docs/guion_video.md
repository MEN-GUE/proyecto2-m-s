# Guion del video: Proyecto 2, Modelización y Simulación

Duración objetivo: 14:30. Límite del curso: 15:00, incluyendo demostración y defensa.
Estructura: los seis bloques oficiales del PDF (2, 2, 3, 3, 3 y 2 minutos).

El texto marcado como **Decir** es para leerlo tal cual, a ritmo tranquilo (unas 140 palabras por minuto). Si vas largo de tiempo, quita las frases marcadas como (opcional).

---

## Antes de grabar

1. Haz commit de todo lo pendiente, para que `git status` salga limpio en la demostración.
2. **Terminal 1**, en la carpeta del proyecto, con letra grande (unos 16 pt). Ten a mano estos tres comandos; córrelos una vez antes de grabar para comprobar que todo responde:

```bash
.venv/bin/python -m pytest -q
```

```bash
.venv/bin/python -m src.simulation.experiments
```

```bash
git status --short results/
```

3. **Terminal 2**: levanta el visor y déjalo corriendo.

```bash
cd web
```

```bash
deno task dev
```

4. **Navegador** en http://localhost:5173, con zoom al 100 %. Recarga con Ctrl+Shift+R justo antes de grabar. Deja "Base, 500 personas" a la izquierda y "PSO, 500 personas" a la derecha, la velocidad en 4x y la densidad activada. En el formulario "Nueva corrida" deja Montaje = PSO y Semilla = 2024.
5. Ten abierta la presentación de Google Slides en modo presentación. Sus 20 diapositivas ya traen las figuras, las ecuaciones y el diagrama del sistema; recárgala antes de grabar para ver la última versión.
6. Graba la pantalla en 1920 x 1080 y silencia las notificaciones.
7. **Respaldo:** graba aparte unos 30 s del visor reproduciendo base contra PSO. Si la demostración en vivo falla, usas ese clip, como pide el PDF.
8. Conviene grabar cada bloque por separado y unirlos al final; así repites solo el que salga mal.

## Diapositivas

La presentación de Google Slides tiene 20 diapositivas. Cada título dice la idea principal, así que el video se puede seguir solo con los títulos.

| # | Título en pantalla | Entra en |
| --- | --- | --- |
| 1 | Salida del público al cierre de un concierto en la Explanada Cayalá | 00:00 |
| 2 | Al cierre, las filas de las barras se cruzan con la salida | 00:20 |
| 3 | ¿Cuánto mejora la salida si un PSO ubica barras y vallas? | 01:30 |
| 4 | Cada persona va a su meta y se aparta de otros y de los muros | 02:00 |
| 5 | El PSO propone un montaje y la simulación lo valida y lo califica | 02:35 |
| 6 | Cada persona tiene su rapidez, decide si compra y espera su turno | 02:50 |
| 7 | El modelo cubre un cierre ordinario y respeta dos restricciones | 03:30 |
| 8 | Un enjambre de 12 partículas busca el montaje entre 14 variables | 04:00 |
| 9 | Solo 1 % de los montajes al azar pasa el validador | 05:00 |
| 10 | Tres reinicios dan montajes distintos; el mejor logra J = 0.956 | 05:50 |
| 11 | Hay varios óptimos locales y, sin paro, el enjambre aprende el ruido | 06:25 |
| 12 | Demostración | 07:00 |
| 13 | El modelo calibrado reproduce el flujo de Jülich con 9 % de error | 10:00 |
| 14 | El modelo subestima en 34 % la densidad medida en Jülich | 10:35 |
| 15 | El PSO baja la densidad pico 7.1 % y el tiempo de salida 1.4 % | 10:50 |
| 16 | Con más público o atención lenta, el PSO sigue bajando la densidad | 11:40 |
| 17 | La mejora es simulada, no medida | 12:15 |
| 18 | Recomendación: sacar las barras del camino al portón suroeste | 13:00 |
| 19 | Preguntas anticipadas | 13:40 |
| 20 | Gracias, con fuentes y uso de IA | 14:35 |

---

## Bloque 1. Problema real, objetivo y fuente (00:00 a 02:00)

### 00:00 a 00:20 | Pantalla: diapositiva 1

**Decir:**
> Buenas. Soy Juan Fernando Menéndez Guerra, carné 17444. Este es mi proyecto 2 de Modelización y Simulación, un trabajo individual aprobado por el docente. El tema es la salida del público al terminar un concierto en la Explanada Cayalá.

### 00:20 a 01:10 | Pantalla: diapositiva 2

**Decir:**
> La Explanada Cayalá, en la zona 16, es un terreno abierto para conciertos grandes; en noviembre de 2022, Prensa Libre reportó que se esperaban más de 15 mil personas por día. Al terminar, casi todos salen a la vez y una parte pasa antes por las barras cashless. Las filas y la corriente hacia los portones se cruzan, y ahí se forman tapones. Según Fruin, por encima de unas 4 personas por metro cuadrado el contacto físico es inevitable y la circulación casi se detiene. Por eso, dónde se ponen las barras y las vallas decide dónde se amontona la gente.

### 01:10 a 02:00 | Pantalla: sigue en la diapositiva 2 mientras hablas del polígono; pasa a la 3 en "Ahí hay 500 personas"

**Decir:**
> No modelo toda la explanada, sino la zona crítica de salida. Tomé el polígono real del terreno en OpenStreetMap, donde aparece como Arena Gallo, y en su extremo sur una ventana de 80 por 50 metros. Ahí hay 500 personas, 4 barras con 3 puntos de atención cada una, 2 vallas y 2 portones de 4 metros.
> La pregunta es: ¿en qué porcentaje bajan la densidad pico y el tiempo de salida si barras y vallas se ubican con un enjambre de partículas, frente al montaje tradicional con las barras en el borde oeste? Mido la densidad pico, en personas por metro cuadrado, y T95, los segundos hasta que sale el 95 por ciento del público. Las dos se quieren bajar.

---

## Bloque 2. Modelo, variables, restricciones y supuestos (02:00 a 04:00)

### 02:00 a 02:35 | Pantalla: diapositiva 4

**Decir:**
> El movimiento sigue el modelo de fuerzas sociales de Helbing. Cada persona quiere ir a su objetivo con su propia rapidez y corrige su velocidad con un tiempo de relajación tau; las demás personas y las paredes la empujan con una fuerza que baja exponencialmente con la distancia. Se integra con Euler semi implícito cada 0.05 segundos, y cada persona sigue un mapa de distancias calculado con Dijkstra para no atorarse detrás de una barra.

### 02:35 a 02:50 | Pantalla: diapositiva 5

**Decir:**
> El diagrama muestra el ciclo: el montaje pasa por un validador; si es válido se simula, y las métricas vuelven al enjambre, que propone otro montaje.

### 02:50 a 03:30 | Pantalla: diapositiva 6

**Decir:**
> Cada persona tiene posición, velocidad, rapidez deseada, radio y un estado: va a una fila, está en ella, va a la salida o ya salió. La rapidez deseada es normal con media de 1.34 metros por segundo; compra el 35 por ciento, con una Bernoulli; y la atención es Log-Normal con media de 16.4 segundos. Las filas atienden en orden de llegada, con tres reglas para que no se traben: quien quedó lejos rodea obstáculos, quien sale evita las filas y, si el primero no llega en 20 segundos, se le atiende igual.

### 03:30 a 04:00 | Pantalla: diapositiva 7

**Decir:**
> Supongo terreno plano, buena iluminación y un cierre normal, sin pánico; quedan fuera sismos, riñas, lluvia y emergencias médicas. Las restricciones son dos: ningún mueble puede bloquear rutas de evacuación, y ninguna celda transitable puede pasar de 4 personas por metro cuadrado. (opcional) Todo vive en arreglos compilados con Numba: una evacuación completa tarda menos de un segundo.

---

## Bloque 3. Técnica investigada e integración (04:00 a 07:00)

### 04:00 a 05:00 | Pantalla: diapositiva 8

**Decir:**
> La técnica adicional es el enjambre de partículas, de Kennedy y Eberhart. Cada partícula es un montaje: un vector de 14 números con el centro de las 4 barras y el punto medio y el ángulo de las 2 vallas. En cada iteración combina su inercia, su mejor posición y la mejor del enjambre.
> Usé 12 partículas, 25 iteraciones, inercia de 0.9 a 0.4 como Shi y Eberhart, coeficientes de 1.49, cercanos al valor estable de Clerc y Kennedy, y paro si la mejora es menor a 0.001 durante 5 iteraciones. Elegí PSO porque la función sale de una simulación con azar, sin derivadas, y porque las partículas se mueven de forma continua; un algoritmo genético mezcla coordenadas de montajes distintos y produce barras encimadas. Lo programé desde cero; NumPy solo maneja los arreglos.

### 05:00 a 05:50 | Pantalla: diapositiva 9

**Decir:**
> Antes de simular, un validador hecho desde cero revisa cinco reglas sobre una grilla: nada fuera del recinto, nada encimado ni pasos menores a 1.12 metros, nada en el círculo de 5 metros de cada portón, 8 metros libres para cada fila y salida desde toda zona, comprobada con Dijkstra. Solo el 1 por ciento de los montajes al azar las cumple.
> La función objetivo pondera 0.6 la densidad y 0.4 el tiempo, normalizados con la base, que vale exactamente 1: todo valor menor es mejora. Los montajes inválidos no se simulan y reciben una penalización, y pasar de 4 personas por metro cuadrado se castiga con un término cuadrático.

### 05:50 a 06:25 | Pantalla: diapositiva 10

**Decir:**
> Para que la búsqueda quepa en una computadora, cada partícula se evalúa con 3 semillas, y las 12 partículas se simulan en paralelo. Repetí la búsqueda tres veces, con semillas distintas del enjambre, y volví a evaluar el mejor montaje de cada una con 10 semillas nuevas. Las 30 semillas del experimento final nunca se usan en la búsqueda, así la comparación no queda sesgada. El ganador obtuvo J igual a 0.956.

### 06:25 a 07:00 | Pantalla: diapositiva 11

**Decir:**
> El análisis de estancamiento muestra los límites. Entre el 60 y el 87 por ciento de las partículas cae en montajes inválidos en cada iteración. Los tres reinicios terminan en montajes distintos, separados entre 9 y 16 metros por barra, con J parecidos: hay varios óptimos locales. Y sin paro temprano, el valor de búsqueda mejora, pero con semillas nuevas empeora: el enjambre aprende el ruido de sus 3 semillas. (opcional) En la función de Rastrigin, con esta configuración, solo 1 de 20 corridas llegó al óptimo global.

---

## Bloque 4. Demostración del programa y ejecución (07:00 a 10:00)

### 07:00 a 07:25 | Pantalla: diapositiva 12 unos segundos; luego la terminal 1 y el explorador de archivos con `src/`

**Acción:** muestra las carpetas `src/model`, `src/simulation`, `src/optimizer` y `src/visualization`.

**Decir:**
> El repositorio separa modelo, simulación, optimizador y visualización, como pide el enunciado. Todo se reproduce con tres comandos del README: crear el entorno, instalar las dependencias y correr run_all, que tarda unos 5 minutos y regenera todas las tablas y figuras del informe.

### 07:25 a 07:50 | Pantalla: terminal 1

**Acción:** corre `.venv/bin/python -m pytest -q`. Tarda unos 6 s y debe decir "11 passed".

**Decir:**
> Primero, las pruebas automáticas: once pruebas en unos 5 segundos. Tres son las de verificación del modelo: que el número de personas se conserva exactamente, que nadie cruza un muro y que una persona sola tarda lo que da la solución exacta sin repulsiones. En esta última, la diferencia fue de tres centésimas de segundo.

### 07:50 a 08:35 | Pantalla: terminal 1

**Acción:** corre `.venv/bin/python -m src.simulation.experiments` (unos 20 s). Mientras corre, habla. Al terminar, señala las dos filas "PSO vs Base". Después corre `git status --short results/`, que no debe mostrar nada.

**Decir:**
> Ahora corro en vivo toda la matriz experimental: 6 condiciones por 30 réplicas, es decir, 180 evacuaciones completas, con las semillas 1001 a 1030. Tarda unos 20 segundos, usando todos los núcleos.
> (al terminar) Ahí está la comparación pareada: el PSO baja la densidad pico 7.1 por ciento y el T95 1.4 por ciento. Y git status no muestra cambios: los archivos que se acaban de generar son idénticos a los guardados, así que el experimento es reproducible.

### 08:35 a 09:35 | Pantalla: navegador con el visor

**Acción:** presiona "Reproducir". Pausa cuando el tiempo marque cerca de t = 40 s. Señala con el cursor la corriente hacia el portón suroeste en cada panel.

**Decir:**
> Este es el visor web, hecho con Deno Fresh. A la izquierda, el montaje tradicional, con las barras en el borde oeste; a la derecha, el del enjambre de partículas. Los puntos azules caminan directo a un portón y los rojos pasan antes por una barra.
> (reproduciendo) Al inicio, el público se divide en dos corrientes, una para cada portón.
> (en pausa) Fíjense en la base: la corriente que va al portón suroeste baja pegada al final de las filas de las barras y se aprieta contra el portón; la capa de color marca dónde sube la densidad. En el montaje del PSO, las barras están en el centro y el norte, y la valla vertical separa las corrientes que van a cada portón. Abajo, la gráfica compara el porcentaje evacuado en el tiempo.

### 09:35 a 10:00 | Pantalla: formulario "Nueva corrida"

**Acción:** con Montaje = PSO y Semilla = 2024, presiona "Simular". En unos 2 s la corrida nueva aparece en el panel derecho.

**Decir:**
> Por último, el botón Simular lanza una corrida nueva en Python con la semilla que elija, por ejemplo la 2024. En un par de segundos aparece en el panel derecho, con sus métricas. Si algo falla al presentar, el visor tiene corridas guardadas como respaldo.

---

## Bloque 5. Resultados, validación y comparación con la vida real (10:00 a 13:00)

### 10:00 a 10:35 | Pantalla: diapositiva 13

**Decir:**
> Antes de interpretar la mejora, hay que ver qué tan cerca está el modelo de la realidad. Lo calibré con las trayectorias reales del experimento Bottleneck Caserne de Jülich, de 2006: 10 corridas de unas 175 personas cruzando puertas de 0.9 a 2.5 metros. Probé 15 valores de tau y el mejor fue 0.5 segundos, con un error absoluto medio de 0.17 personas por metro por segundo, un 9 por ciento. En promedio reproduce el flujo real con 1.5 por ciento de diferencia.

### 10:35 a 10:50 | Pantalla: diapositiva 14

**Decir:**
> Pero, con el mismo método de medición, subestima la densidad en 34 por ciento, porque no tiene fuerzas de contacto: predice bien cuánta gente pasa, pero no qué tan apretada está.

### 10:50 a 11:40 | Pantalla: diapositiva 15

**Decir:**
> Con el montaje ya fijo, corrí 30 réplicas por condición. Frente a la base, el PSO baja la densidad pico de 2.28 a 2.12 personas por metro cuadrado, un 7.1 por ciento, con intervalo de confianza del 95 por ciento entre 6.0 y 8.2. El T95 baja de 254 a 250 segundos, un 1.4 por ciento: es pequeño, pero significativo.
> El mapa de calor explica por qué. En la base, la corriente hacia el portón suroeste queda pegada a las filas; con el PSO, las barras salen de ese camino y las vallas separan las corrientes. En las 180 corridas se conserva exactamente el número de personas, nadie cruza un muro, todos salen y ninguna corrida pasa de 4 personas por metro cuadrado.

### 11:40 a 12:15 | Pantalla: diapositiva 16

**Decir:**
> En la sensibilidad, con 20 por ciento más de público, el PSO sigue bajando la densidad: 4.8 por ciento frente a la base con el mismo sobrecupo. Con atención 50 por ciento más lenta, baja 7 por ciento. Pero el tiempo depende sobre todo de las barras: con atención lenta, T95 sube 40 por ciento, mientras que mover las barras lo cambia menos de 2 por ciento. Con 175 compradores y 12 puntos de atención, las barras tardan unos 4 minutos en atender a todos.

### 12:15 a 13:00 | Pantalla: diapositiva 17

**Decir:**
> Distingo cuatro tipos de dato: el polígono de OpenStreetMap es real, Jülich es una referencia pública medida, los portones y las barras son estimaciones, y el público inicial es sintético. De la explanada no hay mediciones públicas. En los portones, el modelo deja pasar 2.4 personas por metro por segundo, más que los 1.9 de Jülich, así que la salida real sería algo más lenta. Corrigiendo la densidad con el factor de Jülich, el pico quedaría cerca de 3.5 en la base y 3.2 con el PSO, todavía bajo 4. Todo esto es mejora simulada, no medida en un concierto real.

---

## Bloque 6. Conclusiones, preguntas y defensa técnica (13:00 a 15:00)

### 13:00 a 13:40 | Pantalla: diapositiva 18

**Decir:**
> Respondiendo la pregunta: con el montaje del PSO la densidad pico baja 7 por ciento y el tiempo de salida 1.4 por ciento, una mejora real dentro del modelo que solo implica reacomodar el mobiliario. Recomiendo no alinear las barras en el borde oeste, junto al camino al portón suroeste, sino llevarlas al centro y al norte en dos pares; poner una valla entre los portones y otra en diagonal antes del portón suroeste; y, para bajar el tiempo, aumentar la capacidad de atención cashless. Antes de aplicarlo, conviene medir en un evento real para recalibrar la densidad.

### 13:40 a 14:35 | Pantalla: diapositiva 19

**Decir:**
> Respondo de una vez las preguntas que espero.
> ¿Bajo qué condiciones vale el resultado? Para un cierre ordinario, sin pánico, con 500 a 600 personas en esta zona y atención de 16 a 25 segundos.
> ¿Qué tan confiable es la comparación? Dentro del modelo, bastante: son 30 réplicas pareadas, con semillas separadas de la búsqueda, y los intervalos de la densidad no tocan el cero. Frente a la realidad, menos, porque el modelo subestima la densidad y la posición de los portones es una estimación.
> ¿Qué limitaciones quedan? No hay datos reales del recinto, solo calibré tau, y con más de 4 o 5 personas por metro cuadrado o con miles de personas el modelo deja de valer. Calibrar también la densidad es el siguiente paso.

### 14:35 a 14:55 | Pantalla: diapositiva 20

**Decir:**
> Las fuentes y el uso de inteligencia artificial están declarados en el informe: la usé para parte del código, pruebas, correcciones y aclaraciones. Todos los números salen del repositorio y se regeneran con run_all. Muchas gracias.

---

## Qué pide el PDF y dónde se cubre

| Requisito del PDF | Momento del video |
| --- | --- |
| Problema real, objetivo y fuente de referencia | 00:20 a 02:00 |
| Pregunta de investigación y métrica con unidades y sentido | 01:10 a 02:00 |
| Modelo, variables, distribuciones, reglas y ecuaciones | 02:00 a 03:30 |
| Supuestos, restricciones y exclusiones | 03:30 a 04:00 |
| Técnica investigada: fundamento, parámetros, por qué y limitaciones | 04:00 a 05:00 y 06:25 a 07:00 |
| Integración de la técnica con la simulación y restricciones por código | 05:00 a 06:25 |
| Demostración verificable y reproducible | 07:00 a 10:00 |
| Al menos tres condiciones, 30 réplicas, semillas y dispersión | 07:50 a 08:35 y 10:50 a 12:15 |
| Verificación interna del modelo | 07:25 a 07:50 y 10:50 a 11:40 |
| Correspondencia del modelo base con la referencia real, antes de la mejora | 10:00 a 10:50 |
| Datos reales, públicos, estimados y sintéticos diferenciados | 12:15 a 13:00 |
| Mejora simulada frente a mejora real | 12:15 a 13:00 |
| Qué mejoró y cuánto | 13:00 a 13:40 |
| Bajo qué condiciones, qué tan confiable y qué limitaciones quedan | 13:40 a 14:35 |
| Conclusión y recomendación concreta | 13:00 a 13:40 |
| Fuentes y uso de IA citados | 14:35 a 14:55 |
| No exceder 15 minutos | Cierre a las 14:55 |
