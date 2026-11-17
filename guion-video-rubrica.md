# Guion del vídeo de evidencias (rúbrica)

Un solo recorrido, en este orden. Cubre los **cinco criterios** de la rúbrica (§13) y las **pruebas de aceptación** (§11). El panel es una sola página: no cambies de ruta, baja con el scroll. El resto son pestañas del navegador, la terminal y documentos.

Antes de grabar: `docker compose ps` con los cinco servicios en marcha (kafka, postgres, productor, consumidor, api), ngrok activo y el panel abierto en `https://visorterremotos.netlify.app`. No enseñes `.env`, contraseñas ni `node_modules`. No digas que los gráficos predicen terremotos o miden riesgo.

Documentos a tener abiertos (o listos en pestaña):

| Documento | Para qué |
|---|---|
| `informeCalidad.md` | Calidad: consultas, denominadores, decisiones |
| `docs/memoria.md` | Diccionario, modelo, conclusiones, complejidad, costes, tabla de pruebas |
| `docs/prueba-revisiones.md` | Evidencia escrita de reenvío / reinicio del consumidor |
| `docs/prueba-reproduccion.md` | Evidencia escrita del replay (si no quieres relanzarlo en vídeo) |
| `docs/historico.md` | Cómo se descargó y regenera el histórico 2025 |
| `FUENTES-Y-LICENCIAS.md` | Fuentes y licencias |

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

## 1. Los cinco servicios (§2, §9)

Pantalla: terminal, raíz del repo.

```text
docker compose ps
```

Que se vean los cinco nombres (productor, kafka, consumidor, postgres, api) y que postgres y kafka estén healthy. Frase: el sistema entra con un solo `docker compose up --build -d`; la API escucha en el puerto 8000 del host; Kafka y PostgreSQL no salen por el túnel. El navegador descarga el panel desde Netlify y consulta la API mediante ngrok.

Criterio: arquitectura / despliegue.

## 2. De dónde salen los datos (extracción §4–§5)

Pantalla: `FUENTES-Y-LICENCIAS.md`, luego `docs/historico.md` (un mes de ejemplo), luego log del productor.

```text
docker compose logs productor --tail 30
```

Que se vea una consulta al feed (`all_day.geojson`), no un fichero inventado. Frase: el feed USGS se consulta solo cada unos 60 segundos; el histórico 2025 (magnitud ≥4, tipo earthquake) se descargó una vez mes a mes y está en `datos/raw/` fuera de Git; el país sale de Natural Earth (`paises.geojson`), no del texto `place`. El panel consulta la API propia, no USGS directamente. Si enseñas regeneración: el procedimiento está en `docs/historico.md` / `pipeline/historico.py`.

Criterio: **extracción** (histórico, feed, catálogo, automatización).

## 3. Un evento, con sus tipos (§4.1)

Pantalla: URL pública de la API, p. ej. la raíz ngrok + `/api/eventos` (o el panel → Network / JSON).

Abre el JSON. Señala un `Feature`: `coordinates` en orden longitud, latitud, profundidad en km; `mag` numérico o `null`; `time` y `updated` en milisegundos UTC; `country_id` o `null`. En `metadata`, `generated` y `last_ingestion` no son la misma cifra. Frase: la API no rellena un nulo con cero ni cambia el orden de las coordenadas. Filtrado `type == earthquake` en la ingesta.

Criterio: **extracción** (tipos, unidades y límites) y contrato de la API.  
Prueba §11: evento nuevo visible en API (luego en mapa en la toma 9).

## 4. Calidad: qué se midió y qué se decidió (§6)

Pantalla: `informeCalidad.md`, de arriba abajo. (Si prefieres el resumen compacto: apartado Calidad de `docs/memoria.md`.)

Arranca diciendo la fecha del documento, por ejemplo:  
«Estas consultas son del 15 de noviembre de 2026, a las 18:09 UTC, sobre la base observatorio.»

Luego para en **cuatro** sitios (con eso ya cubres aprobado claro / notable). Habla así, señalando cada apartado:

