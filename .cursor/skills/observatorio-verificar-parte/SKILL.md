---
name: observatorio-verificar-parte
description: >-
  Comprueba el código y las evidencias de una parte del observatorio sísmico
  (pasos 01 a 11) y devuelve correcta, incorrecta o incompleta. Usar después
  de implementar un paso, al cerrar una iteración, o cuando el usuario pida
  verificar el código de la parte desarrollada.
disable-model-invocation: true
---

# Verificar una parte del observatorio

Comprueba solo la parte indicada. No implementes, no refactorices y no pases al paso siguiente. Una lectura del código no basta: ejecuta la comprobación o marca la prueba como incompleta.

## Qué parte

1. Si quien te llama indica `01`–`11`, verifica esa.
2. Si no indica ninguna, detecta la parte más avanzada con código o documentos propios (de la 11 hacia la 01) y verifica solo esa. Di cuáles anteriores no has mirado.
3. No uses `observatorio-revisar-rubrica` en lugar de esta skill. La rúbrica mira la entrega completa; aquí se mira el cierre de un paso.
4. A partir de la parte 05, no verifiques las partes 03 ni 04. Si te las piden, responde que quedan cerradas: el mensaje ficticio y la fila de prueba se retiran a propósito en el paso 05. No las marques `incorrecta` por haber desaparecido.

Un paso posterior puede cambiar `config.json` a modo `api`. No reviertas esa configuración al reverificar el paso 01: exige que el modo demo siga implementado y que los ficheros de demostración estén intactos.

## Resultado

La primera línea de la respuesta es exactamente una de estas:

```text
resultado: correcta
resultado: incorrecta
resultado: incompleta
```

- **correcta**: todas las comprobaciones obligatorias de esa parte tienen evidencia leída o ejecutada.
- **incorrecta**: alguna obligatoria falla.
- **incompleta**: falta una evidencia que había que ejecutar (Docker parado, navegador sin abrir, consulta SQL no hecha). No la conviertas en correcta.

Después lista cada comprobación como `pasa`, `falla` o `sin evidencia`, con la ruta, el comando o la salida que lo sostiene. Cierra con qué hay que corregir antes de seguir. No des por bueno un comentario, un TODO ni un documento que solo copie ejemplos ficticios de `FAQ-ALUMNADO.md`.

## En todas las partes

- `.env`, authtoken de ngrok, `node_modules` y GeoJSON grandes descargados no están en Git.
- El código no llama a USGS desde Angular.
- El país no se deduce del texto `place`.

## 01 — Mapa demo

- `frontend/public/datos/terremotos-demo.geojson` sigue teniendo cuatro eventos ficticios, uno con magnitud nula y país nulo.
- SHA-256 de `frontend/public/datos/paises.geojson` igual a `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`.
- El componente distingue modo demo y modo api.
- Si esta parte acaba de implementarse y nadie ha pasado del paso 01, `config.json` está en `"mode": "demo"`.
- El frontend está en marcha en http://localhost:4200. La evidencia visual la da el usuario al confirmar fronteras, cuatro puntos, una ficha, el selector de capas, zoom, leyenda y atribución. Sin esa confirmación, `incompleta`. No la sustituyas por una pasada del agente. Un diff vacío no es un fallo.

## 02 — Fuente USGS

- Existe `docs/fuente-usgs.md` con la URL `all_day.geojson`, la hora UTC de una descarga real, un evento real (id y coordenadas) y las unidades: milisegundos Unix, longitud, latitud, profundidad en km.
- Explica que el feed es una ventana móvil de unas 24 horas.
- El GeoJSON descargado no está en el repositorio. Si la nota solo repite el ejemplo ficticio de la FAQ, falla.

## 03 — Kafka mínimo

- Un solo `compose.yaml` con papeles separados de Kafka, productor y consumidor, salud y reintentos.
- Dentro de Compose, el cliente usa el nombre del servicio Kafka, no `localhost`.
- `requirements.txt` fija aiokafka. `.env.example` no lleva secretos.
- Retención de Kafka limitada y documentada. El broker no se publica por ngrok.
- Evidencia de un mensaje de prueba en el log del consumidor tras `docker compose up --build -d`. Sin contenedores en marcha, incompleta.

## 04 — PostgreSQL

- Servicio PostgreSQL, volumen con nombre e SQL de arranque.
- Existen `fecha` (un día UTC, `fecha_id` único), `evento_actual` (`event_id` único y `fecha_id` del día UTC de ocurrencia), `evento_version` (único `event_id` + `updated`), `cuarentena`, `publicacion` y `consulta_fuente`, o un modelo distinto justificado con el mismo grano. El timestamp completo se conserva para las ventanas horarias.
- La magnitud nula no se guarda como cero. El offset de Kafka se confirma después de la transacción, no antes. Léelo en el código del consumidor.
- Una consulta SQL muestra una fila en `evento_actual` y otra en `evento_version`, y la fila sigue tras reiniciar sin borrar el volumen. Sin esa consulta, incompleta.

## 05 — Duplicados y revisiones

