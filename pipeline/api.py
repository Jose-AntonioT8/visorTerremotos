"""API de consulta. Lee PostgreSQL y no llama a USGS ni a Kafka."""

import math
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
MAX_PUNTOS = int(os.environ.get("MAX_PUNTOS", "5000"))
ORIGENES = [
    origen.strip()
    for origen in os.environ.get("CORS_ORIGINS", "http://localhost:4200").split(",")
    if origen.strip()
]


@asynccontextmanager
async def vida(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        min_size=1,
        max_size=4,
    )
    yield
    await app.state.pool.close()


app = FastAPI(lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["ngrok-skip-browser-warning"],
)


def milis(momento):
    if momento is None:
        return None
    return int(momento.timestamp() * 1000)


def numero(valor):
    if valor is None:
        return None
    valor = float(valor)
    if not math.isfinite(valor):
        return None
    return valor


async def ultima_ingesta(conn):
    momento = await conn.fetchval(
        "SELECT max(consulted_at) FROM consulta_fuente WHERE resultado = 'ok'"
    )
    return milis(momento)


@app.exception_handler(asyncpg.PostgresError)
async def error_base(request: Request, exc: asyncpg.PostgresError):
    return JSONResponse(status_code=503, content={"error": "La base de datos no está disponible"})


@app.get("/api/salud")
async def salud():
    async with app.state.pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
        ingesta = await ultima_ingesta(conn)
    return {"estado": "ok", "last_ingestion": ingesta}


def normalizar(momento):
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def clausula(mode, start, end, min_mag, country_id, subregion):
    condiciones = ["e.mode = $1"]
    argumentos: list = [mode]
    if start is not None:
        argumentos.append(start)
        condiciones.append(f"e.occurred_at >= ${len(argumentos)}")
    if end is not None:
        argumentos.append(end)
        condiciones.append(f"e.occurred_at < ${len(argumentos)}")
    if min_mag is not None:
        argumentos.append(min_mag)
        condiciones.append(f"e.mag IS NOT NULL AND e.mag >= ${len(argumentos)}")
    if country_id == "sin-pais":
        condiciones.append("e.country_id IS NULL")
    elif country_id is not None:
        argumentos.append(country_id)
        condiciones.append(f"e.country_id = ${len(argumentos)}")
    if subregion is not None:
        argumentos.append(subregion)
        condiciones.append(
            "EXISTS (SELECT 1 FROM pais region "
            f"WHERE region.country_id = e.country_id AND region.subregion = ${len(argumentos)})"
        )
    return " AND ".join(condiciones), argumentos


def origen_eventos(mode):
    return "replay.evento_actual" if mode == "replay" else "evento_actual"


@app.get("/api/paises")
async def paises():
    async with app.state.pool.acquire() as conn:
        filas = await conn.fetch(
            "SELECT country_id, name_es, continent, subregion FROM pais ORDER BY name_es"
        )
    return [
        {
            "country_id": fila["country_id"],
            "name_es": fila["name_es"],
            "continent": fila["continent"],
            "subregion": fila["subregion"],
        }
        for fila in filas
    ]