1. **Magnitudes nulas (completitud)** — apartado «Magnitudes nulas»  
   «Aquí el denominador son 18301 eventos de 2025 con magnitud pedida 4 o más. En ese corte no hay magnitudes nulas, porque USGS ya filtraba por 4. La decisión importa igual: si llega un nulo, lo guardamos nulo, no lo convertimos en cero. Esos nulos no entran en la media, y en el mapa se ven como ND. En la base hay un caso de prueba, prueba-mar, con magnitud nula a propósito.»

2. **Duplicados y revisiones (unicidad)** — apartado «Duplicados y revisiones»  
   «En evento_actual hay tantas filas como identificadores distintos: una fila vigente por terremoto. Las revisiones no se cuentan como terremotos nuevos: van a evento_version. En el informe, esas filas de más son revisiones de unos pocos eventos, no duplicados erróneos. Reenviar la misma versión no crea otro terremoto.»

3. **País ausente (completitud / exactitud)** — apartado «País ausente»  
   «Con el mismo denominador de 18301, una parte no tiene país: el porcentaje sale dividiendo sin_pais entre ese total. Si el punto no cae en el polígono ni en el margen de costa, country_id se queda nulo y el panel pone “Sin país asignado”. No inventamos el país leyendo el texto place ni asignando el más cercano.»

4. **Cuarentena (validez)** — apartado «Anomalías»  
   «Lo que no se puede usar no entra en evento_actual: va a la tabla cuarentena, con el motivo y el mensaje original. Ahí está, por ejemplo, una coordenada imposible —latitud 145— y varios mensajes que no son type earthquake. Así no pintamos un punto falso ni metemos explosiones en el análisis.»

Cierra con **una frase** de actualidad y **una** de consistencia (puedes leerlas de la tabla de Calidad en `docs/memoria.md` si te resulta más fácil):

- Actualidad: «La última ingesta correcta, last_ingestion, no es la misma cifra que generated del panel: una es cuándo pedimos a USGS, la otra cuándo se generó la respuesta.»
- Consistencia: «En vivo y en replay el mismo evento puede quedar en magnitudes distintas: los esquemas no se pisan; la revisión controlada solo cambió el replay.»

Criterio: **calidad**.

## 5. El panel no disfraza los nulos (§8)

Pantalla: el panel, bloque de arriba y «Periodo consultado».

Que se lean a la vez: modo API, «Última ingesta USGS UTC», «Sin magnitud», «Sin profundidad» y «Sin país». Baja hasta la tabla y enseña una celda `ND` si hay magnitud nula, o di que en esta ventana no hay ninguna y que el caso de prueba está documentado. En la leyenda: sin profundidad no se pinta como cero.

Criterio: **calidad**. Prueba §11: magnitud nula.

## 6. País por polígono (modelado §7)

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT event_id, country_id, place FROM evento_actual WHERE event_id IN ('prueba-esp','prueba-mar');"
```

`prueba-esp` tiene país y `prueba-mar` no, aunque el texto del lugar diga otra cosa. Después, en el panel, filtro País = «Sin país asignado» y Aplicar. El mapa, la tabla y «Sin país» del periodo tienen que cuadrar. Vuelve a «Todos» antes de seguir.

Opcional 20 s: en `docs/memoria.md`, apartado Modelo, lee grano y claves: `evento_actual` (una fila por `event_id`), `evento_version` (`event_id` + `updated_ms`), `pais` por `ADM0_A3`, esquema `replay` aparte.

Criterio: **modelado** (integración geográfica, grano). Prueba §11: evento marítimo.

## 7. Una fila vigente y las revisiones (§7, §11)

Pantalla: terminal + apartado «Duplicados y revisiones» de `informeCalidad.md` (o `docs/prueba-reproduccion.md`).

**Para qué es el comando:** entrar a PostgreSQL del Compose y sacar **tres números de un golpe**: cuántas filas hay en `evento_actual` (`actuales`), cuántos `event_id` distintos hay ahí (`ids`), y cuántas filas hay en `evento_version` (`versiones`). Sirve para demostrar en vivo que el modelo no duplica terremotos: una fila vigente por evento; el historial de cambios va aparte.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT (SELECT count(*) FROM evento_actual) AS actuales, (SELECT count(DISTINCT event_id) FROM evento_actual) AS ids, (SELECT count(*) FROM evento_version) AS versiones;"
```

