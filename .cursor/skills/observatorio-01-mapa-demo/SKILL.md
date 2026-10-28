---
name: observatorio-01-mapa-demo
description: >-
  Arranca el mapa Angular entregado en modo demo y comprueba fronteras, cuatro
  eventos ficticios, fichas, capas, zoom, leyenda y atribución. Usar cuando el
  usuario pida el paso 1 del observatorio sísmico, verificar el frontend
  entregado o abrir el mapa de demostración.
disable-model-invocation: true
---

# Paso 1 — Mapa de demostración

## Contexto

Repositorio del observatorio sísmico. Este paso solo comprueba el material entregado. No implementes backend, filtros, gráficos ni tabla. No modifiques `frontend/public/datos/paises.geojson` ni `frontend/public/datos/terremotos-demo.geojson`. No cambies `frontend/public/config.json`: debe seguir en `"mode": "demo"`.

Lee `README.md` (secciones 1 y 2) y `VALIDACION.md`.

## Arranque

Requisitos: Node.js 22.12+ de la rama 22, o Node 24. Arranca el frontend y déjalo en marcha. Desde `frontend/`:

```bash
npm ci
npm start
```

Indica al usuario que abra http://localhost:4200. `npm run build` correcto no sustituye la comprobación visual. No cierres este paso con una captura ni con una pasada hecha por el agente: la verificación visual la hace el usuario.

## Comprobar en el navegador

Pide al usuario que recorra el mapa y confirme estos puntos:

1. Se ven fronteras de países y exactamente cuatro puntos.
2. Los puntos están en España, Japón, Chile y el Atlántico (evento marítimo). Intercambiar latitud y longitud los desplazaría.
3. Al pulsar un punto, la ficha muestra lugar, magnitud, profundidad, fecha UTC, país e id. El cuarto evento muestra magnitud ND y «Sin país asignado».
4. El selector de capas activa y desactiva OpenStreetMap, países y terremotos.
5. Zoom y desplazamiento funcionan. El zoom permitido del mapa entregado es 2–8.
6. La leyenda de profundidad y la atribución de OpenStreetMap y Natural Earth son visibles.
7. El estado dice que es demostración con datos ficticios, no actividad real.

Si OpenStreetMap no carga, desactiva esa capa y comprueba que fronteras y puntos locales siguen visibles.

## Hecho cuando

El frontend está sirviendo http://localhost:4200, el usuario ha confirmado los siete puntos y `config.json` sigue en modo demo. Sin esa confirmación el paso no está cerrado.

## No hagas todavía

No conectes la API, no crees Docker y no edites el componente salvo que el mapa entregado esté roto y el usuario pida repararlo.

Siguiente skill, solo si el usuario la pide: `observatorio-02-explorar-usgs`.
