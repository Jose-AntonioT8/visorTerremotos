"""Asignación de país por punto dentro de polígono. WGS84, sin usar el texto place.

Natural Earth 1:110m generaliza la costa y la deja tierra adentro. Se amplía solo
el borde marítimo, 25 km hacia el agua. Donde el margen chocaría con otro país
o con su propio margen, se recorta: la frontera terrestre no se mueve.
"""

import json
import math

from shapely.geometry import MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.ops import transform, unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree
from shapely.validation import make_valid

# Hueco habitual de esta escala en costa abierta. No cubre mar abierto.
MARGEN_COSTA_M = 25_000
M_LON = 111_320.0
M_LAT = 110_540.0
MUNDO = box(-180, -90, 180, 90)


def _poligonos(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return [parte for parte in geom.geoms if not parte.is_empty]
    if geom.geom_type == "GeometryCollection":
        salida = []
        for parte in geom.geoms:
            salida.extend(_poligonos(parte))
        return salida
    return []


def _continuar_longitud(coords, origen=None):
    if not coords:
        return []
    desplazamiento = 0.0
    primero = coords[0][0]
    if origen is not None:
        while primero + desplazamiento - origen > 180:
            desplazamiento -= 360
        while origen - (primero + desplazamiento) > 180:
            desplazamiento += 360
    ajustadas = [(primero + desplazamiento, coords[0][1])]
    for anterior, actual in zip(coords, coords[1:]):
        salto = actual[0] + desplazamiento - ajustadas[-1][0]
        if salto > 180:
            desplazamiento -= 360
        elif salto < -180:
            desplazamiento += 360
        ajustadas.append((actual[0] + desplazamiento, actual[1]))
    return ajustadas


def _desenvolver(poligono):
    exterior = _continuar_longitud(list(poligono.exterior.coords))
    origen = exterior[0][0]
    huecos = [
        _continuar_longitud(list(hueco.coords), origen) for hueco in poligono.interiors
    ]
    return Polygon(exterior, huecos)


def _a_rango(geom):
    if geom.is_empty:
        return geom
    piezas = []
    for turno in (-360, 0, 360):
        movida = transform(lambda x, y, z=None, turno=turno: (x + turno, y), geom)
        recorte = movida.intersection(MUNDO)
        if not recorte.is_empty:
            piezas.append(recorte)
    return unary_union(piezas) if piezas else geom


def _como_area(geom):
    partes = _poligonos(make_valid(geom))
    if not partes:
        return Polygon()
    if len(partes) == 1:
        return partes[0]
    return MultiPolygon(partes)


def _buffer_exterior(poligono, metros):
    """Crece el contorno. Los lagos interiores se conservan."""
    desarrollado = _desenvolver(poligono)
    if desarrollado.is_empty or desarrollado.exterior.is_empty:
        return poligono
    centro = desarrollado.centroid
    latitud = poligono.representative_point().y
    coseno = math.cos(math.radians(min(89.0, max(-89.0, latitud))))
    coseno = max(coseno, 0.05)
    cx, cy = centro.x, centro.y

    def a_metros(x, y, z=None):
        return ((x - cx) * M_LON * coseno, (y - cy) * M_LAT)

    def a_grados(x, y, z=None):
        return (x / (M_LON * coseno) + cx, y / M_LAT + cy)

    crecido = transform(a_metros, Polygon(desarrollado.exterior.coords)).buffer(metros, resolution=4)
    crecido = _a_rango(transform(a_grados, crecido))
    if poligono.interiors:
        lagos = unary_union([Polygon(list(hueco.coords)) for hueco in poligono.interiors])
        crecido = crecido.difference(lagos)
    return crecido


def _buffer_geom(geom, metros):
    partes = [_buffer_exterior(parte, metros) for parte in _poligonos(geom)]
    if not partes:
        return geom
    return unary_union(partes)


def ajustar_costas(geometrias, metros=MARGEN_COSTA_M):
    limpias = []
    for geom in geometrias:
        partes = _poligonos(make_valid(geom))
        limpias.append(unary_union(partes) if partes else Polygon())
    tierra = unary_union([geom for geom in limpias if not geom.is_empty])
    buffers = [_buffer_geom(geom, metros) for geom in limpias]
    arbol = STRtree(buffers)
    ajustadas = []
    for indice, geom in enumerate(limpias):
        if geom.is_empty:
            ajustadas.append(geom)
            continue
        vecinos = [
            buffers[int(otro)]
            for otro in arbol.query(buffers[indice], predicate="intersects")
            if int(otro) != indice
        ]
        oceano = buffers[indice].difference(tierra)
        if vecinos:
            oceano = oceano.difference(unary_union(vecinos).difference(tierra))
        ajustadas.append(_como_area(unary_union([geom, oceano])))
    return ajustadas


def _redondear(valor):
    if isinstance(valor, float):
        return round(valor, 5)
    if isinstance(valor, list):
        return [_redondear(parte) for parte in valor]
    if isinstance(valor, dict):
        return {clave: _redondear(parte) for clave, parte in valor.items()}
    return valor


def escribir_ajustado(origen, destino):
    with open(origen, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    ajustadas = ajustar_costas([shape(feature["geometry"]) for feature in datos["features"]])
    for feature, geom in zip(datos["features"], ajustadas):
        feature["geometry"] = _redondear(mapping(geom))
    with open(destino, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, separators=(",", ":"))


def cargar_catalogo(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    crudas = []
    metadatos = []
    for feature in datos["features"]:
        propiedades = feature["properties"]
        geom = shape(feature["geometry"])
        crudas.append(geom)
        metadatos.append(
            {
                "country_id": propiedades["ADM0_A3"],
                "name_es": propiedades.get("NAME_ES"),
                "admin_name": propiedades.get("ADMIN"),
                "continent": propiedades.get("CONTINENT"),
                "subregion": propiedades.get("SUBREGION"),
                "area": geom.area,
            }
        )
    if len(metadatos) != len({pais["country_id"] for pais in metadatos}):
        raise SystemExit("ADM0_A3 no es único en el catálogo")
    paises = []
    for metadato, geom in zip(metadatos, ajustar_costas(crudas)):
        paises.append({**metadato, "preparada": prep(geom)})
    return paises


def asignar_pais(paises, lon, lat):
    """Usa covers sobre la costa ampliada. Si hay varias coincidencias, gana el de menor área original."""
    punto = Point(lon, lat)
    coincidencias = [pais for pais in paises if pais["preparada"].covers(punto)]
    if not coincidencias:
        return None
    coincidencias.sort(key=lambda pais: (pais["area"], pais["country_id"]))
    return coincidencias[0]["country_id"]