Qué mirar en el resultado: `actuales` e `ids` **iguales** (no hay dos filas vigentes del mismo terremoto). `versiones` **mayor o igual** (si es mayor, la diferencia son revisiones, no eventos nuevos).

Qué decir, por ejemplo:  
«Cuento las filas vigentes y los identificadores distintos: salen iguales, así que hay una sola fila actual por evento. En versiones hay más filas: esas de más son revisiones. En el informe (o en la prueba de reproducción) se ve que reenviar el mismo updated no suma terremotos; una revisión posterior actualiza la fila vigente; una versión antigua no pisa a la más reciente.»

Criterio: **modelado** (revisiones, idempotencia).  
Pruebas §11: misma versión reenviada; versión posterior; versión antigua que no pisa la nueva.

## 7b. Reiniciar el consumidor (sin duplicar) (§11)

Pantalla: `docs/prueba-revisiones.md`, apartado «Reenvío antes de confirmar el offset».

Lee en voz: se guardó, se reinició el consumidor antes del offset, Kafka reentregó, el recuento no se disparó. Frase: procesamiento al menos una vez con escritura idempotente; no hace falta transacción distribuida Kafka–PostgreSQL.

Si puedes demostrarlo en vivo (opcional, ~1 min):

```text
docker compose restart consumidor
docker compose logs consumidor --tail 20
```

Y repite el `count` de la toma 7: los totales no deben dispararse solo por el reinicio.

Criterio: **modelado**. Prueba §11: reiniciar consumidor.

## 8. Coordenada imposible, sin punto dibujado (§6, §11)

Pantalla: terminal.

```text
docker compose exec postgres psql -U observatorio -d observatorio -c "SELECT motivo, original->>'id' AS id FROM cuarentena WHERE original->>'id' = 'prueba-malo'; SELECT count(*) AS en_vivo FROM evento_actual WHERE event_id = 'prueba-malo';"
```

Motivo de coordenadas y `en_vivo` a cero. Frase: se conserva el original con motivo; el offset se confirma después; no se inventa un punto en el mapa.

Criterio: **calidad**. Prueba §11: coordenadas inválidas.

## 9. Mapa, ventanas, países y distribuciones (§8)

Pantalla: el panel, desde el mapa hasta el final de «Distribución de profundidad». Una toma continua, bajando despacio.

En este orden: mapa interactivo con fondo, fronteras, círculos (tamaño por magnitud, color por profundidad), leyenda y ficha del terremoto; «Ventanas horarias UTC»; «Conteo por país» (incluida «Sin país asignado» si sale); media de magnitud con denominador y nulos fuera; lo mismo en profundidad. Si el gráfico agrupa por día, lee esa frase: la consulta sigue siendo por hora UTC. Confirma que los puntos del mapa coinciden con el total del periodo.

Criterio: **análisis** (ventanas, distribuciones, conteo por país). Prueba §11: evento nuevo visible en mapa y análisis.

## 10. Los filtros mueven las tres vistas a la vez (§8)

Pantalla: el panel. Anota en voz el total de «Periodo consultado» antes de filtrar.

Pon magnitud mínima 5 y un país que tenga eventos. Aplicar. En el mismo plano tienen que cambiar el mapa, el total del periodo, las barras y las filas de la tabla. Lee la nota: el filtro de fechas no cambia los dos periodos de la comparación. Quita los filtros (país «Todos», magnitud vacía) y Aplicar.

Criterio: **análisis** (filtros coherentes: fecha, magnitud, país/región).

## 11. Comparación equivalente y tres conclusiones (§8)

Pantalla: «Comparación histórica», sin filtro de país y con la magnitud del mapa vacía o por debajo de 4.

Lee lo que haya escrito ahí, sin inventar cifras: periodo reciente (p. ej. últimas 24 h, magnitud ≥4), media diaria del año histórico 2025, días del denominador (**incluidos días con cero**), mismos filtros geográficos y de tipo, y la variación. Si aparece el aviso de que el corte se mantiene en ≥4, léelo. Menciona que el tramo reciente puede estar incompleto por retrasos de USGS.

Di **tres conclusiones** seguidas, cada una con cifra, ámbito y periodo. Ninguna puede ser predicción ni riesgo.

