---
name: observatorio-09-historico-analisis
description: >-
  Carga el histórico USGS 2025, implementa filtros, ventanas, distribuciones,
  comparación histórica, gráficos y tabla del panel. Usar cuando el usuario
  pida el paso 9 del observatorio sísmico, el histórico, las estadísticas o
  los filtros del mapa.
disable-model-invocation: true
---

# Paso 9 — Histórico, filtros y análisis

## Contexto

El feed de 24 h y el histórico son dos accesos a USGS. El histórico se descarga una vez, no cada minuto. Mismas reglas de limpieza, país y versiones que el directo. Angular sigue leyendo solo la API.

Lee `ENUNCIADO.md` secciones 4.2 y 8, `CONTRATO-API.md` y `FAQ-ALUMNADO.md` preguntas 21–25.

## Descarga del histórico

Propuesta obligatoria salvo que el usuario documente otro recorte y lo use también en la comparación: año 2025, mundial, magnitud ≥ 4, `eventtype=earthquake`.

Mes a mes, por ejemplo:

```text
https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2025-01-01T00:00:00Z&endtime=2025-02-01T00:00:00Z&minmagnitude=4&eventtype=earthquake&orderby=time-asc
```

Si un intervalo devuelve 20.000 eventos, el tope de la fuente, divídelo. No lo trunques en silencio. Los extremos pueden repetir eventos: deduplica por `id` y quédate con la versión coherente con la regla de `updated`. Guarda en `consulta_fuente` la URL, la fecha de extracción y el número de registros. Conserva los GeoJSON fuera de Git y deja en `docs/historico.md` el procedimiento para regenerarlos.

Cárgalos con la lógica común del consumidor (Kafka de carga o un batch que use las mismas funciones). Documéntalo. No pierdas el histórico al reiniciar contenedores.

El histórico es una instantánea del catálogo el día de la extracción, no todas las revisiones pasadas.

## API de estadísticas y filtros

Completa `GET /api/estadisticas`. Cada bloque indica periodo, filtros, unidad y cuántos registros no tienen valor.

Magnitud y país o región sí son los mismos en el mapa, la tabla, los gráficos y la comparación. El intervalo `start`/`end` rige el mapa, la tabla, las ventanas y las distribuciones. No sustituye los dos periodos de la comparación histórica.

Calcula las agregaciones desde `evento_actual` (o recalculando las ventanas afectadas). No incrementes un contador por mensaje Kafka. Una revisión no suma otro evento; si cambia `time`, la ventana vieja y la nueva quedan corregidas.

- Ventanas fijas de una hora UTC por tiempo de ocurrencia: `[10:00, 11:00)` contiene las 10:03 y las 10:48; las 11:00 va a la siguiente. Incluye «Sin país asignado». Conteos por país o subregión.
- Distribuciones de magnitud y de profundidad, con el número de nulos. Los nulos no entran en la media; indica el denominador usado.
- Comparación, en un bloque aparte y con los dos periodos escritos: últimas 24 horas frente a la media diaria de 2025. El denominador histórico es 365 aunque haya días con cero. Los dos lados usan el mismo país o región, el tipo earthquake y la magnitud ≥ 4. Si el filtro de magnitud es mayor que 4, ese corte se aplica también en los dos lados. Si el usuario no filtra magnitud o pone un mínimo menor que 4, la comparación sigue en ≥ 4 y lo indica: no se compara el feed sin ese corte con el histórico ya filtrado. Si la media es 0, la variación porcentual es ND. Advierte de que el periodo reciente puede estar incompleto por retrasos de USGS.

Si la respuesta de puntos va truncada, el panel lo dice y no calcula estadísticas globales sobre el recorte.

## Panel

Añade, aplicados a la vez al mapa y a los gráficos:

1. Filtros de fecha, magnitud y país o región.
2. Gráficos de las ventanas, de los conteos geográficos y de las dos distribuciones. Sin librería nueva si SVG o CSS bastan; si añades una, fija la versión y actualiza el lockfile.
3. La comparación histórica, con los dos periodos, el corte de magnitud, el ámbito y el denominador 365 visibles. El filtro de fechas del mapa no cambia esos dos periodos.
4. Una tabla de eventos usable sin depender del color del mapa.
5. El aviso de truncado y el de datos desactualizados ya empezado en el paso 8.

Comprueba el flujo en el navegador: cambiar un filtro refresca mapa, gráficos y tabla con el mismo criterio. Prueba el vacío (filtro sin eventos) y un país nulo visible como «Sin país asignado».

## Hecho cuando

Hay eventos de 2025 en la base. Mapa, gráficos del periodo elegido y tabla cambian juntos al filtrar. La comparación sigue siendo últimas 24 horas frente a la media de 2025, con el mismo ámbito y el mismo corte de magnitud. Anota tres lecturas con cifras, filtros y periodo en `docs/conclusiones.md` (aún no es la memoria final).

## No hagas todavía

No abras ngrok ni mezcles la reproducción acelerada con estas tablas.

Siguiente skill, solo si el usuario la pide: `observatorio-10-netlify-ngrok`.
