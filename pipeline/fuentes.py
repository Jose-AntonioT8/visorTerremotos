"""Lectura aditiva de feeds públicos IGN, USGS y EMSC.

Normaliza a GeoJSON FeatureCollection compatible con el mapa.
No sustituye a /api/eventos ni al productor: solo expone lecturas en vivo.
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

USER_AGENT = "observatorio-sismico"
URLS = {
    "usgs": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "emsc": "https://www.seismicportal.eu/fdsnws/event/1/query?limit=500&format=json",
    "ign": "https://www.ign.es/ign/RssTools/sismologia.xml",
}


def finito(valor):
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return numero


def a_milis(valor):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return int(valor) if math.isfinite(valor) else None
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return int(datetime.fromisoformat(texto).timestamp() * 1000)
    except ValueError:
        for formato in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                momento = datetime.strptime(texto, formato).replace(tzinfo=timezone.utc)
                return int(momento.timestamp() * 1000)
            except ValueError:
                continue
    return None


def feature_comun(identificador, lon, lat, depth, mag, place, time_ms, updated_ms, fuente, mag_type=None):
    lon_n = finito(lon)
    lat_n = finito(lat)
    depth_n = finito(depth)
    if depth_n is not None:
        depth_n = abs(depth_n)
    props = {
        "mag": finito(mag),
        "magType": mag_type,
        "place": place or "Sin descripción",
        "time": time_ms,
        "updated": updated_ms if updated_ms is not None else time_ms,
        "type": "earthquake",
        "source": fuente,
    }
    return {
        "type": "Feature",
        "id": identificador,
        "geometry": {
            "type": "Point",
            "coordinates": [lon_n, lat_n, depth_n],
        },
        "properties": props,
    }


def coleccion(features, fuente, url):
    ahora = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": ahora,
            "count": len(features),
            "source": fuente,
            "url": url,
        },
        "features": features,
    }


def descargar(url: str) -> tuple[int, bytes, str | None]:
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        return respuesta.status, respuesta.read(), respuesta.headers.get_content_type()


def normalizar_usgs(payload: dict, url: str):
    features = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        if props.get("type") and props.get("type") != "earthquake":
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or [None, None, None]
        features.append(
            feature_comun(
                feature.get("id") or props.get("code") or f"usgs-{len(features)}",
                coords[0] if len(coords) > 0 else None,
                coords[1] if len(coords) > 1 else None,
                coords[2] if len(coords) > 2 else None,
                props.get("mag"),
                props.get("place") or props.get("title"),
                a_milis(props.get("time")),
                a_milis(props.get("updated")),
                "usgs",
                props.get("magType"),
            )
        )
    return coleccion(features, "usgs", url)


def normalizar_emsc(payload: dict, url: str):
    features = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        lon = props.get("lon")
        lat = props.get("lat")
        depth = props.get("depth")
        if lon is None and len(coords) > 0:
            lon = coords[0]
        if lat is None and len(coords) > 1:
            lat = coords[1]
        if depth is None and len(coords) > 2:
            depth = coords[2]
        features.append(
            feature_comun(
                feature.get("id") or props.get("unid") or f"emsc-{len(features)}",
                lon,
                lat,
                depth,
                props.get("mag"),
                props.get("flynn_region") or props.get("place"),
                a_milis(props.get("time")),
                a_milis(props.get("lastupdate")),
                "emsc",
                props.get("magtype") or props.get("magType"),
            )
        )
    return coleccion(features, "emsc", url)


def _texto(nodo, *rutas):
    for ruta in rutas:
        hallado = nodo.find(ruta)
        if hallado is not None and hallado.text:
            return hallado.text.strip()
    return None


def normalizar_ign_rss(cuerpo: bytes, url: str):
    raiz = ET.fromstring(cuerpo)
    features = []
    for item in raiz.findall("./channel/item"):
        descripcion = _texto(item, "description") or ""
        lat = _texto(item, "{http://www.w3.org/2003/01/geo/wgs84_pos#}lat", "geo:lat")
        lon = _texto(item, "{http://www.w3.org/2003/01/geo/wgs84_pos#}long", "geo:long")
        if lat is None or lon is None:
            coords = re.search(r"localización:\s*([-\d.]+)\s*,\s*([-\d.]+)", descripcion, re.I)
            if coords:
                lat, lon = coords.group(1), coords.group(2)
        mag_m = re.search(r"magnitud\s+([-\d.]+)", descripcion, re.I)
        lugar_m = re.search(r"magnitud\s+[-\d.]+\s+en\s+(.+?)\s+en la fecha", descripcion, re.I)
        fecha_m = re.search(r"fecha\s+(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})", descripcion, re.I)
        enlace = _texto(item, "guid", "link") or ""
        evid = None
        evid_m = re.search(r"evid=([A-Za-z0-9_-]+)", enlace)
        if evid_m:
            evid = evid_m.group(1)
        time_ms = a_milis(fecha_m.group(1) if fecha_m else None)
        features.append(
            feature_comun(
                evid or f"ign-{len(features)}",
                lon,
                lat,
                None,
                mag_m.group(1) if mag_m else None,
                (lugar_m.group(1).strip() if lugar_m else None) or _texto(item, "title"),
                time_ms,
                time_ms,
                "ign",
                None,
            )
        )
    return coleccion(features, "ign", url)


def leer_fuente(fuente: str):
    if fuente not in URLS:
        raise KeyError(fuente)
    url = URLS[fuente]
    estado, cuerpo, _ = descargar(url)
    if estado >= 400:
        raise RuntimeError(f"HTTP {estado} al consultar {fuente}")
    if fuente == "ign":
        return normalizar_ign_rss(cuerpo, url)
    payload = json.loads(cuerpo.decode("utf-8"))
    if fuente == "usgs":
        return normalizar_usgs(payload, url)
    return normalizar_emsc(payload, url)
