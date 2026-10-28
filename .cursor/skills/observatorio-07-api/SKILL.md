---
name: observatorio-07-api
description: >-
  Implementa la API FastAPI de consulta sobre PostgreSQL, con /api/eventos,
  /api/salud, CORS y el quinto servicio Docker. Usar cuando el usuario pida el
  paso 7 del observatorio sísmico, el contrato de la API o FastAPI.
disable-model-invocation: true
---

# Paso 7 — API de consulta

## Contexto

La API es el quinto servicio del mismo Compose. Lee datos ya escritos por el consumidor; no llama a USGS ni a Kafka para responder. Uvicorn escucha en `0.0.0.0:8000` dentro del contenedor. Publica el puerto en el host como `127.0.0.1:8000:8000` si ngrok correrá en el equipo. No expongas administración, secretos, PostgreSQL ni Kafka.

Lee `CONTRATO-API.md` entero y `ENUNCIADO.md` sección 9.

## GET /api/eventos

HTTP 200, `Content-Type: application/json`, GeoJSON `FeatureCollection`. Sin filas: `features: []`, no un error. Una fila actual por `event_id`. Por defecto, ocurridos en las últimas 24 horas UTC según `time`, no según la ingesta.

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "generated": 0,
    "last_ingestion": 0,
    "mode": "live",
    "count": 0,
    "truncated": false
  },
  "features": []
}
```

- `generated`: creación de esta respuesta, milisegundos Unix UTC.
- `last_ingestion`: última consulta correcta a USGS, no la hora de esta respuesta.
- Coordenadas `[longitud, latitud, profundidad_km]`.
- `null` para magnitud, profundidad o país desconocidos. Nunca `NaN` ni `Infinity`.
- Este endpoint solo incluye geometría válida. Lo que está en cuarentena no se dibuja.
- Propiedades mínimas: `mag`, `magType`, `place`, `time`, `updated`, `country_id`, `country_name`.

Filtros: `start` ISO8601 inclusive, `end` ISO8601 exclusive, `min_mag`, `country_id`. Una magnitud nula no cumple `min_mag`. Si aplicas un máximo de puntos, documéntalo, pon `truncated: true`, devuelve el total y un modo de paginación. No presentes un recorte como si fuera el censo completo.

Si PostgreSQL falla, error HTTP explícito. No devuelvas cero eventos como si la consulta hubiera tenido éxito.

## GET /api/salud

Estado de la API y fecha de última ingesta. Sin credenciales ni cadena de conexión.

`GET /api/estadisticas` puede responder 501 o un esqueleto con periodo y filtros vacíos hasta el paso 9. No inventes la media histórica.

## CORS

Orígenes exactos: `http://localhost:4200` y, cuando exista, el de Netlify. Métodos GET y OPTIONS. Cabecera permitida: `ngrok-skip-browser-warning`. `CORSMiddleware` basta para el preflight. CORS no es autenticación. No uses cookies.

## Hecho cuando

Con datos de prueba en `evento_actual`, `curl` a `http://127.0.0.1:8000/api/eventos` devuelve un `FeatureCollection` válido leído de PostgreSQL, `/api/salud` no filtra secretos, y un `OPTIONS` desde `http://localhost:4200` responde con los orígenes permitidos. Los cinco servicios quedan definidos en `compose.yaml`.

## No hagas todavía

No cambies el frontend a modo `api` salvo una prueba local que reviertas si el usuario aún no pide el paso 8. No calcules la comparación de 2025.

Siguiente skill, solo si el usuario la pide: `observatorio-08-angular-api`.
