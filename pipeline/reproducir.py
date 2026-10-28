"""Publica en eventos-replay una selección de 2025, un duplicado y una revisión.

No escribe en las tablas en vivo. El consumidor guarda estos mensajes en el esquema replay.
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import asyncpg
from aiokafka import AIOKafkaProducer

BOOTSTRAP = os.environ["KAFKA_BOOTSTRAP"]
TOPIC = os.environ.get("KAFKA_TOPIC_REPLAY", "eventos-replay")
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
PAUSA = float(os.environ.get("REPLAY_PAUSA", "2"))


def como_dict(valor):
    return json.loads(valor) if isinstance(valor, str) else valor


def mensaje(feature, reproduced_at, updated=None, magnitud=None):
    evento = json.loads(json.dumps(feature))
    if updated is not None:
        evento["properties"]["updated"] = updated
    if magnitud is not None:
        evento["properties"]["mag"] = magnitud
    return {
        "source": "usgs",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "reproduced_at": reproduced_at,
        "mode": "replay",
        "event": evento,
    }


async def publicar(productor, cuerpo):
    evento = cuerpo["event"]
    meta = await productor.send_and_wait(
        TOPIC,
        json.dumps(cuerpo).encode("utf-8"),
        key=evento["id"].encode("utf-8"),
    )
    print(
        f"replay id={evento['id']} time={evento['properties']['time']} "
        f"updated={evento['properties']['updated']} mag={evento['properties'].get('mag')} offset={meta.offset}",
        flush=True,
    )
    await asyncio.sleep(PAUSA)


async def main():
    conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    filas = await conn.fetch(
        """
        SELECT event_id, mag, original
        FROM (
            SELECT e.event_id, e.mag, v.original,
                   row_number() OVER (ORDER BY e.occurred_at) AS orden
            FROM evento_actual e
            JOIN evento_version v ON v.event_id = e.event_id AND v.updated_ms = e.updated_ms
            WHERE e.mode = 'live' AND e.occurred_at >= '2025-01-01' AND e.occurred_at < '2025-01-03'
              AND e.mag IS NOT NULL
        ) seleccion
        WHERE orden <= 8
        ORDER BY orden
        """
    )
    await conn.close()
    if len(filas) < 2:
        raise SystemExit("No hay suficientes eventos de 2025 para reproducir")
    productor = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP, acks="all")
    await productor.start()
    try:
        primero = como_dict(filas[0]["original"])
        reproduccion = datetime.now(timezone.utc).isoformat()
        for fila in filas:
            await publicar(productor, mensaje(como_dict(fila["original"]), reproduccion))
        await publicar(productor, mensaje(primero, reproduccion))
        revision = int(primero["properties"]["updated"]) + 60_000
        await publicar(productor, mensaje(primero, reproduccion, updated=revision, magnitud=round(float(primero["properties"]["mag"]) + 0.2, 2)))
    finally:
        await productor.stop()
    print(f"Reproducción enviada: {len(filas)} eventos, 1 duplicado y 1 revisión de {primero['id']}.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
