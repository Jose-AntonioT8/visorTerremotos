# Guion del vídeo de evidencias

Un solo recorrido, en este orden. El panel es una sola página: no cambies de ruta, baja con el scroll. El resto son pestañas del navegador, la terminal y dos documentos.

Antes de darle a grabar: `docker compose ps` con los cinco servicios en marcha (kafka, postgres, productor, consumidor, api), ngrok activo y el panel abierto en `https://visorterremotos.netlify.app`. No enseñes `.env`, contraseñas ni `node_modules`. No digas que los gráficos predicen terremotos o miden riesgo.

`informeCalidad.md` no sirve como prueba: es una nota de una línea. El apartado de calidad que se enseña es `documentacionCalidad/README.md`. No hay un `docs/conclusiones.md`: las tres conclusiones se leen de los números que haya ese día en el panel, no de una cifra escrita de antemano.

## 1. Los cinco servicios

Pantalla: terminal, en la raíz del repo.

```text
docker compose ps
```

Que se vean los cinco nombres y que postgres y kafka estén healthy. Frase: el sistema entra con un solo Compose; la API escucha en el puerto 8000 del host y el navegador no llama a Kafka.

Criterio: cierre operativo de la rúbrica.

## 2. De dónde salen los datos

Pantalla: `FUENTES-Y-LICENCIAS.md`, y luego el log del productor.

```text
docker compose logs productor --tail 30
```

Que se vea una consulta al feed de USGS (`all_day.geojson`) o al histórico FDSN, no un fichero inventado. Frase: hay tres fuentes. El feed se consulta solo cada unos 60 segundos, el histórico de 2025 ya está cargado y el país sale del catálogo Natural Earth, no del texto `place`.

Criterio: extracción.

## 3. Un evento, con sus tipos

Pantalla: `https://visorterremotos.netlify.app/api/eventos`.

Abre el JSON. Señala un `Feature`: `coordinates` en orden longitud, latitud, profundidad en km; `mag` numérico o `null`; `time` y `updated` en milisegundos UTC; `country_id` o `null`. En `metadata`, `generated` y `last_ingestion` no son la misma cifra. Frase: la API no rellena un nulo con cero ni cambia el orden de las coordenadas.

Criterio: extracción (tipos, unidades y límites) y contrato de la API.

## 4. Calidad: qué se midió y qué se decidió

Pantalla: `documentacionCalidad/README.md`, de arriba abajo, sin saltarte las tablas.

Para en cuatro sitios:

- Magnitudes nulas. Denominador escrito, resultado y la decisión: se guardan nulas y no entran en la media.
- Duplicados. `evento_actual` tiene tantos identificadores como filas; las filas de más están en `evento_version`.
- País ausente. El porcentaje con su denominador, y la frase de que no se copia el país desde `place`.
- Cuarentena. La tabla de motivos, con la coordenada inválida y las explosiones fuera de `evento_actual`.

Di la fecha de esas consultas (28 de octubre de 2026). Si quieres cifras de hoy, ejecuta en otra toma las mismas SQL del documento; no mezcles los dos momentos en la misma frase.

Criterio: calidad.

## 5. El panel no disfraza los nulos

Pantalla: el panel, bloque de arriba y el inicio de «Periodo consultado».

Que se lean a la vez: modo `API · datos del backend`, «Última ingesta USGS UTC», «Sin magnitud», «Sin profundidad» y «Sin país». Baja hasta la tabla y enseña una celda `ND` si hay una magnitud nula, o di que en esta ventana no hay ninguna y que el caso de prueba está en `replay`. En el pie, la leyenda del círculo gris: sin profundidad no se pinta como cero.

Criterio: calidad y prueba «magnitud nula».

## 6. País por polígono, no por el texto

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT event_id, country_id, place FROM evento_actual WHERE event_id IN ('prueba-esp','prueba-mar');"
```

`prueba-esp` tiene país y `prueba-mar` no, aunque el texto del lugar diga otra cosa. Después, en el panel, filtro País = «Sin país asignado» y Aplicar. El mapa, la tabla y «Sin país» del periodo tienen que cuadrar. Vuelve a «Todos» antes de seguir.

Criterio: modelado y prueba «evento marítimo».

## 7. Una fila vigente y las revisiones aparte

Pantalla: terminal, y el apartado «Duplicados y revisiones» de `documentacionCalidad/README.md`.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT (SELECT count(*) FROM evento_actual) AS actuales, (SELECT count(DISTINCT event_id) FROM evento_actual) AS ids, (SELECT count(*) FROM evento_version) AS versiones;"
```

`actuales` e `ids` iguales. `versiones` mayor o igual. En el documento, señala la fila de `us6000pjr6`: repetir el mismo `updated` no sumó terremotos, la revisión posterior cambió solo `replay` y la fila viva se quedó en 4,2.

Criterio: modelado. Pruebas: misma versión reenviada, versión posterior, versión antigua que no pisa la nueva.

