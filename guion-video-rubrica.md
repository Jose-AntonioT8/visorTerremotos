# Guion del vídeo de evidencias (aprobado)

Un solo recorrido, en este orden. Cubre los **cinco criterios** de la rúbrica (§13) y las **pruebas de aceptación** (§11). El panel es una sola página: no cambies de ruta, baja con el scroll. El resto son pestañas del navegador, la terminal y documentos.

Antes de grabar: `docker compose ps` con los cinco servicios en marcha (kafka, postgres, productor, consumidor, api), ngrok activo y el panel abierto en `https://visorterremotos.netlify.app`. No enseñes `.env`, contraseñas ni `node_modules`. No digas que los gráficos predicen terremotos o miden riesgo.

Documentos a tener abiertos (o listos en pestaña):

| Documento | Para qué |
|---|---|
| `informeCalidad.md` | Calidad: consultas, denominadores, decisiones (fecha 15 nov 2026) |
| `docs/memoria.md` | Diccionario, modelo, conclusiones, complejidad, costes, tabla de pruebas |
| `docs/prueba-revisiones.md` | Evidencia escrita de reenvío / reinicio del consumidor |
| `docs/prueba-reproduccion.md` | Evidencia escrita del replay (si no quieres relanzarlo en vídeo) |
| `docs/historico.md` | Cómo se descargó y regenera el histórico 2025 |
| `FUENTES-Y-LICENCIAS.md` | Tres fuentes y licencias |

## Mapa rúbrica ↔ tomas

| Criterio | Nivel mínimo aprobado (5–6) | Qué enseña este guion | Tomas |
|---|---|---|---|
| Extracción | Carga básica | Feed + histórico + catálogo; tipos/unidades; automatización Compose | 1–3 |
| Calidad | Análisis parcial | ≥4 dimensiones en `informeCalidad.md` + nulos en panel + cuarentena | 4–5, 8 |
| Modelado | Join básico | País por polígono, grano/claves, revisiones, idempotencia | 6–7, 7b |
| Análisis | 1–2 análisis | Ventanas, países, distribuciones, filtros, comparación, 3 conclusiones | 9–11 |
| Reflexión | Reflexión básica | Mediciones, coste, limitaciones, una mejora | 14–15 |

Las tomas 7b, 12 y 13 cierran las pruebas §11 que no entran solas en un criterio.

---

## 1. Los cinco servicios

Pantalla: terminal, raíz del repo.

```text
docker compose ps
```

Que se vean los cinco nombres y que postgres y kafka estén healthy. Frase: el sistema entra con un solo `docker compose up --build -d`; la API escucha en el puerto 8000 del host; Kafka y PostgreSQL no salen por el túnel.

Criterio: cierre operativo / entregable Compose.

## 2. De dónde salen los datos (extracción)

Pantalla: `FUENTES-Y-LICENCIAS.md` (tres fuentes), luego `docs/historico.md` (un mes de ejemplo), luego log del productor.

```text
docker compose logs productor --tail 30
```

Que se vea una consulta al feed (`all_day.geojson`), no un fichero inventado. Frase: el feed se consulta solo cada unos 60 segundos; el histórico 2025 (magnitud ≥4, tipo earthquake) se descargó una vez mes a mes y está en `datos/raw/` fuera de Git; el país sale de Natural Earth (`paises.geojson`), no del texto `place`. Si enseñas regeneración: el procedimiento está en `docs/historico.md` / `pipeline/historico.py`.

Criterio: **extracción** (histórico, feed, catálogo, automatización).

## 3. Un evento, con sus tipos

Pantalla: URL pública de la API, p. ej. la raíz ngrok + `/api/eventos` (o el panel → Network / JSON).

Abre el JSON. Señala un `Feature`: `coordinates` en orden longitud, latitud, profundidad en km; `mag` numérico o `null`; `time` y `updated` en milisegundos UTC; `country_id` o `null`. En `metadata`, `generated` y `last_ingestion` no son la misma cifra. Frase: la API no rellena un nulo con cero ni cambia el orden de las coordenadas.

