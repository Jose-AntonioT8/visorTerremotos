# Cómo lanzar la aplicación

Desde la raíz del proyecto. Hacen falta Docker (con Compose) y ngrok instalado y autenticado en tu cuenta.

## 1. Backend

```bash
docker compose up --build -d
```

Levanta Kafka, PostgreSQL, el productor, el consumidor y la API. La API queda en `http://127.0.0.1:8000`.

## 2. Túnel público

En otra terminal:

```bash
ngrok http 8000
```

La web no llama a ngrok desde el navegador. `frontend/public/config.json` apunta a `https://visorterremotos.netlify.app` y Netlify reenvía `/api/*` al túnel. La URL del túnel está en `frontend/netlify/edge-functions/proxy-api.js`.

## 3. Ver los terremotos en Netlify

Docker y ngrok tienen que seguir en marcha. Publica el frontend para que Netlify coja `config.json` y la función de reenvío. Si ngrok cambia de dominio, actualiza `TUNEL` en esa función y vuelve a publicar.
