# Skills del observatorio sísmico

Cada skill de paso se aplica solo cuando se invoca por su nombre. El agente `.cursor/agents/observatorio-orquestador.md` ejecuta la parte y, al cerrarla, invoca una sola vez `observatorio-revisar-iteracion`. Las skills de paso no lanzan esa revisión.

| Skill | Qué cierra |
|---|---|
| `observatorio-01-mapa-demo` | Mapa entregado: 4 puntos ficticios, fronteras, fichas y capas |
| `observatorio-02-explorar-usgs` | Un GeoJSON real de USGS y la nota de campos, tipos y unidades |
| `observatorio-03-kafka-minimo` | Compose con Kafka, productor y consumidor; un mensaje de prueba |
| `observatorio-04-postgres` | Esquema, volumen y la primera fila escrita por el consumidor |
| `observatorio-05-duplicados-revisiones` | Productor real y la secuencia E1/E2 sin duplicar ni pisar versiones |
| `observatorio-06-pais-calidad` | País por punto en polígono, nulos y cuarentena |
| `observatorio-07-api` | FastAPI: `/api/eventos`, `/api/salud` y CORS |
| `observatorio-08-angular-api` | El mapa lee la API y muestra la última ingesta |
| `observatorio-09-historico-analisis` | Histórico 2025, filtros, ventanas, gráficos, tabla y comparación |
| `observatorio-10-netlify-ngrok` | Panel público y túnel HTTPS, con el fallo si el túnel se cierra |
| `observatorio-11-reproduccion-informe` | Replay aislado, mediciones, costes y memoria |
| `observatorio-revisar-rubrica` | Contrasta el repo con la rúbrica y las pruebas de aceptación, sin modificar código |
| `observatorio-verificar-parte` | Comprueba el código de la parte recién desarrollada (01 a 11) y devuelve correcta, incorrecta o incompleta |
| `observatorio-revisar-iteracion` | Al cerrar una iteración, revisa el diff de lo hecho y no deja seguir si el resultado no es correcta |
