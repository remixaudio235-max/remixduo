import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.js";

const env = {
  PUBLIC_APP_NAME: "RemiX Duo",
  PUBLIC_APP_VERSION: "8.77",
};

test("publishes Duo-specific app information", async () => {
  const response = await worker.fetch(new Request("https://duo.example/api/appinfo"), env);
  assert.equal(response.status, 200);
  const data = await response.json();
  assert.equal(data.product, "REMIX_DUO");
  assert.equal(data.license_edition, "PRO");
});

test("requires a bearer token before forwarding admin routes", async () => {
  const response = await worker.fetch(new Request("https://duo.example/api/admin/licenses"), env);
  assert.equal(response.status, 401);
});

test("rejects wrong methods and oversized requests before proxying", async () => {
  const wrongMethod = await worker.fetch(
    new Request("https://duo.example/api/license/activate"), env,
  );
  assert.equal(wrongMethod.status, 405);

  const oversized = await worker.fetch(new Request(
    "https://duo.example/api/license/activate",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ value: "x".repeat(33_000) }),
    },
  ), env);
  assert.equal(oversized.status, 413);
});

test("proxies license activation only through the service binding", async () => {
  let captured;
  const boundEnv = {
    ...env,
    LICENSE_BACKEND: {
      async fetch(request) {
        captured = request;
        return new Response(JSON.stringify({
          ok: false,
          status: "LICENSE_NOT_FOUND",
        }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      },
    },
  };
  const response = await worker.fetch(new Request(
    "https://duo.example/api/license/activate",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ license_id: "TEST", machine_hash: "DUO2-TEST" }),
    },
  ), boundEnv);
  assert.equal(response.status, 404);
  assert.equal(response.headers.get("x-remix-duo-gateway"), "v879");
  assert.equal(new URL(captured.url).pathname, "/api/license/activate");
  assert.equal(captured.headers.get("authorization"), null);
});

test("serves a Duo-branded admin page through the service binding", async () => {
  const boundEnv = {
    ...env,
    LICENSE_BACKEND: {
      async fetch() {
        return new Response("<title>RemiX License Admin</title><h1>RemiX License Admin</h1>", {
          headers: { "content-type": "text/html" },
        });
      },
    },
  };
  const response = await worker.fetch(new Request("https://duo.example/"), boundEnv);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /RemiX Duo License Admin/);
  assert.doesNotMatch(html, />RemiX License Admin</);
});

test("forwards bearer auth and query only to the internal admin service", async () => {
  let captured;
  const boundEnv = {
    ...env,
    LICENSE_BACKEND: {
      async fetch(request) {
        captured = request;
        return new Response(JSON.stringify({ ok: true, results: [] }), {
          headers: { "content-type": "application/json" },
        });
      },
    },
  };
  const response = await worker.fetch(new Request(
    "https://duo.example/api/admin/activation-requests?status=PENDING",
    { headers: { authorization: "Bearer test-admin-token" } },
  ), boundEnv);
  assert.equal(response.status, 200);
  assert.equal(captured.headers.get("authorization"), "Bearer test-admin-token");
  assert.equal(
    new URL(captured.url).pathname + new URL(captured.url).search,
    "/api/admin/activation-requests?status=PENDING",
  );
});

test("turns an upstream 401 into a clear shared-token message", async () => {
  const boundEnv = {
    ...env,
    LICENSE_BACKEND: {
      async fetch() {
        return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });
      },
    },
  };
  const response = await worker.fetch(new Request(
    "https://duo.example/api/admin/health",
    { headers: { authorization: "Bearer wrong-token" } },
  ), boundEnv);
  assert.equal(response.status, 401);
  const data = await response.json();
  assert.match(data.error, /trang RemiX License Admin gốc/);
});
