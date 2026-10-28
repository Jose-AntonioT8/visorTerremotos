"""Asignación de país por punto dentro de polígono. WGS84, sin usar el texto place."""

import json

from shapely.geometry import Point, shape
from shapely.prepared import prep


def cargar_catalogo(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    paises = []
    codigos = []
    for feature in datos["features"]:
        propiedades = feature["properties"]
        codigo = propiedades["ADM0_A3"]
        codigos.append(codigo)
        geometria = shape(feature["geometry"])
        paises.append(
            {
                "country_id": codigo,
                "name_es": propiedades.get("NAME_ES"),
                "admin_name": propiedades.get("ADMIN"),
                "continent": propiedades.get("CONTINENT"),
                "subregion": propiedades.get("SUBREGION"),
                "preparada": prep(geometria),
                "area": geometria.area,
            }
        )
    if len(codigos) != len(set(codigos)):
        raise SystemExit("ADM0_A3 no es único en el catálogo")
    return paises


def asignar_pais(paises, lon, lat):
    """Usa covers. Si hay varias coincidencias, gana el polígono de menor área."""
    punto = Point(lon, lat)
    coincidencias = [pais for pais in paises if pais["preparada"].covers(punto)]
    if not coincidencias:
        return None
    coincidencias.sort(key=lambda pais: (pais["area"], pais["country_id"]))
    return coincidencias[0]["country_id"]
