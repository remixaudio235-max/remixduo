# RemiX Duo V8.76 - Cloudflare CENTRAL License / Key Active Handoff
Date: 2026-11-02
Single source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Account from owner's Cloudflare dashboard URL: 1ff16b4d9ee7dc1e699b5d93b0890eb6
Previous Git HEAD: 427e868

## Product policy

COMMERCIAL licenses are issued/renewed/revoked by Cloudflare Worker+D1.
The old standalone V8.74 local license issuer is development/legacy only.
It must not be distributed with Duo. The frozen commercial EXE is gated
through remix_duo_cloud_license_v876.activation_gate, never the legacy
V8.74 local signer. Development source remains on prior QA issuer until
Cloudflare endpoint is provisioned, so the currently running Admin-PC
GUI is not broken. No Smaart, generator, capture, sweeps or audio I/O
were run or changed in this task.

## Files

- cloudflare_duo_license_worker_v876.mjs:
  POST /v1/admin/issue: random RDX key, D1 stores only SHA-256 key hash,
       customer/order_id/days/seats. Bearer secret required.
  GET  /v1/admin/status?id=...: retrieve metadata+used seats (admin).
  POST /v1/admin/revoke: revoke license centrally (admin).
  POST /v1/activate: validates key+machine+edition+expiry+seats, signs
       short-lived LIC1 v2 certificate using Worker Ed25519 secret.
  GET  /admin: web management UI hosted in Cloudflare Worker.
  GET  /admin/app.js: same-origin management script, no token persistence.
  GET  /health: deployment readiness only, no secrets.
- cloudflare_duo_admin_ui_v876.mjs:
  Admin-only issuing/status/revoke page. Uses same-origin requests with
  bearer token entered by operator, not exposed to customers.
- cloudflare_duo_license_schema_v876.sql:
  D1 license_keys and activations, FK/indexes and seat-limit INSERT
  trigger, avoiding concurrent seat over-allocation.
- wrangler.duo-license.example.jsonc:
  Worker name remix-duo-license, account ID from provided dashboard,
  database name remix-duo-license-db, placeholder D1 UUID.
- remix_duo_cloud_license_v876.py:
  HTTPS activation POST only. Validates signed issuer == CLOUDFLARE,
  product DUO_PRO, device hash, 72h maximum offline certificate,
  raw Ed25519 signature; stores the certificate atomically.
  User's RDX activation key can be saved using Windows user DPAPI for
  automatic renewal on restart after expiry. No admin bearer secret
  or private signing key in distributed client.
  Cloud public key pinned to independently generated Cloudflare signer.
  CLOUD_WORKER_URL intentionally BLANK until deployed and real QA.
- remix_duo_cloud_admin_provision_v876.py:
  On ADMIN-PC, creates NEW Cloudflare Ed25519 PKCS8 signing key +
  admin API secret. Both DPAPI-encrypted at:
    %LOCALAPPDATA%\RemiXAudioIssuer\DuoCloud\*.dpapi
  Only prints public key. Optional upload-secrets pipes values directly
  into authenticated Wrangler stdin; no secret appears in CLI args/logs.
  copy-admin-token copies token to clipboard WITHOUT displaying it.
- qa_v876_cloud_signer_parity.py:
  Independent synthetic signing test against pinned client public key;
  NO real customer key signed and no secret printed.
- test_v876_cloudflare_worker.mjs:
  In-memory fake D1 Node tests; no Cloudflare production writes.
- test_v876_cloud_license_client.py:
  Offline synthetic certs, expiry/product/issuer, invalid signature,
  HTTPS transport, atomic storage and Windows DPAPI key caching.
- overlay_v7.py:
  only frozen EXE uses cloud activation gate; developer QA source
  retains existing V8.74 local test license. No GUI behavior changes.

## Verified locally on Admin-PC

- Node Worker admin UI/status/issue/activation/seat/revoke: 6/6 PASS.
- Python Cloudflare client tests: 14/14 PASS.
- Previous V8.73–V8.75 regressions: 103/103 PASS.
- Combined Python QA: 117/117 PASS (if re-run including 14 tests).
- DPAPI-staged Ed25519 signer matches pinned public verifier:
  CLOUD_DPAPI_SIGNER_PUBLIC_PIN_PARITY_PASS.
