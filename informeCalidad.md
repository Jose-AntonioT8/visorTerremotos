# Calidad de los datos

Apartado pedido en el README: consultas, resultado, denominador y decisión. No es un generador de informes ni un panel de la web. La cuarentena que el enunciado pide conservar está en la tabla `cuarentena`.

Consultas hechas el 15 de noviembre de 2026, a las 18:09 UTC, sobre PostgreSQL, base `observatorio`. Los porcentajes de problemas no se suman: un mismo evento puede fallar en más de una cosa. El año 2025 con magnitud pedida mayor o igual que 4 sigue teniendo 18301 eventos: es el mismo histórico. Lo que cambia desde el 28 de octubre es el país de 1116 de ellos, el tamaño del feed vivo y el número de revisiones.

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

El feed vivo sí puede traerla. A las 18:09 UTC, las últimas 24 horas en modo `live` tenían 185 eventos y 0 magnitudes nulas (0 %). En toda la tabla hay 1 magnitud nula: `prueba-mar`, con `mode = replay`, fuera de ese recuento vivo y fuera del histórico de 2025.

Decisión: una magnitud nula se guarda nula. No se sustituye por cero. Al calcular la media, los nulos quedan fuera y el denominador es el número de eventos que sí tienen magnitud. En el mapa se ve como ND. Un filtro de magnitud mínima tampoco los deja pasar, porque un nulo no cumple `mag >= umbral`. Corregir `prueba-mar` poniéndole un cero tocaría 1 fila y sesgaría cualquier media que la incluyera.

## Duplicados y revisiones

Conjunto: toda la base a las 18:09 UTC.

```sql
SELECT COUNT(*) AS actuales, COUNT(DISTINCT event_id) AS ids FROM evento_actual;
SELECT COUNT(*) AS versiones, COUNT(DISTINCT event_id) AS ids FROM evento_version;
```

Resultado: 18750 filas en `evento_actual` y 18750 identificadores distintos. Hay una fila vigente por evento. `evento_version` tiene 18795 filas y los mismos 18750 identificadores: 45 filas de más son revisiones, no terremotos nuevos. Esas 45 filas pertenecen a 25 eventos. La clave de versión es `(event_id, updated_ms)`. El 28 de octubre eran 18557 vigentes y 38 revisiones de más: el feed ha seguido entrando.

Antes y después, en la reproducción de `us6000pjr6`, sin cambio desde octubre:

| Momento | Dónde | Magnitud | `updated_ms` |
|---|---|---|---|
| Antes de la revisión controlada | `replay.evento_actual` | 4.2 | 1742247237040 |
| Después de repetir el mismo `updated` | recuento de `replay` | 8 eventos y 8 ids; las versiones no pasaron de 8 | el mismo |
| Después de la revisión | `replay.evento_actual` | 4.4 | 1742247297040 |
| La fila viva, sin tocarla | `evento_actual` | 4.2 | 1742247237040 |

A 15 de noviembre, `replay.evento_actual` sigue en 8 eventos y 8 ids, y `replay.evento_version` sigue en 9 versiones. La repetición no aumentó el número de terremotos. La revisión cambió la magnitud solo en el esquema `replay`.

Decisión: reenviar la misma versión no crea otro terremoto. Una revisión posterior actualiza la fila vigente y añade una versión. Una versión más antigua no sustituye a la más reciente. Las 45 revisiones de más no son registros erróneos y no se borran.

## País ausente

Mismo conjunto de 2025 y mismo denominador, 18301.

```sql
SELECT COUNT(*) FILTER (WHERE country_id IS NULL) AS sin_pais
FROM evento_actual
WHERE occurred_at >= '2025-01-01'
  AND occurred_at < '2026-01-01'
  AND mag >= 4;
```

Resultado: 13233 sin país, 13233 / 18301 = 72,3 %. El 28 de octubre, con el polígono estricto de Natural Earth, eran 14349, el 78,4 %. Los 1116 de diferencia ya tienen país en la tabla. El apartado siguiente los cuenta y valora lo que cuesta esa corrección.

En las últimas 24 horas vivas, a las 18:09 UTC: 18 de 185, un 9,7 %. Sobre esa misma ventana, el polígono estricto dejaría 29 sin país, un 15,7 %. El margen recupera 11.

Decisión: si el punto no cae dentro del polígono ni de su margen de costa, `country_id` se queda nulo y el panel escribe «Sin país asignado». No se copia el país del texto `place` ni se asigna el país más cercano. `prueba-mar` sigue en la tabla con país nulo.

## Registros erróneos y coste de corregirlos

Aquí un registro erróneo es uno de estos dos: el consumidor no puede usarlo tal como llega, o el polígono estricto lo deja sin país aunque cae en el margen de costa. El mar abierto, más allá de esos 25 km, se cuenta aparte y se queda nulo.

Natural Earth a 1:110m generaliza la costa y la deja tierra adentro. El consumidor amplía solo el borde marítimo, 25 km hacia el agua, y recorta ese borde si chocaría con otro país o con el margen de otro. La frontera terrestre no se mueve. La comparación se hizo en el contenedor del consumidor, el 15 de noviembre de 2026, con los 177 polígonos reales y las coordenadas guardadas. Cada punto se asignó dos veces: con el polígono estricto y con el margen.

En el año 2025 y magnitud mayor o igual que 4, el polígono estricto deja 14349 sin país y el margen deja 13233. La diferencia es 1116. Esos 1116 son los registros erróneos de esta clase. 1116 / 18301 = 6,1 %. Ninguno cambia de un país a otro. Ninguno pierde un país que el polígono estricto ya le daba. 1116 + 13233 = 14349.

