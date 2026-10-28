---
name: observatorio-06-pais-calidad
description: >-
  Asigna país por punto en polígono con el GeoJSON de Natural Earth y aplica
  validación, cuarentena y reglas de nulos en el consumidor. Usar cuando el
  usuario pida el paso 6 del observatorio sísmico, el catálogo geográfico, la
  calidad de datos o la cuarentena.
disable-model-invocation: true
---

# Paso 6 — País y reglas de calidad

## Contexto

Asignar país es trabajo del consumidor, no de Leaflet. Dibujar fronteras no rellena `country_id`. El apartado de calidad de la memoria se redacta en el paso 11; aquí el sistema solo aplica reglas y conserva rechazos. No crees `generar_informe_calidad.py`, ni un panel de calidad, ni una tabla extra de métricas: no son requisitos.

Lee `ENUNCIADO.md` secciones 4.3 y 6, `FUENTES-Y-LICENCIAS.md` y `FAQ-ALUMNADO.md` preguntas 16–20.

## Catálogo

Usa `frontend/public/datos/paises.geojson` sin modificarlo (177 entidades, SHA-256 en `FUENTES-Y-LICENCIAS.md`). Cárgalo en `pais`. `ADM0_A3` es el identificador tras comprobar que es único; no afirmes que todos los códigos son ISO oficiales. Guarda `NAME_ES`, `ADMIN`, `CONTINENT` y `SUBREGION`.

Punto y polígonos en WGS84 / EPSG:4326. Construye el punto con longitud y latitud (`coordinates[0]`, `coordinates[1]`). No saques el país del texto `place`. No asignes el país más cercano.

| Situación | Regla por defecto, documentada en `docs/asignacion-pais.md` |
|---|---|
| Un polígono contiene el punto | `country_id = ADM0_A3` |
| Ninguno | `country_id` nulo, «Sin país asignado»; no es un error |
| Varios o frontera | Regla determinista explícita (por ejemplo el de menor área, y `covers` o `contains` dicho en claro). No afirmes precisión legal: la escala es 1:110m |

Comprueba `(-3.7, 40.4)` → España (`ESP`) y un punto atlántico → nulo.

## Validación del consumidor

| Caso | Acción |
|---|---|
| `type` distinto de `earthquake` | Excluir del análisis y guardar el motivo |
| Coordenadas no finitas, latitud fuera de [-90, 90], longitud fuera de [-180, 180], o geometría que no sea Point | Cuarentena con motivo y original; no inventar un punto |
| `mag` null | Conservar null |
| Magnitud negativa | No rechazarla solo por el signo |
| Profundidad negativa | No rechazarla sin dejar escrito su significado (puede ser una elevación respecto al datum de USGS) |
| Mismo `id` y `updated` | No sumar versión ni evento |
| JSON o tipos ilegibles | Cuarentena; seguir con el resto de la cola |

No rellenes nulos con cero. Fechas a UTC sin perder los milisegundos originales. Registra qué transformación cambia datos y a cuántos registros afecta, aunque sea en el log o en `consulta_fuente`. Los casos dañados a propósito llevan una marca de prueba y no entran en el análisis real.

La cuarentena se confirma en base antes de avanzar el offset, con referencia al original.

## Hecho cuando

Un punto en España tiene `ESP`, un punto en el océano tiene país nulo y sigue consultable, y una coordenada inválida está en `cuarentena` con motivo y no aparece como punto. `paises.geojson` no ha cambiado.

## No hagas todavía

No redactes el informe completo de las seis dimensiones: basta con que las reglas queden aplicadas y los rechazos guardados. La API es el paso 7.

Siguiente skill, solo si el usuario la pide: `observatorio-07-api`.
