"""Consumidor. Valida el mensaje, lo guarda y solo entonces confirma el offset."""

import asyncio
import json
import math
import os
from datetime import datetime, timezone

import asyncpg
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.admin import AIOKafkaAdminClient, NewTopic

from paises import asignar_pais, cargar_catalogo

BOOTSTRAP = os.environ["KAFKA_BOOTSTRAP"]
TOPIC = os.environ["KAFKA_TOPIC"]
TOPIC_REPLAY = os.environ.get("KAFKA_TOPIC_REPLAY", "eventos-replay")
GROUP = os.environ.get("KAFKA_GROUP", "observatorio-consumidor")
PAISES_GEOJSON = os.environ.get("PAISES_GEOJSON", "/datos/paises.geojson")
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]


def finito(valor):
    return isinstance(valor, (int, float)) and math.isfinite(valor) and not isinstance(valor, bool)


def instante(milisegundos):
    return datetime.fromtimestamp(milisegundos / 1000, tz=timezone.utc)


async def guardar(pool, cuerpo, paises):
    try:
        mensaje = json.loads(cuerpo)
    except json.JSONDecodeError:
        await poner_cuarentena(pool, "JSON ilegible", {"raw": cuerpo, "marca": "rechazo"})
        return None
    esquema = "replay" if isinstance(mensaje, dict) and mensaje.get("mode") == "replay" else "public"
    evento = mensaje.get("event")
    if not isinstance(evento, dict):
        await poner_cuarentena(pool, "el mensaje no trae un evento", mensaje if isinstance(mensaje, dict) else {"raw": cuerpo}, esquema)
        return None
    geometria = evento.get("geometry") or {}
    coordenadas = geometria.get("coordinates") or []
    propiedades = evento.get("properties") or {}
    if propiedades.get("type") != "earthquake":
        await poner_cuarentena(pool, f"tipo distinto de earthquake: {propiedades.get('type')}", evento, esquema)
        return None
    motivo = validar_geometria(geometria, coordenadas)
    if motivo:
        await poner_cuarentena(pool, motivo, evento, esquema)
        return None
    lon, lat = coordenadas[0], coordenadas[1]
    profundidad = coordenadas[2] if len(coordenadas) > 2 else None
    magnitud = propiedades.get("mag")
    if magnitud is not None and not finito(magnitud):
        await poner_cuarentena(pool, "la magnitud no es finita", evento, esquema)
        return None
    try:
        time_ms = int(propiedades["time"])
        updated_ms = int(propiedades["updated"])
        ocurrencia = instante(time_ms)
        revision = instante(updated_ms)
        ingesta = datetime.fromisoformat(mensaje["ingested_at"])
    except (KeyError, TypeError, ValueError, OSError):
        await poner_cuarentena(pool, "fechas o identificadores ilegibles", evento, esquema)
        return None
    country_id = asignar_pais(paises, lon, lat)
    esquema = "replay" if mensaje.get("mode") == "replay" else "public"
    reproduccion = mensaje.get("reproduced_at")
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                f"INSERT INTO {esquema}.fecha (fecha_id) VALUES ($1) ON CONFLICT DO NOTHING",
                ocurrencia.date(),
            )
            await conn.execute(
                f"""
                INSERT INTO {esquema}.evento_version (event_id, updated_ms, original, ingested_at)
                VALUES ($1, $2, $3::jsonb, $4)
                ON CONFLICT (event_id, updated_ms) DO NOTHING
                """,
                evento["id"],
                updated_ms,
                json.dumps(evento),
                ingesta,
            )
            if esquema == "replay":
                await conn.execute(
                    """
                    INSERT INTO replay.evento_actual (
                        event_id, mag, mag_type, place, depth_km, lon, lat,
                        time_ms, updated_ms, occurred_at, updated_at, ingested_at, reproduced_at,
                        fecha_id, country_id, source, mode
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12, $13,
                        $14, $15, $16, $17
                    )
                    ON CONFLICT (event_id) DO UPDATE SET
                        mag = EXCLUDED.mag,
                        mag_type = EXCLUDED.mag_type,
                        place = EXCLUDED.place,
                        depth_km = EXCLUDED.depth_km,
                        lon = EXCLUDED.lon,
                        lat = EXCLUDED.lat,
                        time_ms = EXCLUDED.time_ms,
                        updated_ms = EXCLUDED.updated_ms,
                        occurred_at = EXCLUDED.occurred_at,
                        updated_at = EXCLUDED.updated_at,
                        ingested_at = EXCLUDED.ingested_at,
                        reproduced_at = EXCLUDED.reproduced_at,
                        fecha_id = EXCLUDED.fecha_id,
                        country_id = EXCLUDED.country_id,
                        source = EXCLUDED.source,
                        mode = EXCLUDED.mode
                    WHERE replay.evento_actual.updated_ms < EXCLUDED.updated_ms
                    """,
                    evento["id"],
                    magnitud,
                    propiedades.get("magType"),
                    propiedades.get("place"),
                    profundidad,
                    lon,
                    lat,
                    time_ms,
                    updated_ms,
                    ocurrencia,
                    revision,
                    ingesta,
                    datetime.fromisoformat(reproduccion) if reproduccion else datetime.now(timezone.utc),
                    ocurrencia.date(),
                    country_id,
                    mensaje.get("source") or "desconocido",
                    "replay",
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO evento_actual (
                        event_id, mag, mag_type, place, depth_km, lon, lat,
                        time_ms, updated_ms, occurred_at, updated_at, ingested_at,
                        fecha_id, country_id, source, mode
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12,
                        $13, $14, $15, $16
                    )
                    ON CONFLICT (event_id) DO UPDATE SET
                        mag = EXCLUDED.mag,
                        mag_type = EXCLUDED.mag_type,
                        place = EXCLUDED.place,
                        depth_km = EXCLUDED.depth_km,
                        lon = EXCLUDED.lon,
                        lat = EXCLUDED.lat,
                        time_ms = EXCLUDED.time_ms,
                        updated_ms = EXCLUDED.updated_ms,
                        occurred_at = EXCLUDED.occurred_at,
                        updated_at = EXCLUDED.updated_at,
                        ingested_at = EXCLUDED.ingested_at,
                        fecha_id = EXCLUDED.fecha_id,
                        country_id = EXCLUDED.country_id,
                        source = EXCLUDED.source,
                        mode = EXCLUDED.mode
                    WHERE evento_actual.updated_ms < EXCLUDED.updated_ms
                    """,
                    evento["id"],
                    magnitud,
                    propiedades.get("magType"),
                    propiedades.get("place"),
                    profundidad,
                    lon,
                    lat,
                    time_ms,
                    updated_ms,
                    ocurrencia,
                    revision,
                    ingesta,
                    ocurrencia.date(),
                    country_id,
                    mensaje.get("source") or "desconocido",
                    mensaje.get("mode") or "live",
                )
    return country_id


def validar_geometria(geometria, coordenadas):
    if geometria.get("type") != "Point" or len(coordenadas) < 2:
        return "se esperaba una geometría Point"
    lon, lat = coordenadas[0], coordenadas[1]
    profundidad = coordenadas[2] if len(coordenadas) > 2 else None
    if not finito(lon) or not finito(lat) or abs(lon) > 180 or abs(lat) > 90:
        return "coordenadas fuera de rango o no finitas"
    if profundidad is not None and not finito(profundidad):
        return "la profundidad no es finita"
    return None


async def poner_cuarentena(pool, motivo, original, esquema="public"):
    tabla = "replay.cuarentena" if esquema == "replay" else "cuarentena"
    async with pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO {tabla} (motivo, original, ingested_at) VALUES ($1, $2::jsonb, $3)",
            motivo,
            json.dumps(original),
            datetime.now(timezone.utc),
        )
    print(f"Cuarentena: {motivo}", flush=True)


async def preparar_catalogo(pool):
    paises = cargar_catalogo(PAISES_GEOJSON)
    async with pool.acquire() as conn:
        cantidad = await conn.fetchval("SELECT count(*) FROM pais")
        if cantidad == 0:
            await conn.executemany(
                """
                INSERT INTO pais (country_id, name_es, admin_name, continent, subregion)
                VALUES ($1, $2, $3, $4, $5)
                """,
                [
                    (pais["country_id"], pais["name_es"], pais["admin_name"], pais["continent"], pais["subregion"])
                    for pais in paises
                ],
            )
        filas = await conn.fetch("SELECT event_id, lon, lat FROM evento_actual WHERE country_id IS NULL AND mode = 'live'")
    asignados = 0
    for fila in filas:
        country_id = asignar_pais(paises, fila["lon"], fila["lat"])
        if country_id is None:
            continue
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE evento_actual SET country_id = $2 WHERE event_id = $1 AND country_id IS NULL",
                fila["event_id"],
                country_id,
            )
        asignados += 1
    print(
        f"Transformación de país: {asignados} eventos vivos recibieron country_id; "
        f"{len(filas) - asignados} siguen sin polígono.",
        flush=True,
    )
    return paises


async def conectar_postgres():
    espera = 1
    for intento in range(1, 16):
        try:
            return await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                min_size=1,
                max_size=2,
            )
        except Exception as exc:
            print(f"PostgreSQL no está listo (intento {intento}): {exc}", flush=True)
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
    raise SystemExit("No se pudo conectar con PostgreSQL")


async def leer(pool, paises):
    espera = 1
    consumidor = None
    for intento in range(1, 16):
        consumidor = AIOKafkaConsumer(
            TOPIC,
            TOPIC_REPLAY,
            bootstrap_servers=BOOTSTRAP,
            group_id=GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        try:
            await consumidor.start()
            break
        except Exception as exc:
            print(f"Kafka no está listo (intento {intento}): {exc}", flush=True)
            try:
                await consumidor.stop()
            except Exception:
                pass
            consumidor = None
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
    if consumidor is None:
        raise SystemExit("No se pudo conectar con Kafka")
    print(f"Leyendo {TOPIC} y {TOPIC_REPLAY}. El offset se confirma después de la transacción.", flush=True)
    try:
        async for mensaje in consumidor:
            try:
                texto = mensaje.value.decode("utf-8")
            except UnicodeDecodeError:
                await poner_cuarentena(pool, "el mensaje no es UTF-8", {"raw": mensaje.value.hex(), "marca": "rechazo"})
                pais = None
            else:
                pais = await guardar(pool, texto, paises)
            print(f"Transaccion confirmada: offset={mensaje.offset} pais={pais}", flush=True)
            pausa = int(os.environ.get("PAUSA_ANTES_COMMIT", "0"))
            if pausa:
                print(f"Pausa antes de confirmar el offset: {pausa}s", flush=True)
                await asyncio.sleep(pausa)
            particion = TopicPartition(mensaje.topic, mensaje.partition)
            await consumidor.commit({particion: mensaje.offset + 1})
            print(f"Offset confirmado: {mensaje.offset}", flush=True)
    finally:
        await consumidor.stop()


async def asegurar_topics():
    espera = 1
    for intento in range(1, 16):
        admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
        try:
            await admin.start()
            temas = await admin.list_topics()
            nuevos = [NewTopic(nombre, num_partitions=1, replication_factor=1) for nombre in (TOPIC, TOPIC_REPLAY) if nombre not in temas]
            if nuevos:
                await admin.create_topics(nuevos)
            await admin.close()
            return
        except Exception as exc:
            print(f"No se pudieron preparar los topics (intento {intento}): {exc}", flush=True)
            try:
                await admin.close()
            except Exception:
                pass
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)
    raise SystemExit("No se pudieron preparar los topics")


async def main():
    pool = await conectar_postgres()
    try:
        paises = await preparar_catalogo(pool)
        await asegurar_topics()
        await leer(pool, paises)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
