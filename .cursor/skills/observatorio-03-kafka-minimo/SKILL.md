---
name: observatorio-03-kafka-minimo
description: >-
  Crea Docker Compose con Kafka, productor Python y consumidor Python, y
  comprueba que un mensaje de prueba llega al log del consumidor. Usar cuando
  el usuario pida el paso 3 del observatorio sísmico, el broker, aiokafka,
  compose.yaml o un productor y consumidor mínimos.
disable-model-invocation: true
---

# Paso 3 — Kafka, productor y consumidor mínimos

## Contexto

Cinco servicios serán obligatorios al final: productor, Kafka, consumidor, PostgreSQL y API. En este paso solo entran los tres primeros. Un único `compose.yaml` en la raíz; los pasos posteriores lo amplían, no crean otro. Imagen Python reproducible y compartible, con comandos de arranque distintos. Versiones fijadas en `requirements.txt`.

Dentro de un contenedor, `localhost` es ese contenedor. Usa el nombre del servicio (`kafka:9092` o el listener interno que configures).

Lee `ENUNCIADO.md` secciones 2 y 5, `README.md` sección 3 y `FAQ-ALUMNADO.md` preguntas 4, 11 y 28.

## Qué construir

- `compose.yaml` con salud y reintentos. `depends_on` con `service_healthy` no basta solo: productor y consumidor reintentan la conexión a Kafka.
- Kafka en KRaft, un broker, volumen y retención limitada (tiempo o tamaño, documentado). No publiques el broker por ngrok.
- Si también accedes desde el host, documenta listeners y `advertised.listeners`. El listener interno de los contenedores no puede anunciarse como `localhost`.
- Productor y consumidor Python 3.12 + aiokafka, variables de entorno para dirección Kafka, topic y frecuencia. Plantilla `.env.example` sin secretos. `.env` fuera de Git.
- Topic de eventos en vivo. Clave Kafka = identificador del evento. El mensaje de prueba incluye `source`, `ingested_at`, `mode` (`live` o `replay`) y el evento.
- Un evento ficticio basta. Publícalo, espera el acuse de Kafka y muestra el JSON en el log del consumidor.

No marques todavía versiones como publicadas en base de datos: PostgreSQL es el paso 4. No des por bueno un productor que republica USGS cada minuto.

## Comprobación

```bash
docker compose up --build -d
```

Revisa salud de Kafka y el log del consumidor hasta ver el mensaje de prueba. Reinicia el consumidor y comprueba que no se pierde el mensaje aún no confirmado, dentro de la retención.

## Hecho cuando

El mensaje de prueba sale en el log del consumidor tras `docker compose up --build -d`, usando nombres de servicio y sin secretos en Git.

## No hagas todavía

No añadas PostgreSQL, FastAPI, ngrok ni el feed real con deduplicación.

Siguiente skill, solo si el usuario la pide: `observatorio-04-postgres`.
