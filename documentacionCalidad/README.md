# Calidad de los datos

Apartado pedido en el README: consultas, resultado, denominador y decisión. No es un generador de informes ni un panel de la web. La cuarentena que el enunciado pide conservar está en la tabla `cuarentena`.

Consultas hechas el 28 de octubre de 2026 sobre PostgreSQL, base `observatorio`. Los porcentajes de problemas no se suman: un mismo evento puede fallar en más de una cosa.

## Magnitudes nulas

Conjunto: `evento_actual`, año 2025, magnitud pedida en la descarga mayor o igual que 4. Denominador: 18301 eventos.

```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE mag IS NULL) AS sin_mag
FROM evento_actual
WHERE occurred_at >= '2025-01-01'
  AND occurred_at < '2026-01-01'
  AND mag >= 4;
```

Resultado: 18301 eventos, 0 magnitudes nulas, 0 %. La petición a USGS ya exigía magnitud 4, así que este cero no demuestra que USGS nunca publique una magnitud vacía.

El feed vivo sí puede traerla. En el momento de la consulta, las últimas 24 horas en modo `live` tenían 234 eventos y 0 magnitudes nulas (0 %). El caso de prueba `prueba-mar` está guardado con magnitud nula y `mode = replay`, así que no entra en ese recuento vivo.

Decisión: una magnitud nula se guarda nula. No se sustituye por cero. Al calcular la media, los nulos quedan fuera y el denominador es el número de eventos que sí tienen magnitud. En el mapa se ve como ND. Un filtro de magnitud mínima tampoco los deja pasar, porque un nulo no cumple `mag >= umbral`.

## Duplicados y revisiones

Conjunto: toda la base en el momento de la consulta.

```sql
SELECT COUNT(*) AS actuales, COUNT(DISTINCT event_id) AS ids FROM evento_actual;
SELECT COUNT(*) AS versiones, COUNT(DISTINCT event_id) AS ids FROM evento_version;
```

Resultado: 18557 filas en `evento_actual` y 18557 identificadores distintos. Hay una fila vigente por evento. `evento_version` tiene 18595 filas y los mismos 18557 identificadores: 38 filas de más son revisiones, no terremotos nuevos. La clave de versión es `(event_id, updated_ms)`.

Antes y después, en la reproducción de `us6000pjr6`:

| Momento | Dónde | Magnitud | `updated_ms` |
|---|---|---|---|
| Antes de la revisión controlada | `replay.evento_actual` | 4.2 | 1742247237040 |
| Después de repetir el mismo `updated` | recuento de `replay` | 8 eventos y 8 ids; las versiones no pasaron de 8 | el mismo |
| Después de la revisión | `replay.evento_actual` | 4.4 | 1742247297040 |
| La fila viva, sin tocarla | `evento_actual` | 4.2 | 1742247237040 |

Al terminar, `replay.evento_actual` tiene 8 eventos y 8 ids, y `replay.evento_version` tiene 9 versiones. La repetición no aumentó el número de terremotos. La revisión cambió la magnitud solo en el esquema `replay`.

Decisión: reenviar la misma versión no crea otro terremoto. Una revisión posterior actualiza la fila vigente y añade una versión. Una versión más antigua no sustituye a la más reciente.

## País ausente

Mismo conjunto de 2025 y mismo denominador, 18301.

```sql
SELECT COUNT(*) FILTER (WHERE country_id IS NULL) AS sin_pais
FROM evento_actual
WHERE occurred_at >= '2025-01-01'
  AND occurred_at < '2026-01-01'
  AND mag >= 4;
```

Resultado: 14349 sin país, 14349 / 18301 = 78,4 %. En las últimas 24 horas vivas: 50 de 234, un 21,4 %.

Decisión: si el punto no cae dentro de un polígono, `country_id` se queda nulo y el panel escribe «Sin país asignado». No se copia el país del texto `place` ni se asigna el país más cercano. `prueba-mar` sigue en la tabla con país nulo.

## Anomalías

La tabla `cuarentena` guarda el motivo y el mensaje original.

```sql
SELECT motivo, COUNT(*) FROM cuarentena GROUP BY motivo ORDER BY motivo;
```

| Motivo | Filas |
|---|---|
| `coordenadas fuera de rango o no finitas` | 1 |
| `tipo distinto de earthquake: explosion` | 6 |

`prueba-malo` es la fila de coordenadas. El original guardado es `[-3.7, 145, 5]`. No hay ninguna fila con ese id en `evento_actual`, así que no se dibuja un punto inventado.

Otras reglas, con el registro que las prueba:

| Caso | Qué llegó | Qué se hizo |
|---|---|---|
| `prueba-mag-neg` | magnitud −0,4 | Se guardó. Una magnitud negativa no se rechaza solo por el signo |
| `prueba-esp` | profundidad −1,2 km, país `ESP` | Se guardó. En USGS una profundidad negativa puede ser elevación respecto a su datum |
| Explosiones del feed | `type` distinto de `earthquake` | Cuarentena con el motivo y el tipo. No entran en el análisis |

Decisión: lo que no se puede tratar se conserva en cuarentena con motivo y original. El offset de Kafka se confirma después de esa inserción, para no dejar el mensaje reintentándose sin fin.

## Actualidad y exactitud

`last_ingestion` es la última fila de `consulta_fuente` con resultado correcto. No es la hora a la que el panel generó la respuesta. Si esa ingesta pasa de 5 minutos, el panel avisa de que el productor parece parado.

El país se contrasta con el polígono de Natural Earth a escala 1:110m, no con un catastro de fronteras. `(-3.7, 40.4)` cae en `ESP`. `(-30, 25)` no cae en ningún polígono. No se afirma precisión legal.

Salir del feed de 24 horas no borra el evento. Las bajas o fusiones que USGS haga cuando el evento ya no está en esa ventana no se reconcilian.
