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

Copia la URL HTTPS completa que muestra ngrok (acaba en `.dev`) y úsala como `apiUrl` en `frontend/public/config.json`, sin barra final: el frontend añade `/api/eventos`.

## 3. Ver los terremotos en Netlify

https://visorterremotos.netlify.app no lee el archivo de tu PC. El navegador usa el `config.json` del último despliegue.

Si el dominio de ngrok no ha cambiado, no hace falta volver a publicar. Con Docker y ngrok en marcha, recarga la web: pide `https://TU-DOMINIO-NGROK/api/eventos` y ngrok lo reenvía a la API local.

Si ngrok te asigna otro dominio, guarda la URL nueva en `frontend/public/config.json`, súbela al repositorio y espera a que Netlify termine el build. Luego recarga la página.
