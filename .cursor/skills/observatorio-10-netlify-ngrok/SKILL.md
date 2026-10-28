---
name: observatorio-10-netlify-ngrok
description: >-
  Publica el panel Angular en Netlify y expone la API local por HTTPS con
  ngrok, CORS y recuperación si el túnel se cierra. Usar cuando el usuario
  pida el paso 10 del observatorio sísmico, el despliegue, Netlify o el túnel.
disable-model-invocation: true
---

# Paso 10 — Netlify y ngrok

## Contexto

El navegador descarga Angular desde Netlify y llama a la API por la URL HTTPS de ngrok. Kafka y PostgreSQL no se publican. No instales un certificado en FastAPI: ngrok termina HTTPS. El tramo navegador–ngrok es HTTPS; el tramo agente–API puede ser HTTP. Angular en producción usa siempre la URL pública HTTPS.

Lee `ENUNCIADO.md` sección 9, `README.md` secciones 3 y 4, y `FAQ-ALUMNADO.md` preguntas 29–31.

El authtoken de ngrok no entra en Git, en la imagen ni en `config.json`. No lo pegues en el chat si puedes usar una variable de entorno ya configurada en la máquina.

## Túnel

Elige una opción y documéntala en `docs/despliegue.md`:

| Opción | Cómo |
|---|---|
| A. ngrok en el equipo | Puerto `127.0.0.1:8000:8000` y `ngrok http 8000` |
| B. ngrok como contenedor de la misma red | `ngrok http http://api:8000`. No hace falta publicar el puerto para el túnel. Dentro de ese contenedor `localhost:8000` no es la API |

La API sigue en `0.0.0.0:8000`. Durante la defensa el equipo, los contenedores y el túnel tienen que estar encendidos. Si se apagan, Netlify sigue sirviendo la interfaz sin datos nuevos: el panel debe decirlo.

## Frontend público

Antes de compilar, `frontend/public/config.json`:

```json
{
  "mode": "api",
  "apiUrl": "https://DOMINIO-REAL-ASIGNADO",
  "refreshMs": 60000,
  "skipNgrokWarning": true
}
```

Sin `/api` al final y sin el marcador `TU-DOMINIO-NGROK`. El dominio gratuito cambia al reiniciar ngrok: entonces hay que volver a publicar `config.json` o el procedimiento que uses.

CORS debe incluir el origen exacto de Netlify (esquema, host y puerto si no es el predeterminado) y `http://localhost:4200`. Cabecera `ngrok-skip-browser-warning` permitida. Si el navegador recibe HTML, suele ser la página de aviso de ngrok o un error, no un fallo de Leaflet. No uses `mode: "no-cors"`.

Netlify, si el repositorio contiene todo el paquete: base `frontend`, comando `npm run build`, carpeta `dist/observatorio/browser`. `frontend/netlify.toml` y `frontend/public/_redirects` ya lo indican. No subas `node_modules` ni `.env`.

## Comprobación

1. Desde otro dispositivo, o una ventana privada fuera de localhost, el panel HTTPS carga puntos de la API.
2. Cierras ngrok: el panel muestra el fallo y no presenta la capa vieja como lectura nueva.
3. Vuelves a abrir el túnel con la misma URL: el refresco siguiente recupera los datos sin recargar a mano. Si el plan gratuito asigna otro dominio, la recuperación automática no es posible hasta publicar otra vez `config.json`; explícalo en `docs/despliegue.md`. Para la defensa, usa un dominio que no cambie al reiniciar el túnel. La prueba de aceptación se cumple con la URL estable. Un dominio nuevo no suspende el paso si ese caso está escrito y la URL estable sí se recuperó.
4. `GET /api/salud` accesible por el túnel no revela credenciales. El puerto de Kafka no responde en esa URL.

## Hecho cuando

`docs/despliegue.md` tiene la URL del panel, la opción de ngrok y el procedimiento de la defensa. Las comprobaciones 1 y 2 se han visto. La 3 queda hecha o con el cambio de dominio explicado.

## No hagas todavía

No des la práctica por entregada: faltan reproducción, mediciones y memoria.

Siguiente skill, solo si el usuario la pide: `observatorio-11-reproduccion-informe`.
