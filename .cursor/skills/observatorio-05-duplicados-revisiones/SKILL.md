---
name: observatorio-05-duplicados-revisiones
description: >-
  Implementa y demuestra deduplicación, revisiones e idempotencia de productor
  y consumidor con la secuencia E1/E2 del observatorio. Usar cuando el usuario
  pida el paso 5, duplicados, revisiones, offsets, upsert o el productor USGS.
disable-model-invocation: true
---

# Paso 5 — Duplicados, revisiones y productor real

## Contexto

Procesamiento al menos una vez, con escritura idempotente. No hace falta una transacción distribuida Kafka–PostgreSQL. El orden por clave ayuda, pero no sustituye comparar `updated`.

Lee `ENUNCIADO.md` secciones 5 y 7, y `FAQ-ALUMNADO.md` preguntas 10 y 12–15. Los números de la pregunta 12 son la prueba de aceptación de este paso.

## Productor

En cada consulta del feed (cada ~60 s, por entorno):

| Situación frente a `publicacion` | Decisión |
|---|---|
| `id` desconocido | Publicar |
| mismo `id` y mismo `updated` | No publicar |
| `updated` posterior | Publicar la revisión |
| `updated` anterior | No publicar esa versión atrasada |

Espera el acuse de Kafka y solo entonces actualiza `publicacion`. Si el proceso muere entre medias, el reenvío es correcto: el consumidor debe absorberlo. El estado no puede vivir solo en memoria.

Filtra `properties.type == "earthquake"`. Conserva el motivo de exclusión de otros tipos. Ante timeout, HTTP 429/5xx o JSON inválido: reintento con espera creciente, log del error y sin borrar el estado válido anterior.

No borres un evento porque desaparezca del feed: pudo salir de la ventana de 24 h. El alcance mínimo no reconcilia bajas ni fusiones de USGS; deja esa limitación escrita en un comentario de diseño o en `docs/limitaciones.md`.

El mensaje lleva `source`, `ingested_at`, `mode` (`live` o `replay`) y el evento original. Clave Kafka = `id`.

Sustituye el evento ficticio del paso 3 por este productor. Puedes dejar un modo de prueba explícito para la secuencia de abajo; no lo mezcles con el topic en vivo sin etiquetar `mode`.

## Consumidor

Para cada mensaje:

1. Preparar la versión.
2. Si `(event_id, updated)` ya existe, no insertar otra versión ni sumar un evento.
3. Insertar la versión nueva.
4. Actualizar `evento_actual` solo si no hay fila o si `updated` es posterior. Una versión antigua no pisa a una más reciente.
5. Confirmar la transacción y, después, el offset.

Las restricciones únicas y el upsert deben impedir que un reenvío aumente el recuento. Una revisión que cambie la magnitud cambia la fila actual, no añade otro terremoto.

## Prueba obligatoria

Parte de tablas de eventos vacías (no borres el catálogo de países si ya existiera). Inyecta, en este orden, y consulta después de cada mensaje:

| Mensaje | id | updated | mag | Eventos actuales | Versiones |
|---|---|---|---|---:|---:|
| Primera | E1 | 10:05 | 4,2 | 1 | 1 |
| Repetición | E1 | 10:05 | 4,2 | 1 | 1 |
| Revisión | E1 | 10:09 | 4,6 | 1 | 2 |
| Antigua tardía | E1 | 10:05 | 4,2 | 1 | 2 |
| Otro | E2 | 10:12 | 3,1 | 2 | 3 |

En la implementación, `updated` es timestamp completo. Resultado final: E1 magnitud 4,6 y E2 magnitud 3,1. Guarda la salida SQL en `docs/prueba-revisiones.md`. Reinicia el consumidor antes de confirmar un offset y comprueba que el reenvío no duplica la fila.

Estos identificadores son de prueba. No los presentes como sismos reales ni los dejes en el análisis de USGS.

## Hecho cuando

La tabla de la prueba coincide con las consultas reales y un reenvío tras reinicio no aumenta eventos ni versiones.

## No hagas todavía

No asignes país ni abras la API pública.

Siguiente skill, solo si el usuario la pide: `observatorio-06-pais-calidad`.