Criterio: **extracción** (tipos, unidades y límites) y contrato de la API.  
Prueba §11: evento nuevo visible en API (luego en mapa en la toma 9).

## 4. Calidad: qué se midió y qué se decidió

Pantalla: `informeCalidad.md`, de arriba abajo. (Si prefieres el resumen compacto: apartado Calidad de `docs/memoria.md`.)

Para en al menos **cuatro** sitios (aprobado claro / notable):

1. **Completitud — magnitudes nulas.** Denominador, resultado y decisión: se guardan nulas; no entran en la media; el mapa pone ND.
2. **Unicidad — duplicados/revisiones.** `evento_actual`: filas = ids; las de más están en `evento_version`.
3. **Completitud / exactitud — país ausente.** Porcentaje con denominador; no se copia el país desde `place`; «Sin país asignado».
4. **Validez — cuarentena.** Motivo + original; coordenada inválida y tipos no earthquake fuera de `evento_actual`.

Menciona en una frase **actualidad** (última ingesta vs `generated`) y **consistencia** de revisiones (vivo vs replay), aunque sea leyendo la tabla de la memoria. Di la fecha de las consultas del documento que enseñes; no mezcles 28 oct y 15 nov en la misma frase.

Criterio: **calidad**.

## 5. El panel no disfraza los nulos

Pantalla: el panel, bloque de arriba y «Periodo consultado».

Que se lean a la vez: modo `API · datos del backend`, «Última ingesta USGS UTC», «Sin magnitud», «Sin profundidad» y «Sin país». Baja hasta la tabla y enseña una celda `ND` si hay magnitud nula, o di que en esta ventana no hay ninguna y que el caso de prueba (`prueba-mar` / replay) está documentado. En el pie, leyenda del círculo gris: sin profundidad no se pinta como cero.

Criterio: **calidad**. Prueba §11: magnitud nula.

## 6. País por polígono (modelado)

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT event_id, country_id, place FROM evento_actual WHERE event_id IN ('prueba-esp','prueba-mar');"
```

`prueba-esp` tiene país y `prueba-mar` no, aunque el texto del lugar diga otra cosa. Después, en el panel, filtro País = «Sin país asignado» y Aplicar. El mapa, la tabla y «Sin país» del periodo tienen que cuadrar. Vuelve a «Todos» antes de seguir.

Opcional 20 s: en `docs/memoria.md`, apartado Modelo, lee grano y claves: `evento_actual` (una fila por `event_id`), `evento_version` (`event_id` + `updated_ms`), `pais` por `ADM0_A3`, esquema `replay` aparte.

Criterio: **modelado** (integración geográfica, grano). Prueba §11: evento marítimo.

## 7. Una fila vigente y las revisiones

Pantalla: terminal + apartado «Duplicados y revisiones» de `informeCalidad.md` (o `docs/prueba-reproduccion.md`).

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT (SELECT count(*) FROM evento_actual) AS actuales, (SELECT count(DISTINCT event_id) FROM evento_actual) AS ids, (SELECT count(*) FROM evento_version) AS versiones;"
```

`actuales` e `ids` iguales. `versiones` mayor o igual. Señala `us6000pjr6`: repetir el mismo `updated` no sumó terremotos; la revisión posterior cambió solo `replay` (4,4); la fila viva se quedó en 4,2.

Criterio: **modelado** (revisiones, idempotencia).  
Pruebas §11: misma versión reenviada; versión posterior; versión antigua que no pisa la nueva.

## 7b. Reiniciar el consumidor (sin duplicar)

Pantalla: `docs/prueba-revisiones.md`, apartado «Reenvío antes de confirmar el offset».

Lee en voz: se guardó, se reinició el consumidor antes del offset, Kafka reentregó, el recuento siguió en `2|3`. Frase: procesamiento al menos una vez con escritura idempotente; no hace falta transacción distribuida Kafka–PostgreSQL.