## 8. Coordenada imposible, sin punto dibujado

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT motivo, original->>'id' AS id FROM cuarentena WHERE original->>'id' = 'prueba-malo'; SELECT count(*) AS en_vivo FROM evento_actual WHERE event_id = 'prueba-malo';"
```

Motivo de coordenadas y `en_vivo` a cero. Frase: el mensaje se conserva con el original y el offset se confirma después, así no se reintenta para siempre ni se inventa un punto.

Criterio: calidad. Prueba: coordenadas inválidas.

## 9. Mapa, ventanas, países y distribuciones

Pantalla: el panel, desde el mapa hasta el final de «Distribución de profundidad». Una toma continua, bajando despacio.

Enseña, en este orden: el mapa con la leyenda de profundidad, «Ventanas horarias UTC», «Conteo por país» (incluida la barra «Sin país asignado» si sale), la media de magnitud con su denominador y los nulos fuera, y lo mismo en profundidad. Si el gráfico de ventanas dice que agrupa por día, lee esa frase: la consulta sigue siendo por hora UTC.

Criterio: análisis (tres análisis distintos: ventanas, distribuciones, conteo por país).

## 10. Los filtros mueven las tres vistas a la vez

Pantalla: el panel. Anota en voz el total de «Periodo consultado» antes de filtrar.

Pon magnitud mínima 5 y un país que tenga eventos. Aplicar. En el mismo plano tienen que cambiar el mapa, el total del periodo, las barras y las filas de la tabla. Lee la nota gris: el filtro de fechas no cambia los dos periodos de la comparación. Quita los filtros con el país en «Todos» y la magnitud vacía, y Aplicar, para dejar la vista limpia.

Criterio: análisis y la comprobación de filtros coherentes.

## 11. Comparación equivalente y tres conclusiones

Pantalla: «Comparación histórica», sin filtro de país y con la magnitud del mapa vacía o por debajo de 4.

Lee lo que haya escrito ahí, sin sustituir cifras: periodo reciente, media diaria del año histórico, días del denominador, corte de magnitud y la variación. Si aparece el aviso de que el corte se mantiene en 4 o más, léelo: el feed reciente y el histórico de 2025 no se mezclan por debajo de ese corte. La frase de días en cero también se lee.

Di tres conclusiones seguidas, cada una con la cifra que acabas de enseñar, el ámbito (mundial o el país filtrado) y el periodo. Ninguna puede ser «habrá un terremoto» ni «esta zona es peligrosa». Ejemplo de forma, no de contenido: «En estas 24 horas el recuento está un X % por encima de la media diaria de 2025, con el mismo corte de magnitud 4 y los días en cero dentro del denominador».

Criterio: análisis, nivel de conclusiones. Este plano cubre lo que no está redactado en un fichero: si no lo dices con las cifras de la pantalla, la prueba no queda.

## 12. Reproducción aislada

Pantalla: el panel. Pulsa «Ver reproducción».

Tiene que verse la palabra REPRODUCCIÓN y el texto de que esos eventos no entran en el análisis en vivo. La comparación histórica, en esta vista, dice que no se calcula. La tabla trae fechas originales, no la hora de la grabación. Pulsa «Volver al directo» y comprueba que la comparación vuelve.

Si hace falta el origen: `pipeline/reproducir.py` publica en el topic `eventos-replay` y el consumidor escribe en el esquema `replay`, no en `evento_actual`.

Criterio: prueba «reproducción histórica».

## 13. Túnel cerrado y túnel otra vez

Pantalla: el panel, con la hora de «Última lectura UTC» visible. Para ngrok en la terminal, sin cerrar el navegador.

Espera a que el estado deje de decir que la consulta se completó. Tiene que salir un aviso de fallo y la hora de última lectura no puede saltar a «ahora» como si hubiera datos nuevos. Los puntos que ya estaban siguen.

Vuelve a arrancar ngrok. Si el dominio es el mismo que `TUNEL` en `frontend/netlify/edge-functions/proxy-api.js`, no toques nada: en menos de un minuto el estado vuelve a «API accesible · consulta completada». Si ngrok te da otro dominio, di en voz que hay que actualizar `TUNEL` y republicar; no lo presentes como un fallo del panel.

Criterio: pruebas del túnel.

## 14. Medición y coste

Pantalla: terminal. Los datos de esta orden son sintéticos y no entran en el mapa.

```text
docker compose run --rm --no-deps -e PAISES_GEOJSON=/datos/paises.geojson consumidor python mediciones.py
```

Esa imagen no copia `mediciones.py`. Si el contenedor no lo encuentra, lanza la misma orden montando el código:

```text
docker compose run --rm --no-deps --entrypoint python -v "${PWD}/pipeline:/work" -e PYTHONPATH=/work -e PAISES_GEOJSON=/datos/paises.geojson consumidor /work/mediciones.py
```

Enseña las tres tallas de la búsqueda (lista frente a diccionario), el punto en polígono y la agregación por hora con y sin índice. Di que son tiempos de esta máquina, no una previsión. Cierra con una frase de coste con el supuesto a la vista: electricidad, almacenamiento o tiempo de desarrollo, y que una cuota gratuita no es coste cero. Si no tienes esa frase escrita, dilo en este plano; no hay otro documento en el repo que la respalde.

Criterio: reflexión.

## 15. Cierre, en una sentada

Pantalla: el panel en directo, sin reproducción y sin filtros.

Recorre en voz un identificador de la tabla: USGS, Kafka, consumidor, fila de `evento_actual`, API y círculo del mapa. Una decisión tuya, una sola: por ejemplo que el país sale del polígono y el mar se queda sin país, o que la comparación no baja de magnitud 4.

## Orden y duración orientativa

| Toma | Minutos | Qué cubre |
|---|---|---|
| 1–3 | 2 | Servicios, fuentes y tipos |
| 4–5 | 3 | Calidad y nulos |
| 6–8 | 3 | País, revisiones y cuarentena |
| 9–11 | 4 | Análisis, filtros y tres conclusiones |
| 12–13 | 2 | Reproducción y túnel |
| 14–15 | 3 | Medición, coste y recorrido de un evento |

No hace falta un segundo mapa, ni Spark, ni un panel de métricas aparte. Esas ausencias no se justifican en el vídeo.
