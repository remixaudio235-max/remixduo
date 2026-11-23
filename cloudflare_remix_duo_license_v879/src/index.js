const PUBLIC_ROUTES = new Map([
  ["/api/license/activate", "POST"],
  ["/api/license/request-activation", "POST"],
  ["/api/license/verify", "POST"],
  ["/api/license/heartbeat", "POST"],
  ["/api/license/release", "POST"],
]);

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: JSON_HEADERS,
  });
}

function publicAppInfo(env) {
  return json({
    ok: true,
    app_name: env.PUBLIC_APP_NAME || "RemiX Duo",
    version: env.PUBLIC_APP_VERSION || "8.77",
    product: "REMIX_DUO",
    license_edition: "PRO",
    server_time: Math.floor(Date.now() / 1000),
  });
}

function licenseBackend(env) {
  if (!env.LICENSE_BACKEND || typeof env.LICENSE_BACKEND.fetch !== "function") {
    throw new Error("LICENSE_BACKEND_BINDING_MISSING");
  }
  return env.LICENSE_BACKEND;
}

async function proxyAdminPage(env) {
  const response = await licenseBackend(env).fetch(new Request(
    "https://remix-license-admin.internal/",
    { method: "GET", redirect: "manual" },
  ));
  const html = (await response.text())
    .replaceAll("RemiX License Admin", "RemiX Duo License Admin")
    .replace(
      "Dán ADMIN_TOKEN đã set bằng wrangler secret",
      "Dán DUO_ADMIN_TOKEN riêng của RemiX Duo",
    )
    .replace(
      "Sẵn sàng. Bấm “Test kết nối” trước để kiểm tra ADMIN_TOKEN, DB và private key.",
      "Nhập Admin Token riêng của Duo, rồi bấm “Test kết nối”.",
    );
  return new Response(html, {
    status: response.status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "x-remix-duo-gateway": "v879",
    },
  });
}

async function proxyAdminRequest(request, env, url) {
  const authorization = String(request.headers.get("authorization") || "");
  if (!/^Bearer\s+\S+$/i.test(authorization)) {
    return json({ ok: false, error: "Unauthorized" }, 401);
  }
  if (env.DUO_ADMIN_TOKEN) {
    const supplied = authorization.replace(/^Bearer\s+/i, "");
    const digest = async (value) => new Uint8Array(await crypto.subtle.digest(
      "SHA-256", new TextEncoder().encode(value),
    ));
    const actual = await digest(supplied);
    const expected = await digest(env.DUO_ADMIN_TOKEN);
    let difference = 0;
    for (let i = 0; i < actual.length; i++) difference |= actual[i] ^ expected[i];
    if (difference !== 0) return json({ ok: false, error: "Admin Token Duo không đúng." }, 401);
    if (!env.UPSTREAM_ADMIN_TOKEN) return json({
      ok: false, error: "Token Duo hợp lệ. Server cần cấu hình secret UPSTREAM_ADMIN_TOKEN để kết nối hệ thống quản trị.",
    }, 503);
  }

  const contentLength = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(contentLength) && contentLength > 131_072) {
    return json({ ok: false, status: "REQUEST_TOO_LARGE" }, 413);
  }
  const hasBody = !["GET", "HEAD"].includes(request.method);
  const body = hasBody ? await request.arrayBuffer() : undefined;
  if (body && body.byteLength > 131_072) {
    return json({ ok: false, status: "REQUEST_TOO_LARGE" }, 413);
  }

  const headers = new Headers();
  headers.set("authorization", env.DUO_ADMIN_TOKEN
    ? "Bearer " + env.UPSTREAM_ADMIN_TOKEN : authorization);
  headers.set("accept", request.headers.get("accept") || "application/json");
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const upstreamRequest = new Request(
    "https://remix-license-admin.internal" + url.pathname + url.search,
    {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    },
  );
  const response = await licenseBackend(env).fetch(upstreamRequest);
  if (response.status === 401) {
    return json({
      ok: false,
      error: "ADMIN_TOKEN không đúng. Hãy dùng cùng token của trang RemiX License Admin gốc.",
    }, 401);
  }
  const responseHeaders = new Headers({
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "x-remix-duo-gateway": "v879",
  });
  for (const name of ["content-type", "content-disposition"]) {
    const value = response.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(await response.arrayBuffer(), {
    status: response.status,
    headers: responseHeaders,
  });
}

async function proxyPublicLicenseRequest(request, env, path) {
  const contentLength = Number(request.headers.get("content-length") || "0");
  if (Number.isFinite(contentLength) && contentLength > 32_768) {
    return json({ ok: false, status: "REQUEST_TOO_LARGE" }, 413);
  }

  const body = await request.arrayBuffer();
  if (body.byteLength > 32_768) {
    return json({ ok: false, status: "REQUEST_TOO_LARGE" }, 413);
  }

  const headers = new Headers();
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("accept", "application/json");
  headers.set("user-agent", "RemiXDuo-License-Gateway/8.77");

  const upstreamRequest = new Request("https://remix-license-admin.internal" + path, {
    method: "POST",
    headers,
    body,
    redirect: "manual",
  });
  const response = await licenseBackend(env).fetch(upstreamRequest);

  const responseBody = await response.arrayBuffer();
  const responseHeaders = new Headers(JSON_HEADERS);
  responseHeaders.set("x-remix-duo-gateway", "v879");
  return new Response(responseBody, {
    status: response.status,
    headers: responseHeaders,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      try {
        return await proxyAdminPage(env);
      } catch (error) {
        console.error("Duo admin page failure", error);
        return json({ ok: false, status: "LICENSE_GATEWAY_UNAVAILABLE" }, 502);
      }
    }

    if (request.method === "GET" && url.pathname === "/api/appinfo") {
      return publicAppInfo(env);
    }

    if (url.pathname.startsWith("/api/admin/")) {
      try {
        return await proxyAdminRequest(request, env, url);
      } catch (error) {
        console.error("Duo admin gateway failure", error);
        return json({ ok: false, status: "LICENSE_GATEWAY_UNAVAILABLE" }, 502);
      }
    }

    const allowedMethod = PUBLIC_ROUTES.get(url.pathname);
    if (allowedMethod && request.method === allowedMethod) {
      try {
        return await proxyPublicLicenseRequest(request, env, url.pathname);
      } catch (error) {
        console.error("Duo license gateway failure", error);
        return json({ ok: false, status: "LICENSE_GATEWAY_UNAVAILABLE" }, 502);
      }
    }

    if (PUBLIC_ROUTES.has(url.pathname)) {
      return json({ ok: false, status: "METHOD_NOT_ALLOWED" }, 405);
    }

    return json({ ok: false, status: "NOT_FOUND" }, 404);
  },
};

export { publicAppInfo };