@app.get("/api/eventos")
async def eventos(
    start: datetime | None = None,
    end: datetime | None = None,
    min_mag: float | None = None,
    country_id: str | None = None,
    subregion: str | None = None,
    mode: str = "live",
    offset: int = Query(default=0, ge=0),
):
    ahora = datetime.now(timezone.utc)
    start = normalizar(start)
    end = normalizar(end)
    if start is None and end is None and mode != "replay":
        start = ahora - timedelta(hours=24)
        end = ahora
    where, argumentos = clausula(mode, start, end, min_mag, country_id, subregion)
    origen = origen_eventos(mode)
    async with app.state.pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) FROM {origen} e WHERE {where}", *argumentos)
        filas = await conn.fetch(
            f"""
            SELECT e.event_id, e.mag, e.mag_type, e.place, e.depth_km, e.lon, e.lat,
                   e.time_ms, e.updated_ms, e.country_id, p.name_es
            FROM {origen} e
            LEFT JOIN pais p ON p.country_id = e.country_id
            WHERE {where}
            ORDER BY e.occurred_at
            LIMIT ${len(argumentos) + 1} OFFSET ${len(argumentos) + 2}
            """,
            *argumentos,
            MAX_PUNTOS,
            offset,
        )
        ingesta = await ultima_ingesta(conn)
    features = []
    for fila in filas:
        features.append(
            {
                "type": "Feature",
                "id": fila["event_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [numero(fila["lon"]), numero(fila["lat"]), numero(fila["depth_km"])],
                },
                "properties": {
                    "mag": numero(fila["mag"]),
                    "magType": fila["mag_type"],
                    "place": fila["place"],
                    "time": fila["time_ms"],
                    "updated": fila["updated_ms"],
                    "country_id": fila["country_id"],
                    "country_name": fila["name_es"],
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": milis(ahora),
            "last_ingestion": ingesta,
            "mode": mode,
            "count": total,
            "truncated": offset + len(features) < total,
            "limit": MAX_PUNTOS,
            "offset": offset,
        },
        "features": features,
    }


def tramo_magnitud(valor):
    if valor < 0:
        return "menor de 0"
    limite = int(valor)
    if limite >= 8:
        return "8 o más"
    return f"{limite} a {limite + 1}"


def tramo_profundidad(valor):
    if valor < 0:
        return "menor de 0 km"
    if valor < 70:
        return "0 a 70 km"
    if valor < 300:
        return "70 a 300 km"
    return "300 km o más"


@app.get("/api/estadisticas")
async def estadisticas(
    start: datetime | None = None,
    end: datetime | None = None,
    min_mag: float | None = None,
    country_id: str | None = None,
    subregion: str | None = None,
    mode: str = "live",
):
    ahora = datetime.now(timezone.utc)
    start = normalizar(start)
    end = normalizar(end)
    if start is None and end is None and mode != "replay":
        start = ahora - timedelta(hours=24)
        end = ahora
    where, argumentos = clausula(mode, start, end, min_mag, country_id, subregion)
    origen = origen_eventos(mode)
    corte = 4.0 if min_mag is None or min_mag < 4 else min_mag
    where_corte, args_corte = clausula(mode, None, None, corte, country_id, subregion)
    reciente_inicio = ahora - timedelta(hours=24)
    async with app.state.pool.acquire() as conn:
        resumen = await conn.fetchrow(
            f"""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE e.mag IS NULL) AS sin_magnitud,
                   count(*) FILTER (WHERE e.depth_km IS NULL) AS sin_profundidad,
                   count(*) FILTER (WHERE e.country_id IS NULL) AS sin_pais,
                   avg(e.mag) FILTER (WHERE e.mag IS NOT NULL) AS media_mag,
                   count(e.mag) AS con_magnitud,
                   avg(e.depth_km) FILTER (WHERE e.depth_km IS NOT NULL) AS media_prof,
                   count(e.depth_km) AS con_profundidad
            FROM {origen} e
            WHERE {where}
            """,
            *argumentos,
        )
        magnitudes = await conn.fetch(
            f"SELECT e.mag FROM {origen} e WHERE {where} AND e.mag IS NOT NULL",
            *argumentos,
        )
        profundidades = await conn.fetch(
            f"SELECT e.depth_km FROM {origen} e WHERE {where} AND e.depth_km IS NOT NULL",
            *argumentos,
        )
        ventanas = await conn.fetch(
            f"""
            SELECT date_trunc('hour', e.occurred_at AT TIME ZONE 'UTC') AS hora,
                   e.country_id, p.name_es, count(*) AS total
            FROM {origen} e
            LEFT JOIN pais p ON p.country_id = e.country_id
            WHERE {where}
            GROUP BY 1, 2, 3
            ORDER BY 1, 3
            """,
            *argumentos,
        )
        paises_filas = await conn.fetch(
            f"""
            SELECT e.country_id, p.name_es, count(*) AS total
            FROM {origen} e
            LEFT JOIN pais p ON p.country_id = e.country_id
            WHERE {where}
            GROUP BY 1, 2
            ORDER BY total DESC, 2
            """,
            *argumentos,
        )
        reciente = await conn.fetchval(
            f"""
            SELECT count(*) FROM {origen} e
            WHERE {where_corte} AND e.occurred_at >= ${len(args_corte) + 1} AND e.occurred_at < ${len(args_corte) + 2}
            """,
            *args_corte,
            reciente_inicio,
            ahora,
        )
        historico = await conn.fetchval(
            f"""
            SELECT count(*) FROM {origen} e
            WHERE {where_corte}
              AND e.occurred_at >= ${len(args_corte) + 1}
              AND e.occurred_at < ${len(args_corte) + 2}
            """,
            *args_corte,
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    tramos_mag: dict[str, int] = {}
    for fila in magnitudes:
        etiqueta = tramo_magnitud(fila["mag"])
        tramos_mag[etiqueta] = tramos_mag.get(etiqueta, 0) + 1
    tramos_prof: dict[str, int] = {}
    for fila in profundidades:
        etiqueta = tramo_profundidad(fila["depth_km"])
        tramos_prof[etiqueta] = tramos_prof.get(etiqueta, 0) + 1
    orden_prof = ["menor de 0 km", "0 a 70 km", "70 a 300 km", "300 km o más"]
    tramos_prof_lista = [
        {"etiqueta": clave, "total": tramos_prof[clave]} for clave in orden_prof if clave in tramos_prof
    ]
    def orden_mag(etiqueta):
        if etiqueta.startswith("menor"):
            return -1
        if etiqueta.startswith("8"):
            return 8
        return int(etiqueta.split(" ")[0])
    horas: dict[str, dict] = {}
    for fila in ventanas:
        inicio = fila["hora"].replace(tzinfo=timezone.utc)
        clave = inicio.isoformat()
        bloque = horas.setdefault(
            clave,
            {"inicio": inicio.isoformat(), "fin": (inicio + timedelta(hours=1)).isoformat(), "total": 0, "paises": []},
        )
        nombre = fila["name_es"] or "Sin país asignado"
        bloque["total"] += fila["total"]
        bloque["paises"].append(
            {"country_id": fila["country_id"], "nombre": nombre, "total": fila["total"]}
        )
    media = (historico or 0) / 365
    variacion = None if media == 0 else (reciente - media) / media * 100
    return {
        "periodo": {
            "start": None if start is None else start.isoformat(),
            "end": None if end is None else end.isoformat(),
            "unidad": "eventos aislados de la reproducción" if mode == "replay" else "eventos de evento_actual",
        },
        "filtros": {
            "min_mag": min_mag,
            "country_id": country_id,
            "subregion": subregion,
            "mode": mode,
        },
        "total": resumen["total"],
        "sin_valor": {
            "magnitud": resumen["sin_magnitud"],
            "profundidad": resumen["sin_profundidad"],
            "pais": resumen["sin_pais"],
        },
        "ventanas": list(horas.values()),
        "por_pais": [
            {
                "country_id": fila["country_id"],
                "nombre": fila["name_es"] or "Sin país asignado",
                "total": fila["total"],
            }
            for fila in paises_filas
        ],
        "magnitud": {
            "nulos": resumen["sin_magnitud"],
            "denominador": resumen["con_magnitud"],
            "media": numero(resumen["media_mag"]),
            "tramos": [
                {"etiqueta": clave, "total": tramos_mag[clave]}
                for clave in sorted(tramos_mag, key=orden_mag)
            ],
        },
        "profundidad": {
            "nulos": resumen["sin_profundidad"],
            "denominador": resumen["con_profundidad"],
            "media": numero(resumen["media_prof"]),
            "unidad": "km",
            "tramos": tramos_prof_lista,
        },
        "comparacion": None if mode == "replay" else {
            "reciente": {
                "inicio": reciente_inicio.isoformat(),
                "fin": ahora.isoformat(),
                "total": reciente,
                "etiqueta": "últimas 24 horas",
            },
            "historico": {
                "anio": 2025,
                "dias": 365,
                "total": historico,
                "media_diaria": media,
            },
            "corte_magnitud": corte,
            "corte_forzado_a_4": min_mag is None or min_mag < 4,
            "country_id": country_id,
            "subregion": subregion,
            "variacion_porcentual": variacion,
            "aviso": "El periodo reciente puede estar incompleto por retrasos de USGS.",
        },
    }

