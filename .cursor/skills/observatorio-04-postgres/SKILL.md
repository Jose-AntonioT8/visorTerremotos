---
name: observatorio-04-postgres
description: >-
  Añade PostgreSQL al Compose, crea el modelo físico e inserta un evento desde
  el consumidor de forma transaccional. Usar cuando el usuario pida el paso 4
  del observatorio sísmico, el esquema, las tablas o la escritura en la base.
disable-model-invocation: true
---

# Paso 4 — PostgreSQL y primera escritura

## Contexto

Amplía el mismo `compose.yaml`. PostgreSQL es el cuarto servicio. No lo publiques por ngrok. Credenciales por entorno; `.env.example` solo con marcadores. Volumen con nombre para que los datos sobrevivan a `docker compose down` sin `-v`.

Lee `ENUNCIADO.md` sección 7 y `FAQ-ALUMNADO.md` preguntas 13, 20 y 21.

## Modelo por defecto

Puedes apartarte de estas tablas si justificas grano, claves y relaciones. No dejes el modelo solo en un diagrama: tiene que existir SQL de inicialización.

| Tabla | Una fila es | Restricción |
|---|---|---|
| `pais` | Una entidad Natural Earth | `country_id` (`ADM0_A3`) único |
| `fecha` | Un día UTC | `fecha_id` único |
| `evento_actual` | Versión vigente de un terremoto | `event_id` único |
| `evento_version` | Una versión observada | único `(event_id, updated)` |
| `cuarentena` | Un rechazo con motivo y original | conservar el payload |
| `publicacion` | Última versión que el productor ya confirmó en Kafka | `event_id` único |
| `consulta_fuente` | Una descarga o replay: cuándo, URL o intervalo, registros, resultado | no guardar indefinidamente copias idénticas del feed |

`evento_actual` guarda magnitud, tipo de magnitud, lugar, profundidad, longitud, latitud, tiempos de ocurrencia y de revisión, país nulo si no hay asignación, y la clave `fecha_id` del día UTC en que ocurrió. Conserva el timestamp completo: las ventanas de una hora se calculan con esa hora, no solo con el día. Conserva milisegundos originales y columnas `timestamptz` UTC. Separa ocurrencia (`time`) de procesamiento (`ingested_at`). País puede ser nulo. No rellenes la magnitud nula con cero. `fecha_id` puede ser la fecha `YYYY-MM-DD`.

Índices mínimos a dejar creados, aunque la medición sea el paso 11: único de versión, único de evento actual y un índice por tiempo de ocurrencia. El índice no se afirma como mejora hasta medirlo.

Guarda el GeoJSON original de cada versión en `evento_version`. La cuarentena puede estar vacía en este paso, pero la tabla existe.

## Escritura

El consumidor, al recibir el mensaje de prueba:

1. Valida lo mínimo para poder insertarlo (geometría Point y coordenadas finitas).
2. Escribe versión y estado actual en una transacción.
3. Confirma la transacción.
4. Solo después confirma el offset de Kafka.

No confirmes el offset si la transacción falla. Si el registro no se puede guardar, no bloquees la cola para siempre: eso se completa en el paso 6 con cuarentena.

## Hecho cuando

Tras `docker compose up --build -d`, una consulta SQL muestra una fila en `evento_actual` y otra en `evento_version` para el evento de prueba. Al reiniciar los contenedores sin borrar el volumen, la fila sigue ahí.

## No hagas todavía

No des por cerrada la idempotencia ni la regla de versiones: es el paso 5. No asignes país todavía.

Siguiente skill, solo si el usuario la pide: `observatorio-05-duplicados-revisiones`.
