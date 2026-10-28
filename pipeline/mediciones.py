"""Mide tres operaciones con datos sintéticos. No escribe en evento_actual."""

import asyncio
import json
import os
import random
import time
import tracemalloc
from datetime import datetime, timedelta, timezone

import asyncpg

from paises import asignar_pais, cargar_catalogo

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
PAISES = os.environ.get("PAISES_GEOJSON", "/datos/paises.geojson")


def preparar(tamano):
    claves = [f"id-{indice}" for indice in range(tamano)]
    versiones = [(clave, indice) for indice, clave in enumerate(claves)]
    indice = {clave: valor for clave, valor in versiones}
    consultas = [f"id-{random.randrange(tamano)}" for _ in range(200)]
    return versiones, indice, consultas


def medir_busqueda():
    print("\n# busqueda de la ultima version, 200 consultas, datos sinteticos", flush=True)
    for tamano in (1000, 10000, 100000):
        tracemalloc.start()
        versiones, indice, consultas = preparar(tamano)
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        inicio = time.perf_counter()
        for clave in consultas:
            for candidata, _valor in versiones:
                if candidata == clave:
                    break
        secuencial = time.perf_counter() - inicio
        inicio = time.perf_counter()
        for clave in consultas:
            indice[clave]
        diccionario = time.perf_counter() - inicio
        print(
            f"{tamano}\tsecuencial={secuencial:.4f}s\tdiccionario={diccionario:.4f}s\tmemoria_estructura={pico / 1_048_576:.2f} MiB",
            flush=True,
        )


def poligono(catalogo):
    def ejecutar(tamano):
        puntos = [(random.uniform(-180, 180), random.uniform(-90, 90)) for _ in range(tamano)]
        for lon, lat in puntos:
            asignar_pais(catalogo, lon, lat)

    return ejecutar


async def ventanas():
    conn = await asyncpg.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, database=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
    )
    print("\n# agregacion por hora, datos sinteticos", flush=True)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for tamano in (1000, 10000, 50000):
        await conn.execute("DROP TABLE IF EXISTS medicion_ventana")
        await conn.execute("CREATE TABLE medicion_ventana (id int, occurred_at timestamptz)")
        await conn.executemany(
            "INSERT INTO medicion_ventana (id, occurred_at) VALUES ($1, $2)",
            [(indice, base + timedelta(minutes=indice % (24 * 60))) for indice in range(tamano)],
        )
        sin = await conn.fetchval("EXPLAIN (ANALYZE, FORMAT JSON) SELECT date_trunc('hour', occurred_at), count(*) FROM medicion_ventana GROUP BY 1")
        await conn.execute("CREATE INDEX medicion_ventana_idx ON medicion_ventana (occurred_at)")
        await conn.execute("ANALYZE medicion_ventana")
        con = await conn.fetchval("EXPLAIN (ANALYZE, FORMAT JSON) SELECT date_trunc('hour', occurred_at), count(*) FROM medicion_ventana GROUP BY 1")
        busqueda_sin = await conn.fetchval("EXPLAIN (ANALYZE, FORMAT JSON) SELECT * FROM medicion_ventana WHERE occurred_at = $1", base)
        await conn.execute("DROP INDEX medicion_ventana_idx")
        # The lookup above used the index. Repeat it after dropping the index.
        busqueda_lineal = await conn.fetchval("EXPLAIN (ANALYZE, FORMAT JSON) SELECT * FROM medicion_ventana WHERE occurred_at = $1", base)
        def plan(valor):
            if isinstance(valor, str):
                valor = json.loads(valor)
            return valor[0]

        sin_plan = plan(sin)
        con_plan = plan(con)
        busqueda_plan = plan(busqueda_sin)
        lineal_plan = plan(busqueda_lineal)
        print(
            f"{tamano}\tagregacion_sin_indice_ms={sin_plan['Execution Time']:.3f}"
            f"\tagregacion_con_indice_ms={con_plan['Execution Time']:.3f}"
            f"\tplan_con={con_plan['Plan']['Node Type']}"
            f"\tbusqueda_con_indice_ms={busqueda_plan['Execution Time']:.3f}"
            f"\tplan_busqueda={busqueda_plan['Plan']['Node Type']}"
            f"\tbusqueda_sin_indice_ms={lineal_plan['Execution Time']:.3f}"
            f"\tplan_lineal={lineal_plan['Plan']['Node Type']}",
            flush=True,
        )
        await conn.execute("DROP TABLE medicion_ventana")
    await conn.close()


def medir(nombre, tamanos, funcion):
    print(f"\n# {nombre}", flush=True)
    for tamano in tamanos:
        tracemalloc.start()
        inicio = time.perf_counter()
        funcion(tamano)
        segundos = time.perf_counter() - inicio
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"{tamano}\t{segundos:.4f}s\t{pico / 1_048_576:.2f} MiB", flush=True)


def main():
    random.seed(2025)
    medir_busqueda()
    catalogo = cargar_catalogo(PAISES)
    medir("punto en poligono, catalogo real, puntos sinteticos", (200, 1000, 5000), poligono(catalogo))
    asyncio.run(ventanas())


if __name__ == "__main__":
    main()
