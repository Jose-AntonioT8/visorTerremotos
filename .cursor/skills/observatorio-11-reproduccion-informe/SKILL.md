---
name: observatorio-11-reproduccion-informe
description: >-
  Prepara la reproducción histórica aislada, las mediciones de complejidad y
  coste, y la memoria o notebook de entrega del observatorio sísmico. Usar
  cuando el usuario pida el paso 11, el replay, la rúbrica escrita, el
  informe de calidad o la defensa.
disable-model-invocation: true
---

# Paso 11 — Reproducción, mediciones y memoria

## Contexto

Este paso cierra las evidencias. No añade infraestructura (Spark, Kubernetes, aprendizaje automático). No exige disponibilidad 24/7. Lee `ENUNCIADO.md` secciones 6, 10, 11 y 12, y `FAQ-ALUMNADO.md` preguntas 17, 32 y 33.

La revisión contra la rúbrica es otra skill: `observatorio-revisar-rubrica`. No la lances salvo que el usuario lo pida.

## Reproducción

Hace falta actividad aunque USGS no publique un sismo nuevo durante la defensa.

- Selección histórica ordenada por fecha, publicada acelerada (por ejemplo un evento cada pocos segundos).
- Se conserva `time` original y se añade la hora de reproducción.
- Topic distinto y esquema o tablas distintas de las de `live`, o un aislamiento equivalente.
- Etiqueta visible «REPRODUCCIÓN» en API (`metadata.mode`) y en el panel.
- El productor de replay reutiliza el procesamiento del consumidor.
- Incluye un duplicado y una revisión controlados, con el mismo resultado que la prueba E1/E2.
- La vista de replay consulta el intervalo histórico y los datos aislados. No reescribas las fechas a «ahora» para colarlas en el filtro de últimas 24 horas. No mezcles esos eventos con el análisis real.

Guarda la evidencia (SQL y captura o descripción del panel) en `docs/prueba-reproduccion.md`.

## Complejidad, memoria y coste

Justifica tres operaciones reales del código: búsqueda de la última versión por `event_id`, punto en polígono y agregación por ventanas. Distingue coste medio y peor caso.

Mide tiempo y memoria con al menos tres tamaños de entrada. Anota equipo, procedimiento y resultados. Los datos sintéticos van marcados y fuera de las conclusiones de sismicidad. Compara una búsqueda secuencial con un diccionario, o la misma consulta sin índice y con índice. Razona, sin fingir una medición, qué pasaría con 100 millones de filas.

Costes con supuestos explícitos: hardware, electricidad, almacenamiento, transferencia, mantenimiento y tiempo de desarrollo. Una cuota gratuita no es coste cero. Incluye una propuesta de escalado sin contratar servicios. No inventes un beneficio económico del observatorio; un ROI solo si el beneficio es medible y está justificado.

## Memoria o notebook

Un solo documento basta. Tiene que incluir, con consultas o código y resultados pegados:

- Diccionario de datos, procedencia y registro de consultas.
- Calidad: completitud, unicidad, validez, consistencia, actualidad y exactitud. Si una dimensión no se puede medir, explica el límite. Para cada comprobación: conjunto (mensajes, versiones o eventos actuales), periodo, denominador, resultado, acción y antes/después cuando exista. Los problemas se solapan: no sumes porcentajes de fallos como si fueran registros distintos.
- Decisiones: nulos conservados, magnitud negativa, profundidad negativa, cuarentena, país nulo, versiones.
- Modelo conceptual, lógico y físico, y por qué esos índices.
- Tres conclusiones. Cada una lleva cifra, filtros, ámbito, periodo y denominador. No son una predicción ni una evaluación de riesgo. Los tipos de magnitud no son la misma escala.
- Complejidad, mediciones, costes, limitaciones (feed que no avisa bajas, catálogo 1:110m, retrasos USGS, túnel encendido solo en la defensa) y mejoras.
- Pruebas de aceptación del enunciado, sección 11, con el resultado observado.
- Qué decisión técnica propia explica el alumno, en primera persona si el usuario redacta, o marcada como borrador para que la complete.

No hace falta un generador automático de informes ni un panel de calidad.

## Hecho cuando

Replay aislado y etiquetado, tres mediciones escritas, y la memoria o el notebook cubren calidad, modelo, tres conclusiones, costes y pruebas. Los originales grandes y los secretos siguen fuera de Git.

## Después

Si el usuario quiere la rúbrica, o el orquestador ya cerró la parte 11, usa `observatorio-revisar-rubrica`. No modifiques la nota tú mismo dentro de este paso.
