---
name: observatorio-revisar-rubrica
description: >-
  Revisa el observatorio sísmico ya construido y lo contrasta con la rúbrica y
  las pruebas de aceptación, sin modificar código. Usar cuando el usuario pida
  revisar el trabajo, puntuar la práctica, buscar huecos o contrastar con la
  rúbrica de Big Data.
disable-model-invocation: true
---

# Revisión contra la rúbrica

## Cómo revisar

No cambies código, Compose ni documentos salvo que el usuario lo pida en el mismo mensaje. Inspecciona el repositorio; no puntúes por la intención ni por comentarios que no tengan implementación. Si un servicio no está en marcha, dilo y no des por pasada esa prueba.

Lee `ENUNCIADO.md` secciones 11 y 13, `FAQ-ALUMNADO.md` pregunta 35, `CONTRATO-API.md` y el código real (Compose, productor, consumidor, SQL, API, `frontend/src`, `config.json`, memoria o notebook).

Responde con el informe de más abajo. Niveles: insuficiente 0–4, suficiente 5–6, notable 7–8, sobresaliente 9–10. Elige el nivel cuya evidencia sí está, no el siguiente.

## Qué no marques como falta

No bajan la nota por estar ausentes: Spark, Flink, Kubernetes, aprendizaje automático, certificado TLS propio, generador `generar_informe_calidad.py`, panel de calidad en Angular, tabla aparte de métricas, transacción distribuida, reconciliación exhaustiva de eventos borrados por USGS, disponibilidad 24/7, motor de mapas propio.

Sí bajan la nota: panel que llama a USGS, país sacado de `place`, nulos grabados como cero, contador que suma cada mensaje, replay mezclado con live, secretos en Git, `localhost` entre contenedores, histórico truncado al llegar a 20.000, borrar eventos que salen de las 24 horas, estadísticas vendidas como predicción o riesgo.

## Criterios

| Criterio | Insuficiente | Suficiente | Notable | Sobresaliente | Evidencia que hay que encontrar |
|---|---|---|---|---|---|
| Extracción | No carga | Carga básica | Carga y exploración | Carga y análisis de tipos | Feed, histórico 2025 y catálogo; tipos, unidades, límites, automatización cada ~60 s |
| Calidad | No analiza | Análisis parcial | 4 dimensiones o más | Completo y con acciones | Apartado en memoria o notebook, antes/después, cuarentena con motivo, limitaciones. No exigas automatizar el informe |
| Modelado | No combina fuentes | Join básico | Modelo correcto | Modelo optimizado | Punto en polígono, grano, claves, revisión que no duplica, idempotencia, índice justificado con una medida |
| Análisis | No analiza | 1 o 2 análisis | 3 o más | Análisis con conclusiones | Ventanas horarias UTC, distribuciones con nulos, comparación equivalente (mismos filtros, días con cero), al menos tres conclusiones con cifras |
| Reflexión | No reflexiona | Reflexión básica | Buena | Excelente y con propuestas | Complejidad de tres operaciones, tres tamaños medidos, costes con supuestos, escalado, limitaciones |

## Pruebas de aceptación

Para cada fila: cumplida, incumplida o sin evidencia. Cita archivo, consulta o salida.

| Prueba | Resultado exigido |
|---|---|
| Evento nuevo | Una fila actual, visible en API, mapa y análisis |
| Misma versión reenviada | No aumenta el número de terremotos |
| Versión posterior | Cambian la fila actual y las agregaciones afectadas |
| Versión antigua tardía | No sustituye a la más reciente |
| Magnitud nula | Se conserva y se ve como ND |
| Coordenadas inválidas | Cuarentena con motivo; no hay punto inventado |
| Evento marítimo | Sin país; sigue en el análisis |
| Reinicio del consumidor | Reanuda sin duplicar lo ya persistido |
| Túnel cerrado | El panel avisa y no disfraza la última lectura de lectura nueva |
| Túnel reabierto | Con la misma URL, el refresco siguiente recupera las consultas. Un dominio nuevo de ngrok no suspende la prueba si el despliegue lo explica y la URL estable sí se recuperó |
| Reproducción | Pasa por Kafka, aislada, etiquetada «REPRODUCCIÓN», con las fechas originales |

Comprueba también el cierre operativo: los cinco servicios en un solo `compose.yaml` con salud y reintentos; volúmenes; `.env.example` sin secretos; API en `0.0.0.0:8000`; CORS del origen real; `config.json` en modo `api` con HTTPS de ngrok cuando se hable de producción; filtros coherentes entre mapa, tabla y estadísticas; truncado señalado.

## Informe

```markdown
# Revisión del observatorio

## Veredicto
Una frase: qué nivel global sostiene la evidencia y qué criterio lo frena.

## Por criterio
Para cada uno: nivel, prueba concreta (ruta o consulta) y el hueco exacto para el nivel siguiente.

## Pruebas de aceptación
Tabla con cumplida / incumplida / sin evidencia.

## Errores que bajan la nota
Solo los que estén en el código o en la memoria.

## Huecos ordenados
Lista corta para acercarse a sobresaliente, del bloqueo mayor al menor.

## Opcional no exigido
Menciona ampliaciones solo para no perseguirlas.

## No comprobado
Qué no estaba en marcha o no estaba en el repositorio.
```
