"""Productor. Publica novedades y revisiones, y consulta el feed real en MODE=live.

No borra un evento porque desaparezca del feed: pudo salir de la ventana de 24 horas.
La reconciliación de bajas y fusiones de USGS queda fuera del alcance mínimo;
está descrita en docs/limitaciones.md.
"""

import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

import asyncpg
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic

BOOTSTRAP = os.environ["KAFKA_BOOTSTRAP"]
TOPIC = os.environ["KAFKA_TOPIC"]
MODE = os.environ.get("MODE", "live")
INTERVAL_SECONDS = int(os.environ.get("INTERVAL_SECONDS", "60"))
FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

DIA = datetime(2026, 10, 28, tzinfo=timezone.utc)


def milis(hora, minuto):
    momento = DIA.replace(hour=hora, minute=minuto)
    return int(momento.timestamp() * 1000)


def evento_prueba(identificador, updated_ms, magnitud):
    return {
        "type": "Feature",
        "id": identificador,
        "geometry": {"type": "Point", "coordinates": [-3.7, 40.4, 12]},
        "properties": {
            "type": "earthquake",
            "mag": magnitud,
            "magType": "ml",
            "place": "Secuencia de prueba, no es un sismo real",
            "time": milis(10, 0),
            "updated": updated_ms,
        },
    }


SECUENCIA = [
    evento_prueba("E1", milis(10, 5), 4.2),
    evento_prueba("E1", milis(10, 5), 4.2),
    evento_prueba("E1", milis(10, 9), 4.6),
    evento_prueba("E1", milis(10, 5), 4.2),
    evento_prueba("E2", milis(10, 12), 3.1),
]


async def conectar_postgres():
    espera = 1
    for intento in range(1, 16):
        try:
            return await asyncpg.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
            )
        except Exception as exc:
            print(f"PostgreSQL no está listo (intento {intento}): {exc}", flush=True)
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
    raise SystemExit("No se pudo conectar con PostgreSQL")


async def asegurar_topic():
    espera = 1
    for intento in range(1, 16):
        admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
        try:
            await admin.start()
            temas = await admin.list_topics()
            if TOPIC not in temas:
                await admin.create_topics([NewTopic(TOPIC, num_partitions=1, replication_factor=1)])
            await admin.close()
            return
        except Exception as exc:
            print(f"Kafka no está listo (intento {intento}): {exc}", flush=True)
            try:
                await admin.close()
            except Exception:
                pass
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
    raise SystemExit("No se pudo conectar con Kafka")


async def decision(conn, evento):
    fila = await conn.fetchrow(
        "SELECT updated_ms FROM publicacion WHERE event_id = $1",
        evento["id"],
    )
    updated = evento["properties"]["updated"]
    if fila is None:
        return "publicar"
    if updated == fila["updated_ms"]:
        return "omitir-igual"
    if updated > fila["updated_ms"]:
        return "publicar"
    return "omitir-atrasada"


async def marcar_publicada(conn, evento):
    await conn.execute(
        """
        INSERT INTO publicacion (event_id, updated_ms, published_at)
        VALUES ($1, $2, $3)
        ON CONFLICT (event_id) DO UPDATE
        SET updated_ms = EXCLUDED.updated_ms, published_at = EXCLUDED.published_at
        WHERE publicacion.updated_ms < EXCLUDED.updated_ms
        """,
        evento["id"],
        evento["properties"]["updated"],
        datetime.now(timezone.utc),
    )


async def enviar(productor, evento, mode):
    mensaje = {
        "source": "usgs" if mode == "live" else "secuencia-prueba",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "event": evento,
    }
    meta = await productor.send_and_wait(
        TOPIC,
        json.dumps(mensaje).encode("utf-8"),
        key=evento["id"].encode("utf-8"),
    )
    print(
        f"Acuse de Kafka: id={evento['id']} updated={evento['properties']['updated']} "
        f"offset={meta.offset} mode={mode}",
        flush=True,
    )