Criterio: **análisis** (comparación + conclusiones).

## 12. Reproducción aislada (§11)

Pantalla: el panel. Pulsa «Ver reproducción».

Tiene que verse la palabra **REPRODUCCIÓN** y que esos eventos no entran en el análisis en vivo. La comparación histórica, en esta vista, dice que no se calcula. La tabla trae fechas originales, no la hora de la grabación. Pulsa «Volver al directo» y comprueba que la comparación vuelve.

Origen (una frase): reproducción por Kafka con topic/esquema separados o equivalente. Evidencia escrita: `docs/prueba-reproduccion.md`.

Criterio: prueba §11 **reproducción histórica**.

## 13. Túnel cerrado y túnel otra vez (§9, §11)

Pantalla: el panel, con «Última lectura UTC» visible. Para ngrok en la terminal, sin cerrar el navegador.

Espera a que el estado deje de decir que la consulta se completó. El panel **muestra el fallo** y **conserva/identifica la última lectura**; los puntos que ya estaban siguen; la hora de última lectura no se presenta como datos nuevos.

Vuelve a arrancar ngrok. Si el dominio es el mismo, en menos de un minuto el estado vuelve a accesible. Si ngrok da otro dominio, di en voz que hay que actualizar la URL del túnel / proxy, `npm run build` y republicar Netlify; no lo presentes como fallo del panel.

Frase: al apagar contenedores o túnel, Netlify sigue sirviendo la interfaz pero no hay datos nuevos; se evalúa el tratamiento del error, no disponibilidad 24/7.

Criterio: pruebas §11 del túnel. Reflexión breve de §9.

## 14. Medición, coste, limitaciones y una mejora (§10)

Pantalla: terminal. Datos sintéticos; no entran en el mapa.

```text
docker compose run --rm --no-deps --entrypoint python -v "${PWD}/pipeline:/work" -e PYTHONPATH=/work consumidor /work/mediciones.py
```

En Windows PowerShell, si `${PWD}` falla, usa la ruta absoluta a `pipeline`.

Enseña las tres tallas y al menos tres operaciones justificadas (p. ej. búsqueda de versiones por id, integración geográfica, agregación por ventanas): búsqueda lista vs diccionario; punto en polígono; agregación/búsqueda con y sin índice. Di que son tiempos de esta máquina. Cierra con:

1. **Coste:** electricidad / equipo / tiempo de desarrollo; una cuota cloud gratuita no es coste total cero (supuestos en `docs/memoria.md`).
2. **Limitación:** el feed de 24 h no reconcilia bajas fuera de ventana; el mapa de Natural Earth no es frontera legal.
3. **Mejora:** p. ej. índice espacial si creciera el volumen, o lo que hayas documentado.

Criterio: **reflexión** (complejidad, memoria, costes, limitaciones, mejoras).

## 15. Cierre: un evento de punta a punta (§12)

Pantalla: el panel en directo, sin reproducción y sin filtros. Opcional: diccionario en `docs/memoria.md` (10 s).

Recorre en voz un `event_id` de la tabla: USGS → productor → Kafka → consumidor (validación + país) → `evento_actual` → API → mapa.  
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

- [ ] Cinco servicios healthy; Kafka/Postgres no por el túnel  
- [ ] Feed USGS + histórico + catálogo Natural Earth  
- [ ] Tipos/unidades en un Feature  
- [ ] ≥4 dimensiones de calidad con denominador y decisión  
- [ ] País por polígono + «Sin país asignado»  
- [ ] Revisiones / idempotencia / reinicio consumidor  
- [ ] Cuarentena `prueba-malo`  
- [ ] Mapa + ventanas + distribuciones + países  
- [ ] Filtros coherentes mapa/gráficos/tabla  
- [ ] Comparación equivalente + 3 conclusiones sin predicción  
- [ ] REPRODUCCIÓN aislada  
- [ ] Túnel caído (fallo + última lectura) y recuperado  
- [ ] Medición + coste + limitación + mejora  
- [ ] Un evento de punta a punta + una decisión propia  

No hace falta Spark, Flink, Kubernetes ni un panel de calidad en Angular. Esas ausencias no se justifican en el vídeo.