En toda `evento_actual` (18750 filas a las 18:09 UTC) el mismo criterio marca 1148. Los 1116 son el corte de 2025. Los otros 32 están fuera de ese corte. De esos 32, 11 siguen dentro de las últimas 24 horas. La columna `country_id` ya coincide con el margen en las 18750 filas: la corrección está escrita. Repetirla no vuelve a cambiar países; sirve para saber lo que cuesta.

`us6000phj9` es uno de los 1116: magnitud 4,5, profundidad 10 km, texto USGS «10 km SW of Alanya, Turkey». El margen lo deja en `TUR`. El texto `place` no entra en la asignación. De los 1116, 3 quedan en `ESP`. Con magnitud 4 o más, el año 2025 tiene 4 eventos en España: 3 llegan por este margen y 1 ya caía dentro del polígono.

País que reciben los 1116:

| `country_id` | Registros |
|---|---|
| RUS | 216 |
| IDN | 183 |
| PHL | 150 |
| PNG | 133 |
| JPN | 72 |
| CHL | 59 |
| SLB | 34 |
| VUT | 33 |
| TWN | 33 |
| GRC | 20 |
| PER | 20 |
| IRN | 19 |
| MEX | 15 |
| USA | 15 |
| TUR | 13 |
| VEN | 13 |
| GRL | 11 |
| SLV | 10 |
| GTM | 9 |
| NZL | 8 |
| ECU | 7 |
| ISL | 7 |
| DOM | 6 |
| CRI | 5 |
| NIC | 4 |
| ITA | 3 |
| ESP | 3 |
| TLS | 3 |
| CYP | 3 |
| COL | 2 |
| AZE | 1 |
| MDG | 1 |
| PAN | 1 |
| CAN | 1 |
| HRV | 1 |
| FJI | 1 |
| NOR | 1 |

Son 37 países. La suma de la tabla es 1116.

Coste de repetir la corrección, medido en ese contenedor. El vatio no se volvió a medir: se usa el supuesto de la memoria, 40 W de media y 0,20 €/kWh. Una hora encendido sale a 0,008 €. No hay máquina nueva, ni otra descarga a USGS, ni tabla nueva. `country_id` ya existía.

| Paso | Qué recorre | Tiempo | Electricidad |
|---|---|---|---|
| Armar el margen de los 177 países | el catálogo, una vez | 1,030 s | 0,000002 € |
| Volver a asignar los candidatos de 2025 | las 14349 filas que el polígono estricto deja sin país | 9,306 s | 0,000021 € |
| Los dos pasos, que es la corrección completa | de esas 14349, cambian 1116 y 13233 siguen nulas | 10,336 s | 0,000023 € |

La electricidad del segundo paso es 9,306 / 3600 × 0,040 kW × 0,20 €/kWh = 0,000021 €. Sumando el armado del margen, 10,336 s salen a 0,000023 €. Una pasada anterior, el mismo día, tardó 0,825 s y 9,132 s: el mismo orden. Rehacer las 18750 filas con el margen, no solo las candidatas de 2025, tardó 12,572 s, unas 0,000028 €, y también dejó 1148 diferencias frente al polígono estricto.

El margen ya se calcula al arrancar el consumidor. Los eventos nuevos pasan por él al guardarse, así que el feed de cada minuto no necesita este repaso. El tiempo de haber escrito la regla es el del proyecto de aula. No se convierte en un salario.

Registros que se cuentan y no se reescriben. Arreglarlos sustituiría el dato por otro inventado:

| Registros | Cuántos | Qué tocaría un arreglo | Decisión |
|---|---|---|---|
| Sin país más allá de los 25 km, año 2025 y magnitud ≥ 4 | 13233 | escribir el país más cercano en 13233 filas, el 72,3 % del conjunto | se quedan nulos y se etiquetan «Sin país asignado» |
| Coordenada imposible, `prueba-malo`, latitud 145 | 1 | inventar un punto y sacarlo de la cuarentena | sigue en `cuarentena`, con el original `[-3.7, 145, 5]`, y no está en `evento_actual` |
| `type` distinto de `earthquake` | 6 | meter las explosiones en el análisis | siguen en `cuarentena` |
| Magnitud nula, `prueba-mar` | 1 | guardar un cero | sigue nula |

Dentro de `evento_actual` hay 0 duplicados de `event_id` y 0 coordenadas fuera de rango. Esas dos clases, en la tabla de análisis, suman 0.

## Anomalías

La tabla `cuarentena` guarda el motivo y el mensaje original. Sigue en 7 filas.

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

Decisión: lo que no se puede tratar se conserva en cuarentena con motivo y original. El offset de Kafka se confirma después de esa inserción, para no dejar el mensaje reintentándose sin fin. Esas 7 filas no se corrigen: el coste de reescribirlas sería un punto falso o seis explosiones dentro del análisis.

## Actualidad y exactitud

`last_ingestion` es la última fila de `consulta_fuente` con resultado correcto. A las 18:09:00 UTC era la fila 211, resultado `ok`, 185 registros en el feed. No es la hora a la que el panel generó la respuesta. Si esa ingesta pasa de 5 minutos, el panel avisa de que el productor parece parado.

El país se contrasta con el polígono de Natural Earth a escala 1:110m, más el margen de costa de 25 km, no con un catastro de fronteras. `(-3.7, 40.4)` cae en `ESP`. `(-30, 25)` no cae en ningún polígono. No se afirma precisión legal.

Salir del feed de 24 horas no borra el evento. Las bajas o fusiones que USGS haga cuando el evento ya no está en esa ventana no se reconcilian.
