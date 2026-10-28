---
name: observatorio-08-angular-api
description: >-
  Conecta el mapa Angular a GET /api/eventos, muestra la última ingesta USGS y
  conserva la última capa si la API falla. Usar cuando el usuario pida el paso
  8 del observatorio sísmico, config.json en modo api o ver la base en el mapa.
disable-model-invocation: true
---

# Paso 8 — Angular consulta la API

## Contexto

El mapa ya pide `GET {apiUrl}/api/eventos` cuando `frontend/public/config.json` tiene `"mode": "api"`. `apiUrl` no termina en `/api`. El componente añade la ruta, refresca cada `refreshMs` (mínimo 30 s; el enunciado pide 60 s) después de acabar la petición anterior, corta a los 15 s y, si falla, conserva los puntos anteriores.

Lee `README.md` sección 3 y `FAQ-ALUMNADO.md` preguntas 25 y 26. No llames a USGS desde el navegador.

## Configuración de desarrollo

```json
{
  "mode": "api",
  "apiUrl": "http://127.0.0.1:8000",
  "refreshMs": 60000,
  "skipNgrokWarning": true
}
```

En local, sin ngrok, la URL es la del puerto publicado. No dejes `https://TU-DOMINIO-NGROK`. Recarga tras cambiar `config.json`. CORS del paso 7 tiene que permitir `http://localhost:4200`.

## Qué añadir al componente entregado

El estado debe distinguir tres momentos, porque una respuesta recién generada puede traer datos viejos:

- Última lectura del panel (cuándo el navegador recibió la respuesta).
- `metadata.generated`.
- `metadata.last_ingestion`. Si esa ingesta supera un umbral documentado (por ejemplo varios minutos), mostrar que el productor parece parado aunque la API responda.

Amplía el tipo `metadata` del componente: hoy no lee `last_ingestion`. Mantén el texto de las fichas en nodos DOM, no como HTML. Sustituye la capa de puntos; no acumules una capa por refresco. Magnitud nula sigue como ND. País nulo sigue como «Sin país asignado».

No añadas todavía filtros, gráficos ni tabla: son el paso 9.

## Comprobar en el navegador

Con productor, Kafka, consumidor, PostgreSQL y API en marcha:

1. Los puntos del mapa coinciden con `evento_actual` de las últimas 24 horas, no con los cuatro ficticios. Si solo ves los cuatro, `config.json` sigue en demo.
2. La ficha de un evento real muestra magnitud, profundidad, fecha, país e id servidos por la API.
3. Parar la API, o poner una URL mala, cambia el estado a error y no borra la última capa.
4. Al recuperar la API, el siguiente refresco vuelve a pintar sin recargar a mano.

## Hecho cuando

Esos cuatro comportamientos se han visto en el navegador y la última ingesta USGS es visible en el panel.

## No hagas todavía

No publiques en Netlify ni des por cerrados los gráficos.

Siguiente skill, solo si el usuario la pide: `observatorio-09-historico-analisis`.
