"""Descarga el catálogo USGS de 2025 y lo guarda con las mismas reglas del consumidor.

No publica en Kafka: llama a guardar(), que valida, asigna país y respeta las versiones.
Los GeoJSON quedan en /datos/raw/historico, fuera de Git.
"""

import asyncio
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from consumidor import conectar_postgres, guardar, preparar_catalogo

SALIDA = Path("/datos/raw/historico")
BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
TOPE = 20000


def url_de(inicio, fin):
    return (
        f"{BASE}?format=geojson&starttime={inicio.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&endtime={fin.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&minmagnitude=4&eventtype=earthquake&orderby=time-asc"
    )


async def leer_url(url):
    espera = 2
    for intento in range(1, 6):
        try:
            def leer():
                peticion = urllib.request.Request(url, headers={"User-Agent": "observatorio-sismico"})
                with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                    return respuesta.status, respuesta.read()

            estado, cuerpo = await asyncio.to_thread(leer)
            if estado == 429 or estado >= 500:
                raise RuntimeError(f"HTTP {estado}")
            return json.loads(cuerpo)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            print(f"Reintento {intento} de {url}: {exc}", flush=True)
            await asyncio.sleep(espera)
            espera = min(espera * 2, 60)
    raise SystemExit(f"No se pudo descargar {url}")


async def registrar(conn, url, inicio, fin, cantidad, resultado):
    await conn.execute(
        """
        INSERT INTO consulta_fuente (consulted_at, url, intervalo, record_count, resultado)
        VALUES ($1, $2, $3, $4, $5)
        """,
        datetime.now(timezone.utc),
        url,
        f"{inicio.isoformat()} / {fin.isoformat()}",
        cantidad,
        resultado,
    )


async def intervalo(conn, inicio, fin, profundidad=0):
    if profundidad > 12:
        raise SystemExit(f"El intervalo sigue en el tope: {inicio} {fin}")
    destino = SALIDA / f"{inicio.strftime('%Y%m%dT%H%M%SZ')}_{fin.strftime('%Y%m%dT%H%M%SZ')}.geojson"
    url = url_de(inicio, fin)
    if destino.exists():
        datos = json.loads(destino.read_text(encoding="utf-8"))
        print(f"Ya descargado {destino.name}: {len(datos.get('features') or [])}", flush=True)
        return datos.get("features") or []
    datos = await leer_url(url)
    features = datos.get("features") or []
    await registrar(conn, url, inicio, fin, len(features), "ok" if len(features) < TOPE else "tope")
    if len(features) >= TOPE:
        print(f"Tope de {TOPE} en {inicio.isoformat()} / {fin.isoformat()}. Se divide.", flush=True)
        medio = inicio + (fin - inicio) / 2
        primera = await intervalo(conn, inicio, medio, profundidad + 1)
        segunda = await intervalo(conn, medio, fin, profundidad + 1)
        return primera + segunda
    destino.write_text(json.dumps(datos), encoding="utf-8")
    print(f"Guardado {destino.name}: {len(features)}", flush=True)
    return features


def quedarse_con_la_revision(features):
    por_id = {}
    for feature in features:
        identificador = feature.get("id")
        updated = ((feature.get("properties") or {}).get("updated")) or 0
        anterior = por_id.get(identificador)
        if anterior is None or updated > (((anterior.get("properties") or {}).get("updated")) or 0):
            por_id[identificador] = feature
    return list(por_id.values())


async def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    pool = await conectar_postgres()
    try:
        paises = await preparar_catalogo(pool)
        features = []
        async with pool.acquire() as conn:
            inicio = datetime(2025, 1, 1, tzinfo=timezone.utc)
            fin_anio = datetime(2026, 1, 1, tzinfo=timezone.utc)
            while inicio < fin_anio:
                mes = (inicio.month % 12) + 1
                anio = inicio.year + (1 if inicio.month == 12 else 0)
                fin = datetime(anio, mes, 1, tzinfo=timezone.utc)
                features.extend(await intervalo(conn, inicio, fin))
                inicio = fin
        unicos = quedarse_con_la_revision(features)
        print(f"Features descargadas {len(features)}. Tras deduplicar por id: {len(unicos)}.", flush=True)
        ahora = datetime.now(timezone.utc).isoformat()
        for indice, feature in enumerate(unicos, start=1):
            mensaje = {
                "source": "usgs",
                "ingested_at": ahora,
                "mode": "live",
                "event": feature,
            }
            await guardar(pool, json.dumps(mensaje), paises)
            if indice % 500 == 0:
                print(f"Cargados {indice} de {len(unicos)}", flush=True)
        print(f"Carga histórica terminada: {len(unicos)}", flush=True)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