Si puedes demostrarlo en vivo (opcional, ~1 min):

```text
docker compose restart consumidor
docker compose logs consumidor --tail 20
```

Y repite el `count` de la toma 7: los totales no deben dispararse solo por el reinicio.

Criterio: **modelado**. Prueba §11: reiniciar consumidor.

## 8. Coordenada imposible, sin punto dibujado

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT motivo, original->>'id' AS id FROM cuarentena WHERE original->>'id' = 'prueba-malo'; SELECT count(*) AS en_vivo FROM evento_actual WHERE event_id = 'prueba-malo';"
```

Motivo de coordenadas y `en_vivo` a cero. Frase: se conserva el original con motivo; el offset se confirma después; no se inventa un punto en el mapa.

Criterio: **calidad**. Prueba §11: coordenadas inválidas.

## 9. Mapa, ventanas, países y distribuciones

Pantalla: el panel, desde el mapa hasta el final de «Distribución de profundidad». Una toma continua, bajando despacio.

En este orden: mapa con leyenda de profundidad (y tamaño por magnitud); «Ventanas horarias UTC»; «Conteo por país» (incluida «Sin país asignado» si sale); media de magnitud con denominador y nulos fuera; lo mismo en profundidad. Si el gráfico agrupa por día, lee esa frase: la consulta sigue siendo por hora UTC. Confirma que los puntos del mapa coinciden con el total del periodo (evento nuevo en mapa + análisis).

Criterio: **análisis** (ventanas, distribuciones, conteo por país).

## 10. Los filtros mueven las tres vistas a la vez

Pantalla: el panel. Anota en voz el total de «Periodo consultado» antes de filtrar.

Pon magnitud mínima 5 y un país que tenga eventos. Aplicar. En el mismo plano tienen que cambiar el mapa, el total del periodo, las barras y las filas de la tabla. Lee la nota gris: el filtro de fechas no cambia los dos periodos de la comparación. Quita los filtros (país «Todos», magnitud vacía) y Aplicar.

Criterio: **análisis** (filtros coherentes).

## 11. Comparación equivalente y tres conclusiones

Pantalla: «Comparación histórica», sin filtro de país y con la magnitud del mapa vacía o por debajo de 4.

Lee lo que haya escrito ahí, sin inventar cifras: periodo reciente, media diaria del año histórico, días del denominador (365, **incluidos días con cero**), corte de magnitud y la variación. Si aparece el aviso de que el corte se mantiene en ≥4, léelo. Menciona que el tramo reciente puede estar incompleto por retrasos de USGS.

Di **tres conclusiones** seguidas, cada una con cifra, ámbito y periodo. Ninguna puede ser predicción ni riesgo. Forma (no copies cifras viejas): «En estas 24 horas el recuento está un X % respecto de la media diaria de 2025, mismo corte de magnitud ≥4 y días en cero en el denominador.»

Opcional: si quieres cifras ya redactadas, abre `docs/memoria.md` / `docs/conclusiones.md` y di que son del día de esa consulta, no de hoy.

Criterio: **análisis** (comparación + insights / conclusiones).

## 12. Reproducción aislada

Pantalla: el panel. Pulsa «Ver reproducción».

Tiene que verse la palabra **REPRODUCCIÓN** y que esos eventos no entran en el análisis en vivo. La comparación histórica, en esta vista, dice que no se calcula. La tabla trae fechas originales, no la hora de la grabación. Pulsa «Volver al directo» y comprueba que la comparación vuelve.

Origen (una frase): `pipeline/reproducir.py` → topic `eventos-replay` → esquema `replay`, mismo consumidor. Evidencia escrita: `docs/prueba-reproduccion.md`.

Criterio: prueba §11 **reproducción histórica**.

## 13. Túnel cerrado y túnel otra vez

Pantalla: el panel, con «Última lectura UTC» visible. Para ngrok en la terminal, sin cerrar el navegador.

Espera a que el estado deje de decir que la consulta se completó. Aviso de fallo; la hora de última lectura no salta a «ahora» como si hubiera datos nuevos; los puntos que ya estaban siguen.

Vuelve a arrancar ngrok. Si el dominio es el mismo que en `frontend/public/config.json` / proxy Netlify, en menos de un minuto el estado vuelve a accesible. Si ngrok da otro dominio, di en voz que hay que actualizar la URL, `npm run build` y republicar Netlify (`docs/despliegue.md`); no lo presentes como fallo del panel.

Criterio: pruebas §11 del túnel. Reflexión breve: sin equipo/túnel, Netlify sigue sirviendo la UI pero no hay datos nuevos.

## 14. Medición, coste, limitaciones y una mejora

Pantalla: terminal. Datos sintéticos; no entran en el mapa.

```text
docker compose run --rm --no-deps --entrypoint python -v "${PWD}/pipeline:/work" -e PYTHONPATH=/work consumidor /work/mediciones.py
```

En Windows PowerShell, si `${PWD}` falla, usa la ruta absoluta a `pipeline`.

Enseña las tres tallas: búsqueda lista vs diccionario; punto en polígono; agregación/búsqueda con y sin índice. Di que son tiempos de esta máquina. Cierra con:

1. **Coste:** electricidad / equipo / tiempo de desarrollo; una cuota cloud gratuita no es coste total cero (supuestos en `docs/memoria.md`).
2. **Limitación:** el feed de 24 h no reconcilia bajas fuera de ventana; el mapa 1:110m no es frontera legal (`docs/limitaciones.md` o memoria).
3. **Mejora:** p. ej. calcular el país solo en la ingesta (ya hecho) o índice espacial si creciera el volumen.

Criterio: **reflexión** (complejidad, memoria, costes, limitaciones, mejoras).

## 15. Cierre: un evento de punta a punta

Pantalla: el panel en directo, sin reproducción y sin filtros. Opcional: diccionario en `docs/memoria.md` (10 s).

Recorre en voz un `event_id` de la tabla: USGS → productor → Kafka → consumidor (validación + país) → `evento_actual` → API → círculo del mapa.  
Una decisión técnica tuya, una sola: por ejemplo que el país sale del polígono y el mar queda sin país, o que la comparación no baja de magnitud 4.

Entregable §12: explicación individual del flujo y de una decisión propia.

---

## Orden y duración orientativa (~18–20 min)

| Toma | Min | Rúbrica / prueba |
|---|---|---|
| 1–3 | 3 | Extracción + Compose + tipos |
| 4–5 | 3 | Calidad (doc + panel) |
| 6–7–7b–8 | 4 | Modelado, mar, revisiones, reinicio, cuarentena |
| 9–11 | 4 | Análisis, filtros, comparación, 3 conclusiones |
| 12–13 | 2 | Reproducción + túnel |
| 14–15 | 3 | Reflexión + flujo completo |

## Checklist rápido antes de cortar

- [ ] Cinco servicios healthy  
- [ ] Tres fuentes dichas en voz  
- [ ] Tipos/unidades en un Feature  
- [ ] ≥4 dimensiones de calidad con denominador y decisión  
- [ ] País por polígono + «Sin país asignado»  
- [ ] Revisiones / idempotencia / reinicio consumidor  
- [ ] Cuarentena `prueba-malo`  
- [ ] Ventanas + distribuciones + países  
- [ ] Filtros coherentes mapa/gráficos/tabla  
- [ ] Comparación equivalente + 3 conclusiones sin predicción  
- [ ] REPRODUCCIÓN aislada  
- [ ] Túnel caído y recuperado  
- [ ] Medición + coste + limitación + mejora  
- [ ] Un evento de punta a punta + una decisión propia  

No hace falta Spark, ni un segundo mapa, ni un panel de calidad en Angular. Esas ausencias no se justifican en el vídeo.