- DO NOT confuse synthetic QA with Cloudflare production deployment.

## Cloudflare account provisioning steps (requires real admin login)

1. Open Cloudflare dashboard of the supplied account:
   https://dash.cloudflare.com/1ff16b4d9ee7dc1e699b5d93b0890eb6/home/overview

2. Workers & Pages: create a NEW dedicated Worker named
   remix-duo-license. Do not alter existing MeTube or other Workers.
3. D1 SQL Database: create a NEW database remix-duo-license-db.
4. In a terminal authenticated to the SAME account via Wrangler:
   npx wrangler login
   npx wrangler d1 create remix-duo-license-db
   Copy the returned D1 UUID into a local Wrangler JSONC config based
   on wrangler.duo-license.example.jsonc (name, account_id already set).
5. Apply the schema to the new D1 ONLY:
   npx wrangler d1 execute remix-duo-license-db --remote ^
     --file cloudflare_duo_license_schema_v876.sql ^
     --config wrangler.duo-license.local.jsonc
6. Initial deploy of Worker under this account:
   npx wrangler deploy --config wrangler.duo-license.local.jsonc
7. Set the two Worker Secrets using protected Admin-PC tool:
   python remix_duo_cloud_admin_provision_v876.py upload-secrets ^
     --config wrangler.duo-license.local.jsonc
   This requires already-authenticated Wrangler, may create Worker
   versions/deployments. No secret should be sent in chat, git or URL.
8. Confirm /health reports configured:true on the returned Worker URL.
   Then set CLOUD_WORKER_URL in remix_duo_cloud_license_v876.py to
   that HTTPS Worker URL. The verified public key is ALREADY pinned.
9. Cloudflare Zero Trust Access: protect admin management routes
   /admin, /admin/app.js and /v1/admin/* (on a compatible hostname/
   route configuration). Keep /v1/activate public for customer clients,
   but use WAF rate limiting. A whole-Worker Access policy would block
   customer activation if their desktop does not authenticate to Access.
   The admin Bearer token remains required independently.
10. Run live create/activate/status/revoke on dedicated TEST licenses and
    test a clean Windows VM before signing a commercial release.
    Only then freeze/package Windows EXE and point it at the real URL.
    This release MUST NOT include _issuer_admin or the DPAPI files.

## How admins issue keys AFTER deployment

- From Cloudflare Workers & Pages > remix-duo-license > Visit, open
  /admin. Sign in to Cloudflare Access as the authorized staff member
  and enter admin API token (on admin PC:
    python remix_duo_cloud_admin_provision_v876.py copy-admin-token).
- Enter order ID/customer/days (0 = perpetual)/seats (1-500).
- Click "Cap key tren Cloudflare": new RDX-... key is displayed ONCE.
- Send only customer activation key (RDX-...), not admin bearer.
- On end user's Duo, click Copy Machine ID, enter RDX key; Duo calls
  Cloudflare API, verifies Ed25519 cert, caches offline <=72h.
- To revoke, lookup license UUID and click Thu hoi. Already-issued
  offline cert expires within 72h; revocation is NOT instantaneous
  while the client has no internet access.

## Exact status after this task

PASS: backend implementation, D1 migration source, admin page source,
signed cloud-client protocol, DPAPI server secrets staged on Admin-PC,
cryptographic parity and local QA.
HOLD: Cloudflare account authentication, D1 actual creation, secrets
upload to Cloudflare, Worker deploy, Access policy and live API QA.
HOLD: customer installer/Windows Sandbox or clean-machine EXE testing.
Cloud Worker URL is deliberately empty: frozen EXE fails CLOSED instead
of accepting the legacy local QA key.
HOLD: live native Smaart TF Mag/Phase remains unrelated.

Security notes: Signer private key stays outside Git. Keep Cloudflare
API token out of chat and code. Secure Access/WAF before production.
Track D1 charges in the Cloudflare dashboard. D1/Worker deployment and
auth must be proven in target account, never inferred from a URL alone.
