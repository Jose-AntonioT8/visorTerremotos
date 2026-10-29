const TUNEL = "https://whoops-botanical-humorist.ngrok-free.dev";

export default async (request) => {
  const incoming = new URL(request.url);
  if (request.method !== "GET" || !incoming.pathname.startsWith("/api/")) {
    return new Response(JSON.stringify({ error: "No encontrado" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
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
