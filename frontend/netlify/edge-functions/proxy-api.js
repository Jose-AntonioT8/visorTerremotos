const TUNEL = "https://whoops-botanical-humorist.ngrok-free.dev";

const FUENTES = {
  usgs: "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
  emsc: "https://www.seismicportal.eu/fdsnws/event/1/query?limit=500&format=json",
  ign: "https://www.ign.es/ign/RssTools/sismologia.xml",
};

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "access-control-allow-origin": "*",
};

function finito(valor) {
  const n = Number(valor);
  return Number.isFinite(n) ? n : null;
}

function aMilis(valor) {
  if (valor == null || valor === "") return null;
  if (typeof valor === "number" && Number.isFinite(valor)) return Math.trunc(valor);
  const texto = String(valor).trim();
  const iso = Date.parse(texto.includes("T") || texto.endsWith("Z") ? texto : texto.replace(" ", "T") + "Z");
  if (!Number.isNaN(iso)) return iso;
  const m = texto.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})$/);
  if (!m) return null;
  return Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4], +m[5], +m[6]);
}

function featureComun(id, lon, lat, depth, mag, place, time, updated, source, magType) {
  const depthN = finito(depth);
  return {
    type: "Feature",
    id,
    geometry: {
      type: "Point",
      coordinates: [finito(lon), finito(lat), depthN == null ? null : Math.abs(depthN)],
    },
    properties: {
      mag: finito(mag),
      magType: magType ?? null,
      place: place || "Sin descripción",
      time,
      updated: updated ?? time,
      type: "earthquake",
      source,
    },
  };
}

function coleccion(features, source, url) {
  return {
    type: "FeatureCollection",
    metadata: {
      generated: Date.now(),
      count: features.length,
      source,
      url,
    },
    features,
  };
}

function normalizarUsgs(payload, url) {
  const features = [];
  for (const feature of payload.features || []) {
    const p = feature.properties || {};
    if (p.type && p.type !== "earthquake") continue;
    const c = feature.geometry?.coordinates || [];
    features.push(featureComun(feature.id || p.code || `usgs-${features.length}`, c[0], c[1], c[2], p.mag, p.place || p.title, aMilis(p.time), aMilis(p.updated), "usgs", p.magType));
  }
  return coleccion(features, "usgs", url);
}

function normalizarEmsc(payload, url) {
  const features = [];
  for (const feature of payload.features || []) {
    const p = feature.properties || {};
    const c = feature.geometry?.coordinates || [];
    features.push(featureComun(
      feature.id || p.unid || `emsc-${features.length}`,
      p.lon ?? c[0],
      p.lat ?? c[1],
      p.depth ?? c[2],
      p.mag,
      p.flynn_region || p.place,
      aMilis(p.time),
      aMilis(p.lastupdate),
      "emsc",
      p.magtype || p.magType,
    ));
  }
  return coleccion(features, "emsc", url);
}

function normalizarIgnRss(texto, url) {
  const features = [];
  const items = texto.match(/<item>[\s\S]*?<\/item>/g) || [];
  for (const item of items) {
    const pick = (re) => {
      const m = item.match(re);
      return m ? m[1].trim() : null;
    };
    const descripcion = pick(/<description>([\s\S]*?)<\/description>/) || "";
    const lat = pick(/<geo:lat>([^<]+)<\/geo:lat>/) || pick(/localizaci[oó]n:\s*([-\d.]+)\s*,/i);
    const lon = pick(/<geo:long>([^<]+)<\/geo:long>/) || (() => {
      const m = descripcion.match(/localizaci[oó]n:\s*[-\d.]+\s*,\s*([-\d.]+)/i);
      return m ? m[1] : null;
    })();
    const mag = pick(/magnitud\s+([-\d.]+)/i);
    const lugar = pick(/magnitud\s+[-\d.]+\s+en\s+(.+?)\s+en la fecha/i) || pick(/<title>([\s\S]*?)<\/title>/);
    const fecha = pick(/fecha\s+(\d{2}\/\d{2}\/\d{4}\s+\d{1,2}:\d{2}:\d{2})/i);
    const evid = pick(/evid=([A-Za-z0-9_-]+)/);
    const time = aMilis(fecha);
    features.push(featureComun(evid || `ign-${features.length}`, lon, lat, null, mag, lugar, time, time, "ign", null));
  }
  return coleccion(features, "ign", url);
}

async function leerFuente(id) {
  const url = FUENTES[id];
  const upstream = await fetch(url, {
    headers: { "user-agent": "observatorio-proxy-fuentes" },
  });
  if (!upstream.ok) {
    return new Response(JSON.stringify({ error: `HTTP ${upstream.status}`, url }), { status: 502, headers: jsonHeaders });
  }
  if (id === "ign") {
    const texto = await upstream.text();
    return new Response(JSON.stringify(normalizarIgnRss(texto, url)), { status: 200, headers: jsonHeaders });
  }
  const payload = await upstream.json();
  const normalizado = id === "usgs" ? normalizarUsgs(payload, url) : normalizarEmsc(payload, url);
  return new Response(JSON.stringify(normalizado), { status: 200, headers: jsonHeaders });
}

export default async (request) => {
  const incoming = new URL(request.url);
  if (request.method !== "GET" || !incoming.pathname.startsWith("/api/")) {
    return new Response(JSON.stringify({ error: "No encontrado" }), {
      status: 404,
      headers: jsonHeaders,
    });
  }

  const fuenteMatch = incoming.pathname.match(/^\/api\/fuentes\/(ign|usgs|emsc)\/?$/);
  if (fuenteMatch) {
    try {
      return await leerFuente(fuenteMatch[1]);
    } catch {
      return new Response(JSON.stringify({ error: "No se pudo leer la fuente externa" }), {
        status: 502,
        headers: jsonHeaders,
      });
    }
  }

  if (incoming.pathname === "/api/fuentes" || incoming.pathname === "/api/fuentes/") {
    return new Response(JSON.stringify({
      fuentes: [
        { id: "ign", nombre: "IGN (España)", url: FUENTES.ign },
        { id: "usgs", nombre: "USGS", url: FUENTES.usgs },
        { id: "emsc", nombre: "EMSC", url: FUENTES.emsc },
      ],
    }), { status: 200, headers: jsonHeaders });
  }

  try {
    const upstream = await fetch(TUNEL + incoming.pathname + incoming.search, {
      method: "GET",
      headers: {
        "ngrok-skip-browser-warning": "1",
        "user-agent": "observatorio-proxy",
      },
    });
    const headers = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    headers.set("cache-control", "no-store");
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return new Response(JSON.stringify({ error: "El túnel no responde" }), {
      status: 502,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  }
};