- El productor publica solo id desconocido o `updated` posterior, espera el acuse de Kafka y solo entonces escribe `publicacion`. El estado no vive solo en memoria.
- El consumidor no inserta otra versión si `(event_id, updated)` ya existe y no pisa `evento_actual` con un `updated` anterior.
- `docs/prueba-revisiones.md` recoge la secuencia E1/E2 con recuentos 1/1, 1/1, 1/2, 1/2 y 2/3, y E1 queda en magnitud 4,6. Tienen que ser salidas de consulta, no la tabla copiada del enunciado.
- Hay evidencia de reenvío tras reiniciar el consumidor sin aumentar filas. Sin ella, incompleta.

## 06 — País y calidad

- El consumidor hace punto en polígono con `frontend/public/datos/paises.geojson`, en WGS84, longitud y latitud en ese orden. El hash del fichero no ha cambiado.
- País nulo si no hay polígono. No hay asignación al país más cercano.
- `docs/asignacion-pais.md` explica frontera o varias coincidencias.
- Coordenada inválida va a `cuarentena` con motivo y original, y no sale en la geometría servida.
- Magnitud nula se conserva. Una magnitud negativa no se rechaza solo por el signo.
- Evidencia de un punto en España con `ESP`, un punto oceánico con país nulo y un punto inválido en cuarentena. Sin esas tres consultas o pruebas, incompleta.

## 07 — API

- El quinto servicio escucha en `0.0.0.0:8000`. Puerto de host, si existe, en `127.0.0.1`.
- `GET /api/eventos` devuelve un `FeatureCollection` leído de PostgreSQL: una versión actual por evento, últimas 24 horas por `time`, `features: []` si no hay filas, `null` en vez de NaN, y metadatos `generated`, `last_ingestion`, `mode`, `count`, `truncated`.
- Filtros `start` (inclusive), `end` (exclusive), `min_mag`, `country_id`. Una magnitud nula no cumple `min_mag`.
- Un fallo de base es un error HTTP, no un recuento cero.
- `GET /api/salud` no devuelve credenciales. CORS permite `http://localhost:4200`, GET, OPTIONS y `ngrok-skip-browser-warning`.
- Evidencia de un GET real y de un OPTIONS. Sin ella, incompleta.

## 08 — Angular contra la API

- `config.json` en modo `api`, con `apiUrl` sin sufijo `/api` y sin el marcador `TU-DOMINIO-NGROK`.
- El panel muestra la última lectura, `generated` y `last_ingestion`, y avisa si la ingesta está vieja.
- Si la petición falla, el estado cambia y la capa anterior permanece.
- Pasada en el navegador: puntos de la base (no los cuatro ficticios), una ficha, fallo al cortar la API y recuperación al siguiente refresco. Sin esa pasada, incompleta.

## 09 — Histórico y análisis

- `docs/historico.md` explica la descarga de 2025, magnitud ≥ 4, por intervalos, el corte al llegar a 20.000 y la deduplicación de extremos. Los GeoJSON no están en Git.
- `GET /api/estadisticas` usa en mapa, tabla, ventanas y distribuciones los mismos `start`, `end`, `min_mag` y `country_id`. La comparación no hereda `start`/`end`: es últimas 24 horas frente a la media diaria de 2025, con el mismo país o región y el mismo corte de magnitud (≥ 4, o mayor si el filtro lo sube). Las ventanas son horas UTC de ocurrencia, con el extremo final excluido, e incluyen «Sin país asignado».
- La media histórica divide entre 365 aunque haya días a cero. Si la media es 0, la variación es ND. El panel muestra los dos periodos y el denominador.
- No hay un contador que sume cada mensaje Kafka.
- El panel tiene filtros, gráficos, tabla y la comparación, y los tres cambian juntos. `docs/conclusiones.md` tiene tres lecturas con cifra, filtro y periodo.
- Si la API trunca, el panel lo dice y no calcula totales sobre el recorte.
- Sin ver el filtro en el navegador y sin filas de 2025 en la base, incompleta.

## 10 — Netlify y ngrok

- `docs/despliegue.md` tiene la URL HTTPS del panel, la opción de ngrok (equipo o contenedor) y cómo encender el sistema en la defensa.
- `apiUrl` es la URL HTTPS real asignada. El authtoken no aparece en el repo, en la imagen ni en `config.json`.
- CORS incluye el origen exacto de Netlify.
- El panel distingue túnel caído de datos simplemente antiguos.
- Con la misma URL, al reabrir el túnel el refresco siguiente recupera los datos. Si el dominio gratuito cambia, `docs/despliegue.md` explica que hay que volver a publicar `config.json`; eso no suspende la prueba cuando la URL estable sí se recuperó.
- Evidencia de apertura desde fuera de localhost, del aviso al cerrar el túnel y de la recuperación con la URL estable. Sin ella, incompleta.

## 11 — Reproducción e informe

- Replay con topic y tablas o esquema distintos de `live`, etiqueta «REPRODUCCIÓN» en API y panel, fechas originales conservadas, y un duplicado más una revisión controlados.
- `docs/prueba-reproduccion.md` muestra que esos eventos no entran en el análisis en vivo.
- Hay memoria o notebook con las seis dimensiones de calidad (consulta, denominador, acción), el modelo físico, tres conclusiones que no predicen terremotos, tres mediciones de tiempo y memoria, costes con supuestos y las pruebas de aceptación con resultado observado.
- Los datos sintéticos de la medición están marcados y fuera de las conclusiones de sismicidad.
- Si el replay no se ha ejecutado o la memoria no contiene resultados pegados, incompleta.
