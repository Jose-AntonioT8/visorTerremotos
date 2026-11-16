# Fuentes y licencias

## Catálogo incluido

`frontend/public/datos/paises.geojson`: copia sin modificar de Natural Earth, Admin 0 Countries, escala 1:110.000.000, 177 entidades en esta copia.

- Descargado: 27 de octubre de 2026.
- Fuente: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson
- Proyecto: https://www.naturalearthdata.com/
- Licencia de los datos: dominio público. Se conserva el reconocimiento de procedencia.
- SHA-256: `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`
- El repositorio fuente puede cambiar: usa la copia entregada para reproducibilidad.
- `ADM0_A3` identifica la entidad Natural Earth; no asumir que todos los códigos son ISO oficiales. `NAME_ES`, `ADMIN`, `CONTINENT` y `SUBREGION` contienen atributos útiles.
- Fronteras simplificadas y convenciones cartográficas del proveedor; no sirve para delimitar jurisdicción legal ni para asignar con precisión eventos costeros. No incluye todos los pequeños territorios. El mar no es un país.
- `frontend/public/datos/paises-costa.geojson` sale de esa copia, que no se edita. El contorno crece 25 km hacia el mar y se corta al llegar a otro país, así la frontera terrestre sigue igual. El consumidor aplica el mismo margen al asignar el país.
- `frontend/public/datos/paises-10m.geojson` es el contorno que dibuja el mapa. La frontera terrestre sigue Natural Earth a 1:10.000.000, alineada con OpenStreetMap. En la costa el trazo sale 25 km hacia el mar, el mismo margen del consumidor, y se corta al llegar al margen de otro país. Solo conserva `NAME_ES` y `ADMIN`. No sustituye a `paises.geojson` en la asignación del país.
- Descargado: 15 de noviembre de 2026.
- Fuente: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson
- Licencia de los datos: dominio público, la misma del proyecto Natural Earth.

## Visualización

- Leaflet (BSD-2-Clause): https://leafletjs.com/
- ngx-leaflet (MIT): https://github.com/bluehalo/ngx-leaflet
- Angular (MIT): https://angular.dev/
- Teselas estándar OpenStreetMap: atribución visible obligatoria y política https://operations.osmfoundation.org/policies/tiles/ . No descargar masivamente ni precargar para uso offline. El servicio es externo, requiere Internet y no ofrece garantía para este proyecto.
- El GeoJSON está incluido; las bibliotecas se descargan mediante npm. No se distribuyen teselas de OpenStreetMap.

## Sismicidad y docencia

Lecturas en vivo del visor (filtro multi-fuente en la UI; propiedad `source`: `ign` | `usgs` | `emsc`):

| Fuente | Endpoint usado | Formato |
|---|---|---|
| USGS | https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson | GeoJSON |
| EMSC | https://www.seismicportal.eu/fdsnws/event/1/query?limit=500&format=json | GeoJSON (FDSN) |
| IGN (España) | https://www.ign.es/ign/RssTools/sismologia.xml | GeoRSS (últimos ~10 días, área ibérica/Canarias) |

También: formato USGS https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php · histórico USGS https://earthquake.usgs.gov/fdsnws/event/1/ · portal IGN https://www.ign.es/web/ign/portal · EMSC https://www.emsc.eu/

El pipeline propio (`GET /api/eventos`) sigue alimentándose del feed USGS y no se elimina. Las rutas aditivas `GET /api/fuentes/{ign|usgs|emsc}` normalizan las tres lecturas. En Netlify, el edge proxy puede servir esas rutas sin pasar por el túnel.

Sesiones: https://juanarrow.github.io/BigData/sesiones/index.html · Rúbrica: https://juanarrow.github.io/BigData/sesiones/sesion-08.html

Los eventos del archivo `terremotos-demo.geojson` son ficticios y están marcados como demostración. No utilizarlos para extraer conclusiones sobre sismicidad real.

El código de apoyo original de este paquete se ofrece para uso, modificación y distribución educativa sin restricciones adicionales. Las dependencias conservan sus propias licencias.