async def excluir(conn, evento):
    tipo = (evento.get("properties") or {}).get("type")
    motivo = f"tipo distinto de earthquake: {tipo}"
    await conn.execute(
        """
        INSERT INTO cuarentena (motivo, original, ingested_at)
        SELECT $1, $2::jsonb, $3
        WHERE NOT EXISTS (
            SELECT 1 FROM cuarentena
            WHERE motivo = $1 AND original->>'id' = $4
        )
        """,
        motivo,
        json.dumps(evento),
        datetime.now(timezone.utc),
        evento.get("id"),
    )
    print(f"Excluido {evento.get('id')}: {motivo}", flush=True)


async def publicar_si_procede(conn, productor, evento, mode):
    tipo = (evento.get("properties") or {}).get("type")
    if tipo != "earthquake":
        await excluir(conn, evento)
        return
    accion = await decision(conn, evento)
    if accion != "publicar":
        print(f"No publico {evento['id']} updated={evento['properties']['updated']}: {accion}", flush=True)
        return
    await enviar(productor, evento, mode)
    await marcar_publicada(conn, evento)


async def descargar_feed():
    espera = 1
    for intento in range(1, 6):
        try:
            def leer():
                peticion = urllib.request.Request(FEED_URL, headers={"User-Agent": "observatorio-sismico"})
                with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                    return respuesta.status, respuesta.read()

            estado, cuerpo = await asyncio.to_thread(leer)
            if estado == 429 or estado >= 500:
                raise RuntimeError(f"HTTP {estado}")
            return json.loads(cuerpo)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            print(f"Error al consultar USGS, se conserva la publicacion anterior (intento {intento}): {exc}", flush=True)
            await asyncio.sleep(espera)
            espera = min(espera * 2, 60)
    return None


async def bucle_vivo(conn, productor):
    while True:
        datos = await descargar_feed()
        if datos is not None:
            features = datos.get("features") or []
            for feature in features:
                await publicar_si_procede(conn, productor, feature, "live")
            await conn.execute(
                """
                INSERT INTO consulta_fuente (consulted_at, url, record_count, resultado)
                VALUES ($1, $2, $3, 'ok')
                """,
                datetime.now(timezone.utc),
                FEED_URL,
                len(features),
            )
            print(f"Consulta USGS correcta: {len(features)} features. Siguiente en {INTERVAL_SECONDS}s", flush=True)
        await asyncio.sleep(INTERVAL_SECONDS)


async def inyectar_secuencia(productor):
    indice = int(os.environ["MENSAJE"])
    await enviar(productor, SECUENCIA[indice - 1], "replay")


async def demostrar_decisiones(conn, productor):
    for evento in SECUENCIA:
        await publicar_si_procede(conn, productor, evento, "replay")


async def prueba_pais(productor):
    ahora = int(datetime.now(timezone.utc).timestamp() * 1000)
    casos = [
        ("prueba-esp", [-3.7, 40.4, -1.2], 4.1, "Punto de prueba en España, no es un sismo real"),
        ("prueba-mar", [-30, 25, 8], None, "Punto de prueba en el océano, no es un sismo real"),
        ("prueba-malo", [-3.7, 145, 5], 2.0, "Punto de prueba con latitud imposible, no es un sismo real"),
    ]
    for indice, (identificador, coordenadas, magnitud, lugar) in enumerate(casos):
        evento = {
            "type": "Feature",
            "id": identificador,
            "geometry": {"type": "Point", "coordinates": coordenadas},
            "properties": {
                "type": "earthquake",
                "mag": magnitud,
                "magType": "ml",
                "place": lugar,
                "time": ahora,
                "updated": ahora + indice,
            },
        }
        await enviar(productor, evento, "replay")


async def main():
    await asegurar_topic()
    conn = await conectar_postgres()
    productor = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP, acks="all")
    await productor.start()
    try:
        if MODE == "inyectar":
            await inyectar_secuencia(productor)
        elif MODE == "decidir":
            await demostrar_decisiones(conn, productor)
        elif MODE == "live":
            await bucle_vivo(conn, productor)
        elif MODE == "prueba-pais":
            await prueba_pais(productor)
        else:
            raise SystemExit(f"MODE no reconocido: {MODE}")
    finally:
        await productor.stop()
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
