---
name: observatorio-02-explorar-usgs
description: >-
  Descarga una respuesta real de USGS, explica un evento y documenta campos,
  tipos, unidades, opcionales, frecuencia y errores del feed all_day. Usar
  cuando el usuario pida el paso 2 del observatorio sísmico, explorar el
  GeoJSON de terremotos o entender el feed de USGS.
disable-model-invocation: true
---

# Paso 2 — Explorar USGS

## Contexto

Aún no hay pipeline. Este paso produce una nota corta de la fuente, en `docs/fuente-usgs.md`, para reutilizarla en la memoria. No inventes valores: usa la respuesta descargada.

Lee `ENUNCIADO.md` sección 4 y `FAQ-ALUMNADO.md` preguntas 8 y 9. Los ejemplos de la FAQ son ficticios; no los copies como si fueran la respuesta real.

## Descarga

```text
GET https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
```

Es una ventana móvil de unas 24 horas, actualizada cada minuto. No es el día natural anterior ni un push. Cada respuesta repite toda la ventana.

Guarda el archivo fuera de Git, en una ruta documentada (por ejemplo `datos/raw/`, ignorada). No subas el GeoJSON completo al repositorio.

## Qué explicar con un evento real

Elige un feature con `properties.type == "earthquake"` y anota:

| Campo | Qué comprobar |
|---|---|
| `id` | Identificador estable entre revisiones |
| `properties.time` | Ocurrencia, milisegundos Unix UTC |
| `properties.updated` | Revisión USGS, milisegundos Unix UTC; no es `time` ni la hora de descarga |
| `properties.mag` | Puede ser null; no lo conviertas a 0 |
| `properties.magType` | Escala; no todas son comparables |
| `properties.type` | Filtrar `earthquake`; explosiones y otros tipos se excluyen y se conserva el motivo |
| `properties.place` | Texto descriptivo; no es el país |
| `geometry.coordinates` | Longitud, latitud, profundidad en km |

Cuenta features totales y cuántos tienen `type == "earthquake"`. Señala campos ausentes u opcionales que aparezcan en la respuesta. Anota código HTTP, tamaño aproximado y hora UTC de la descarga.

Si la descarga falla (timeout, 429, 5xx, JSON inválido), documenta el fallo. No fabriques un evento real.

## Hecho cuando

`docs/fuente-usgs.md` cita la URL, la hora de descarga, un evento real con los campos de la tabla, las unidades y la diferencia entre la ventana móvil y un día natural. El archivo grande no está en Git.

## No hagas todavía

No publiques en Kafka ni diseñes tablas. No llames a USGS desde Angular.

Siguiente skill, solo si el usuario la pide: `observatorio-03-kafka-minimo`.
