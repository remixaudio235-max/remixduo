import { validateClientProfile, clientProfileMismatch, macMachineAuthorized } from './clientProfiles';
import { ed25519 } from '@noble/curves/ed25519';

type Env = {
  DB: any;
  ADMIN_TOKEN: string;
  ED25519_PRIVATE_SEED_B64: string;
  PUBLIC_APP_NAME?: string;

  PUBLIC_LATEST_VERSION?: string;
  PUBLIC_CODENAME?: string;
  PUBLIC_DISPLAY_VERSION?: string;
  PUBLIC_INSTALLER_NAME?: string;
  PUBLIC_INSTALLER_URL?: string;
  PUBLIC_INSTALLER_SHA256?: string;
  PUBLIC_OFFLINE_GRACE_DAYS?: string;
};

const DEFAULT_FEATURES = [
  'SPL', 'RTA', 'TF', 'IR', 'POLARITY', 'AUTO_TUNE', 'AUTO_PHASE', 'FIR', 'EXPORT', 'AI_ASSISTANT'
];

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' }
  });
}

function html(body: string, status = 200) {
  return new Response(body, {
    status,
    headers: { 'content-type': 'text/html; charset=utf-8' }
  });
}

function nowIso() { return new Date().toISOString(); }
function nowTs() { return Math.floor(Date.now() / 1000); }
function uuid(prefix = '') { return prefix + crypto.randomUUID(); }

function b64urlEncode(bytes: Uint8Array): string {
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function b64DecodeAny(input: string): Uint8Array {
  const raw = String(input || '')
    // Notepad/pipe on Windows may introduce BOM or invisible unicode chars.
    .replace(/[\uFEFF\u200B-\u200D\u2060]/g, '')
    .trim()
    .replace(/^["']|["']$/g, '');

  const candidates: string[] = [];

  // Normal expected value: only the base64/base64url seed.
  if (raw) candidates.push(raw);

  // If admin accidentally pasted "ED25519_PRIVATE_SEED_B64: <value>",
  // try the part after the last colon as a recovery candidate.
  const afterColon = raw.includes(':') ? raw.split(':').pop()!.trim() : '';
  if (afterColon && afterColon !== raw) candidates.unshift(afterColon);

  // Also try the longest base64-looking segment. This handles accidental
  // copy with surrounding text while still failing if no valid seed exists.
  const matches = raw.match(/[A-Za-z0-9+/_-]{40,}={0,2}/g) || [];
  matches.sort((a, b) => b.length - a.length);
  for (const m of matches) {
    if (!candidates.includes(m)) candidates.unshift(m);
  }

  let lastErr = '';
  for (const cand of candidates) {
    const cleaned = cand
      .replace(/[\uFEFF\u200B-\u200D\u2060]/g, '')
      .replace(/\s+/g, '')
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .replace(/^["']|["']$/g, '');

    if (!cleaned) continue;

    const pad = '='.repeat((4 - cleaned.length % 4) % 4);
    try {
      const bin = atob(cleaned + pad);
      return Uint8Array.from(bin, c => c.charCodeAt(0));
    } catch (e: any) {
      lastErr = e?.message || String(e);
    }
  }

  throw new Error(lastErr || 'BAD_BASE64');
}

function loadEd25519PrivateSeed(env: Env): Uint8Array {
  const rawBytes = b64DecodeAny(env.ED25519_PRIVATE_SEED_B64 || '');

  // Some old/offline tools export 64 bytes. The old signer used the first
  // 32 bytes as the Ed25519 seed, so keep that compatibility here.
  if (rawBytes.length === 64) return rawBytes.slice(0, 32);

  if (rawBytes.length !== 32) {
    throw new Error(`BAD_LENGTH_${rawBytes.length}`);
  }
  return rawBytes;
}

function canonicalize(value: any): any {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    const out: Record<string, any> = {};
    for (const key of Object.keys(value).sort()) out[key] = canonicalize(value[key]);
    return out;
  }
  return value;
}

function canonicalJsonBytes(obj: any): Uint8Array {
  const s = JSON.stringify(canonicalize(obj));
  return new TextEncoder().encode(s);
}

function normalizeHwIds(raw: string | string[]): string[] {
  const parts = Array.isArray(raw) ? raw : String(raw || '').split(/[\s,;]+/g);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of parts) {
    const h = String(p || '').trim().toUpperCase();
    if (!h || seen.has(h)) continue;
    seen.add(h); out.push(h);
  }
  if (out.length < 1) throw new Error('HW ID không được trống.');
  if (out.length > 2) throw new Error('Chỉ hỗ trợ 1-2 HW ID cho mỗi license.');
  if (out[0].length < 8) throw new Error('HW ID quá ngắn.');
  return out;
}

function calcExp(days: number, iat: number): number {
  const d = Math.max(0, Math.floor(Number(days || 0)));
  return d <= 0 ? 0 : iat + d * 86400;
}

function parseHwIdsFromLicenseRow(raw: any): string[] {
  try {
    const arr = JSON.parse(String(raw || '[]'));
    if (!Array.isArray(arr)) return [];
    return arr.map(x => String(x || '').trim().toUpperCase()).filter(Boolean);
  } catch {
    return [];
  }
}

export function normalizeLicenseEdition(raw: any): string {
  const value = String(raw || '').trim().toUpperCase();
  if (!value) return 'PRO';
  if (['PREMIUM', 'SUITE', 'LUX', 'LUXURY'].includes(value)) return 'PREMIUM';
  return 'PRO';
}

function licenseEditionFromRow(row: any): string {
  return normalizeLicenseEdition(row?.edition || row?.plan || 'PRO');
}

export function shouldBlockDuplicateHwIdForEdition(existingLicense: any, requestedEdition: any): boolean {
  return licenseEditionFromRow(existingLicense) === normalizeLicenseEdition(requestedEdition);
}

async function findDuplicateHwIdLicense(env: Env, hwIds: string[], requestedEdition: string) {
  const wanted = new Set(hwIds.map(x => String(x || '').trim().toUpperCase()).filter(Boolean));
  if (wanted.size < 1) return null;

  // A machine may hold one Pro-family license and one Suite/Premium license.
  // Still block duplicates inside the same effective edition.
  const rows = await env.DB.prepare(`
    SELECT id, license_id, customer_name, customer_phone, hw_ids_json, edition, plan, status, exp, created_at
    FROM licenses
    WHERE status != 'REVOKED'
    ORDER BY created_at DESC
    LIMIT 5000
  `).all();

  const now = nowTs();

  for (const r of ((rows.results || []) as any[])) {
    const rowHwIds = parseHwIdsFromLicenseRow(r.hw_ids_json);

    for (const h of rowHwIds) {
      if (!wanted.has(h)) continue;

      const exp = Number(r.exp || 0);
      const notExpired = exp === 0 || exp > now;

      if (notExpired && shouldBlockDuplicateHwIdForEdition(r, requestedEdition)) {
        return {
          duplicateHwId: h,
          license: r
        };
      }
    }
  }

  return null;
}

function signLicenseToken(env: Env, payload: any): string {
  const seed = loadEd25519PrivateSeed(env);
  const msg = canonicalJsonBytes(payload);
  const sig = ed25519.sign(msg, seed);
  return `LIC1.${b64urlEncode(msg)}.${b64urlEncode(sig)}`;
}

function requireAdmin(request: Request, env: Env): Response | null {
  const expected = env.ADMIN_TOKEN || '';
  if (!expected) return json({ ok: false, error: 'ADMIN_TOKEN chưa được cấu hình.' }, 500);
  const auth = request.headers.get('authorization') || '';
  const token = auth.toLowerCase().startsWith('bearer ') ? auth.slice(7).trim() : '';
  if (token !== expected) return json({ ok: false, error: 'Unauthorized' }, 401);
  return null;
}

async function audit(env: Env, action: string, detail: any, actor = 'admin') {
  // Audit log must never break license activation/admin actions.
  // If audit_logs table is missing or D1 throws, keep the main flow alive.
  try {
    await env.DB.prepare('INSERT INTO audit_logs(id, action, actor, detail_json, created_at) VALUES(?,?,?,?,?)')
      .bind(uuid('AUD-'), action, actor, JSON.stringify(detail), nowIso()).run();
  } catch (e: any) {
    console.warn('audit skipped:', action, String(e?.message || e || ''));
  }
}

async function upsertCustomer(env: Env, input: any) {
  const name = String(input.name || '').trim();
  if (!name) throw new Error('Tên khách không được trống.');
  const phone = String(input.phone || '').trim();
  const email = String(input.email || '').trim();
  const zalo = String(input.zalo || '').trim();
  const note = String(input.note || '').trim();

  let existing: any = null;
  if (phone) {
    existing = await env.DB.prepare('SELECT * FROM customers WHERE phone = ? LIMIT 1').bind(phone).first();
  }
  const t = nowIso();
  if (existing) {
    await env.DB.prepare('UPDATE customers SET name=?, email=?, zalo=?, note=?, updated_at=? WHERE id=?')
      .bind(name, email, zalo, note, t, existing.id).run();
    return { ...existing, name, phone, email, zalo, note, updated_at: t };
  }
  const id = uuid('CUS-');
  await env.DB.prepare('INSERT INTO customers(id, name, phone, email, zalo, note, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)')
    .bind(id, name, phone, email, zalo, note, t, t).run();
  return { id, name, phone, email, zalo, note, created_at: t, updated_at: t };
}

async function createLicense(request: Request, env: Env) {
  const input: any = await request.json();
  const hwIds = normalizeHwIds(input.hwIds || input.hw_ids || '');
  const edition = String(input.edition || input.plan || 'PRO').trim().toUpperCase();
  const plan = String(input.plan || edition || 'PRO').trim().toUpperCase();

  // DUPLICATE HWID GUARD:
  // Do not issue a second active license for the same effective edition.
  // Pro -> Premium/Suite upgrade on the same HWID is allowed.
  const dup = await findDuplicateHwIdLicense(env, hwIds, edition);
  if (dup) {
    return json({
      ok: false,
      status: 'DUPLICATE_HWID',
      error: 'HWID này đã có license cùng gói đang còn hiệu lực. Không thể cấp license mới trùng edition cho cùng một máy. Nếu nâng Pro lên Suite, hãy chọn Gói/Edition = PREMIUM.',
      duplicate_hwid: dup.duplicateHwId,
      existing_license_row_id: dup.license.id,
      existing_license_id: dup.license.license_id,
      existing_edition: dup.license.edition,
      existing_plan: dup.license.plan,
      existing_customer_name: dup.license.customer_name,
      existing_customer_phone: dup.license.customer_phone,
      existing_status: dup.license.status,
      existing_exp: dup.license.exp
    }, 409);
  }

  const platform = String(input.platform || 'WIN').trim().toUpperCase();
  const fpv = Number(input.fpv || 3);
  validateClientProfile(platform, fpv, hwIds);
  const customerName = String(input.customerName || input.name || '').trim();
  const customerPhone = String(input.customerPhone || input.phone || '').trim();
  if (!customerName) throw new Error('Tên khách không được trống.');
  const days = Math.max(0, Math.floor(Number(input.days ?? 365)));
  const maxRebind = Math.max(0, Math.min(99, Math.floor(Number(input.maxRebind ?? input.max_rebind ?? 3))));
  const features = Array.isArray(input.features) ? input.features.map((x: any) => String(x).trim().toUpperCase()).filter(Boolean) : DEFAULT_FEATURES;
  const licenseId = String(input.licenseId || input.lic_id || customerPhone || `LIC-${Date.now()}`).trim();
  const price = String(input.price || '').trim();
  const orderCode = String(input.orderCode || '').trim();
  const note = String(input.note || '').trim();

  const customer = await upsertCustomer(env, { name: customerName, phone: customerPhone, note });

  const iat = nowTs();
  const exp = calcExp(days, iat);
  const h0 = hwIds[0] || '';

  const payload = {
    v: 3,
    fpv,
    platform,
    hw_ids: hwIds,
    machine_ids: hwIds,
    machine: h0,
    machine_id: h0,
    lic_id: licenseId,
    edition,
    name: customerName,
    iat,
    exp,
    max_rebind: maxRebind,
    // Field mới để quản lý tốt hơn. App cũ có thể bỏ qua nếu chưa dùng.
    plan,
    features,
    customer_phone: customerPhone,
    order_code: orderCode
  };
  const token = signLicenseToken(env, payload);
  const t = nowIso();
  const id = uuid('LIC-');

  await env.DB.prepare(`INSERT INTO licenses(
    id, license_id, customer_id, customer_name, customer_phone, platform, fpv, hw_ids_json,
    edition, plan, features_json, days, iat, exp, max_rebind, price, order_code, note, token, status, created_at, updated_at
  ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(
    id, licenseId, customer.id, customerName, customerPhone, platform, fpv, JSON.stringify(hwIds),
    edition, plan, JSON.stringify(features), days, iat, exp, maxRebind, price, orderCode, note, token, 'ACTIVE', t, t
  ).run();

  await audit(env, 'license.created', { id, licenseId, customerName, customerPhone, hwIds, days, exp, plan });

  return json({ ok: true, license: { id, licenseId, customerName, customerPhone, platform, fpv, hwIds, edition, plan, features, days, iat, exp, maxRebind, price, orderCode, note, status: 'ACTIVE', token } });
}

async function listLicenses(request: Request, env: Env) {
  const url = new URL(request.url);
  const q = `%${(url.searchParams.get('q') || '').trim()}%`;
  const limit = Math.min(300, Math.max(1, Number(url.searchParams.get('limit') || 100)));
  const rows = await env.DB.prepare(`SELECT * FROM licenses
    WHERE id LIKE ? OR license_id LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ? OR hw_ids_json LIKE ? OR order_code LIKE ? OR note LIKE ?
    ORDER BY created_at DESC LIMIT ?`).bind(q, q, q, q, q, q, q, limit).all();
  return json({ ok: true, results: rows.results || [] });
}

async function listCustomers(request: Request, env: Env) {
  const url = new URL(request.url);
  const q = `%${(url.searchParams.get('q') || '').trim()}%`;
  const rows = await env.DB.prepare(`SELECT * FROM customers
    WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR zalo LIKE ? OR note LIKE ?
    ORDER BY updated_at DESC LIMIT 200`).bind(q, q, q, q, q).all();
  return json({ ok: true, results: rows.results || [] });
}

async function revokeLicense(request: Request, env: Env, id: string) {
  const t = nowIso();
  await env.DB.prepare('UPDATE licenses SET status=?, updated_at=? WHERE id=?').bind('REVOKED', t, id).run();
  await audit(env, 'license.revoked', { id });
  return json({ ok: true });
}

function buildStoredLicensePayloadFromRow(lic: any, expOverride?: number, daysOverride?: number): any {
  const hwIds = parseJsonArraySafe(lic.hw_ids_json).map(x => String(x || '').trim().toUpperCase()).filter(Boolean);
  const h0 = hwIds[0] || '';
  const edition = String(lic.edition || lic.plan || 'PRO').trim().toUpperCase();
  const plan = String(lic.plan || edition || 'PRO').trim().toUpperCase();
  const fpv = Number(lic.fpv || 3);
  const platform = String(lic.platform || 'WIN').trim().toUpperCase();
  const features = parseJsonArraySafe(lic.features_json);
  const iat = Number(lic.iat || nowTs());
  const exp = Number(expOverride ?? lic.exp ?? 0);
  return {
    v: 3,
    fpv,
    platform,
    hw_ids: hwIds,
    machine_ids: hwIds,
    machine: h0,
    machine_id: h0,
    lic_id: String(lic.license_id || lic.id || '').trim(),
    edition,
    name: String(lic.customer_name || '').trim(),
    iat,
    exp,
    max_rebind: Number(lic.max_rebind || 1),
    plan,
    features,
    customer_phone: String(lic.customer_phone || '').trim(),
    order_code: String(lic.order_code || '').trim()
  };
}

async function updateLicenseExpiryAndToken(
  env: Env,
  lic: any,
  newExp: number,
  newDays: number,
  auditAction: string,
  auditDetail: any
) {
  const payload = buildStoredLicensePayloadFromRow(lic, newExp, newDays);
  const token = signLicenseToken(env, payload);
  const t = nowIso();

  await env.DB.prepare('UPDATE licenses SET exp=?, days=?, token=?, updated_at=? WHERE id=?')
    .bind(newExp, newDays, token, t, lic.id).run();

  await audit(env, auditAction, { id: lic.id, license_id: lic.license_id, newExp, newDays, ...auditDetail });

  return {
    ok: true,
    id: lic.id,
    license_id: lic.license_id,
    exp: newExp,
    days: newDays,
    token
  };
}

async function renewLicense(request: Request, env: Env, id: string) {
  const input: any = await request.json().catch(() => ({}));
  const lic: any = await env.DB.prepare('SELECT * FROM licenses WHERE id=?').bind(id).first();
  if (!lic) return json({ ok: false, error: 'Không tìm thấy license.' }, 404);

  const extraDays = Math.max(1, Math.floor(Number(input.extraDays || 365)));
  const currentExp = Number(lic.exp || 0);

  // Nếu đang vĩnh viễn exp=0 mà admin bấm Gia hạn, chuyển sang hạn mới tính từ hôm nay.
  // Nếu còn hạn thì cộng thêm từ ngày hết hạn hiện tại.
  const base = currentExp > nowTs() ? currentExp : nowTs();
  const newExp = base + extraDays * 86400;
  const oldDays = Number(lic.days || 0);
  const newDays = currentExp === 0 ? extraDays : oldDays + extraDays;

  const result = await updateLicenseExpiryAndToken(env, lic, newExp, newDays, 'license.renewed', {
    extraDays,
    oldExp: currentExp,
    oldDays
  });

  return json({
    ...result,
    extraDays,
    expires_text: newExp === 0 ? 'Vĩnh viễn' : new Date(newExp * 1000).toISOString()
  });
}

async function setLicenseExpiry(request: Request, env: Env, id: string) {
  const input: any = await request.json().catch(() => ({}));
  const lic: any = await env.DB.prepare('SELECT * FROM licenses WHERE id=?').bind(id).first();
  if (!lic) return json({ ok: false, error: 'Không tìm thấy license.' }, 404);

  const permanent = !!input.permanent;
  const oldExp = Number(lic.exp || 0);
  const oldDays = Number(lic.days || 0);

  let days = Math.floor(Number(input.days ?? 0));
  if (permanent || days <= 0) {
    const result = await updateLicenseExpiryAndToken(env, lic, 0, 0, 'license.expiry_set', {
      mode: 'PERMANENT',
      oldExp,
      oldDays
    });
    return json({
      ...result,
      permanent: true,
      expires_text: 'Vĩnh viễn'
    });
  }

  days = Math.max(1, Math.min(36500, days));
  const newExp = nowTs() + days * 86400;
  const result = await updateLicenseExpiryAndToken(env, lic, newExp, days, 'license.expiry_set', {
    mode: 'SET_DAYS_FROM_NOW',
    oldExp,
    oldDays
  });

  return json({
    ...result,
    permanent: false,
    expires_text: new Date(newExp * 1000).toISOString()
  });
}

async function deleteLicenseAdmin(request: Request, env: Env, id: string) {
  const lic: any = await env.DB.prepare('SELECT * FROM licenses WHERE id=? LIMIT 1').bind(id).first();
  if (!lic) return json({ ok: false, error: 'Không tìm thấy license để xóa.' }, 404);

  // Hard delete: xóa cả thiết bị đã active của license này trước, rồi xóa license.
  // Không xóa bảng customers để giữ lịch sử khách hàng nếu cần tra cứu sau.
  await env.DB.prepare('DELETE FROM license_activations WHERE license_row_id=? OR license_id=?')
    .bind(id, lic.license_id || '').run();

  await env.DB.prepare('DELETE FROM licenses WHERE id=?').bind(id).run();

  await audit(env, 'license.deleted.admin', {
    id,
    license_id: lic.license_id,
    customer_name: lic.customer_name,
    customer_phone: lic.customer_phone
  });

  return json({
    ok: true,
    deleted: true,
    id,
    license_id: lic.license_id
  });
}

async function ensureActivationRequestsTable(env: Env) {
  // Tự tạo bảng để không cần migration riêng trong giai đoạn dev/test.
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS activation_requests (
      id TEXT PRIMARY KEY,
      license_input TEXT NOT NULL,
      customer_phone TEXT,
      machine_hash TEXT NOT NULL,
      machine_label TEXT,
      app_version TEXT,
      client_edition TEXT,
      status TEXT NOT NULL DEFAULT 'PENDING',
      client_note TEXT,
      admin_note TEXT,
      request_count INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      resolved_at TEXT,
      resolved_by TEXT
    )
  `).run();

  await env.DB.prepare(`ALTER TABLE activation_requests ADD COLUMN client_edition TEXT`)
    .run()
    .catch((e: any) => {
      const msg = String(e?.message || e || '').toLowerCase();
      if (!msg.includes('duplicate column') && !msg.includes('already exists')) throw e;
    });

  await env.DB.prepare(`
    CREATE INDEX IF NOT EXISTS idx_activation_requests_status_updated
    ON activation_requests(status, updated_at)
  `).run();

  await env.DB.prepare(`
    CREATE INDEX IF NOT EXISTS idx_activation_requests_license_machine
    ON activation_requests(license_input, machine_hash)
  `).run();

  await env.DB.prepare(`
    CREATE INDEX IF NOT EXISTS idx_activation_requests_machine
    ON activation_requests(machine_hash)
  `).run();
}

function normalizeLicenseInput(raw: any): string {
  return String(raw || '').trim().slice(0, 80);
}

async function requestActivation(request: Request, env: Env) {
  const input: any = await request.json().catch(() => ({}));
  const licenseInput = normalizeLicenseInput(
    input.license_id || input.licenseId || input.phone || input.customer_phone || input.customerPhone || input.sdt
  );
  const customerPhone = normalizeLicenseInput(input.phone || input.customer_phone || input.customerPhone || input.sdt || licenseInput);
  const machineHash = normalizeMachineHash(input.machine_hash || input.machineHash || input.machine_id || input.machineId || input.hw_id || input.hwid);
  const machineLabel = String(input.machine_label || input.machineLabel || input.device_name || input.deviceName || '').trim().slice(0, 120);
  const appVersion = String(input.app_version || input.appVersion || '').trim().slice(0, 40);
  const clientEdition = requestedClientEdition(input);
  const clientNote = String(input.note || input.client_note || '').trim().slice(0, 500);

  if (!licenseInput) {
    return json({ ok: false, status: 'MISSING_LICENSE_ID', error: 'Thiếu License ID / SĐT.' }, 400);
  }

  await ensureActivationRequestsTable(env);

  const t = nowIso();
  const old: any = await env.DB.prepare(`
    SELECT * FROM activation_requests
    WHERE license_input=? AND machine_hash=? AND status='PENDING'
      AND (client_edition=? OR (client_edition IS NULL AND ?='PRO'))
    LIMIT 1
  `).bind(licenseInput, machineHash, clientEdition, clientEdition).first();

  if (old) {
    await env.DB.prepare(`
      UPDATE activation_requests
      SET customer_phone=?, machine_label=?, app_version=?, client_edition=?, client_note=?,
          request_count=COALESCE(request_count,1)+1, updated_at=?
      WHERE id=?
    `).bind(customerPhone, machineLabel, appVersion, clientEdition, clientNote, t, old.id).run();

    return json({
      ok: true,
      status: 'ACTIVATION_REQUEST_UPDATED',
      request_id: old.id,
      message: 'Đã cập nhật yêu cầu kích hoạt đang chờ admin duyệt.',
      license_input: licenseInput,
      client_edition: clientEdition,
      machine_hash: machineHash
    });
  }

  const id = uuid('REQ-');
  await env.DB.prepare(`
    INSERT INTO activation_requests(
      id, license_input, customer_phone, machine_hash, machine_label, app_version, client_edition,
      status, client_note, admin_note, request_count, created_at, updated_at, resolved_at, resolved_by
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  `).bind(
    id, licenseInput, customerPhone, machineHash, machineLabel, appVersion, clientEdition,
    'PENDING', clientNote, '', 1, t, t, null, ''
  ).run();

  await audit(env, 'activation_request.created', { id, licenseInput, customerPhone, machineHash, machineLabel, appVersion, clientEdition }, 'client');

  return json({
    ok: true,
    status: 'ACTIVATION_REQUEST_SENT',
    request_id: id,
    message: 'Đã gửi yêu cầu kích hoạt đến admin. Vui lòng chờ admin cấp license.',
    license_input: licenseInput,
    client_edition: clientEdition,
    machine_hash: machineHash
  });
}

async function listActivationRequests(request: Request, env: Env) {
  await ensureActivationRequestsTable(env);
  const url = new URL(request.url);
  const q = String(url.searchParams.get('q') || '').trim();
  const status = String(url.searchParams.get('status') || '').trim().toUpperCase();
  const limit = Math.min(1000, Math.max(1, Number(url.searchParams.get('limit') || 100)));

  const wh: string[] = [];
  const binds: any[] = [];

  if (q) {
    const like = `%${q}%`;
    wh.push(`(
      license_input LIKE ? OR customer_phone LIKE ? OR machine_hash LIKE ?
      OR machine_label LIKE ? OR app_version LIKE ? OR client_note LIKE ? OR admin_note LIKE ?
    )`);
    binds.push(like, like, like, like, like, like, like);
  }

  if (status && status !== 'ALL') {
    wh.push(`status=?`);
    binds.push(status);
  }

  const whereSql = wh.length ? `WHERE ${wh.join(' AND ')}` : '';
  const rows = await env.DB.prepare(`
    SELECT *
    FROM activation_requests
    ${whereSql}
    ORDER BY
      CASE status WHEN 'PENDING' THEN 0 WHEN 'APPROVED' THEN 1 WHEN 'REJECTED' THEN 2 ELSE 3 END,
      updated_at DESC
    LIMIT ?
  `).bind(...binds, limit).all();

  return json({ ok: true, results: rows.results || [] });
}

async function updateActivationRequestStatus(request: Request, env: Env, id: string, status: string) {
  await ensureActivationRequestsTable(env);
  const input: any = await request.json().catch(() => ({}));
  const adminNote = String(input.admin_note || input.note || '').trim().slice(0, 500);
  const t = nowIso();
  const row: any = await env.DB.prepare('SELECT * FROM activation_requests WHERE id=? LIMIT 1').bind(id).first();
  if (!row) return json({ ok: false, error: 'Không tìm thấy yêu cầu kích hoạt.' }, 404);

  await env.DB.prepare(`
    UPDATE activation_requests
    SET status=?, admin_note=?, resolved_at=?, resolved_by=?, updated_at=?
    WHERE id=?
  `).bind(status, adminNote, t, 'admin', t, id).run();

  await audit(env, 'activation_request.status', {
    id,
    status,
    license_input: row.license_input,
    machine_hash: row.machine_hash
  });

  return json({ ok: true, status, id });
}

async function deleteActivationRequestAdmin(request: Request, env: Env, id: string) {
  await ensureActivationRequestsTable(env);
  const row: any = await env.DB.prepare('SELECT * FROM activation_requests WHERE id=? LIMIT 1').bind(id).first();
  if (!row) return json({ ok: false, error: 'Không tìm thấy yêu cầu kích hoạt.' }, 404);

  await env.DB.prepare('DELETE FROM activation_requests WHERE id=?').bind(id).run();
  await audit(env, 'activation_request.deleted', {
    id,
    license_input: row.license_input,
    machine_hash: row.machine_hash
  });

  return json({ ok: true, deleted: true, id });
}

function adminPage(appName: string) {
  return html(`<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${appName}</title>
<style>
:root{--bg:#0e141b;--card:#151d27;--line:#2b3a4c;--text:#e7eef7;--muted:#a7b6c8;--ok:#35e0ad;--bad:#ff7b84;--btn:#19c997;--btn2:#29384a}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:10;background:#0b1118;border-bottom:1px solid #243244;padding:14px 18px;display:flex;gap:12px;align-items:center}
h1{font-size:18px;margin:0;color:var(--ok)}.wrap{max-width:1220px;margin:0 auto;padding:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}label{font-size:12px;color:var(--muted);display:block;margin-top:8px}input,textarea,select{width:100%;box-sizing:border-box;background:#0f1721;color:var(--text);border:1px solid #34465b;border-radius:8px;padding:9px;margin-top:4px}textarea{height:76px}button{background:var(--btn);border:0;color:#06120e;border-radius:8px;padding:9px 12px;font-weight:700;cursor:pointer}button:hover{filter:brightness(1.08)}button:disabled{opacity:.55;cursor:not-allowed}.secondary{background:var(--btn2);color:var(--text)}.danger{background:#ef5964;color:white}pre{white-space:pre-wrap;word-break:break-all;background:#0c1118;border:1px solid var(--line);border-radius:8px;padding:10px;max-height:220px;overflow:auto}.row{display:flex;gap:8px;align-items:center}.row>*{flex:1}table{width:100%;border-collapse:collapse;font-size:12px}td,th{border-bottom:1px solid #283647;padding:6px;text-align:left;vertical-align:top}th{color:#79d9ff}.muted{color:#9daec2;font-size:12px}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:#ffd166}.status{margin-top:10px;padding:10px;border:1px solid #34465b;border-radius:8px;background:#0f1721;min-height:20px}.toolbar{display:flex;gap:8px;flex-wrap:wrap}.toolbar button{min-width:130px}.small{font-size:11px}.hide{display:none}.tableBox{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:10px;background:#0c1118}.tableBox table{min-width:1180px}.tableBox thead th{position:sticky;top:0;z-index:2;background:#101923}.nowrap{white-space:nowrap}code{color:#b5f3ff;font-family:Consolas,monospace;font-size:11px}@media(max-width:900px){.grid{grid-template-columns:1fr}.row{flex-direction:column;align-items:stretch}}
:root{color-scheme:dark;--bg:#0d0915;--card:#181222;--line:#3d3150;--text:#f5f1fc;--muted:#bdb1ce;--ok:#75e3bd;--bad:#ff9da9;--btn:#a78bfa;--btn2:#30233f;--purple:#c4b5fd}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:160px}body{font-family:Inter,"Segoe UI",Arial,sans-serif;font-size:15px;line-height:1.55;background:radial-gradient(ellipse at 85% 0%,#302045 0%,transparent 42%),var(--bg)}
header{padding:18px max(24px,calc((100vw - 1320px)/2));background:#120d1c;border-color:var(--line);flex-wrap:wrap;gap:16px}h1{font-size:19px;color:var(--text);letter-spacing:-.5px}.brand-mark{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:#8b5cf6;color:white;font-size:22px;font-weight:800;box-shadow:0 4px 24px #8b5cf633}.brand-sub{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--purple)}#healthBadge{margin-left:auto;border:1px solid var(--line);padding:6px 12px;border-radius:99px;color:var(--ok);font-size:12px;min-height:32px}
.wrap{max-width:1320px;padding:32px 24px 64px}.intro{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:24px}.eyebrow{color:var(--purple);font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase}.intro h2{font-size:32px;line-height:1.2;letter-spacing:-1px;margin:8px 0 12px}.intro p{color:var(--muted);margin:0;max-width:600px}.workspace-tag{border:1px solid #674c85;color:#ddccfa;background:#251934;border-radius:8px;padding:8px 14px;white-space:nowrap;font-size:12px}.quick-nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}.quick-nav a{display:inline-flex;align-items:center;min-height:44px;padding:9px 16px;border:1px solid var(--line);border-radius:9px;color:var(--muted);text-decoration:none;background:#191222;font-weight:600;font-size:13px}.quick-nav a:hover{border-color:#a78bfa;color:white;background:#302044}
.grid{gap:24px}.card{min-width:0;border-color:var(--line);border-radius:16px;padding:24px;margin-bottom:0;box-shadow:0 12px 32px #00000020}.wrap>.card{margin-bottom:24px}.card h2{font-size:20px;letter-spacing:-.4px;margin:0 0 20px;display:flex;align-items:center;gap:12px}.card h2:before{content:"";width:4px;height:22px;background:#a78bfa;border-radius:4px}.card h3{font-size:15px;margin-top:24px}label{font-size:13px;color:#d8cce8;margin:0 0 6px;font-weight:500}.muted,.small{color:var(--muted);font-size:13px}.section-note{margin:-10px 0 22px;color:var(--muted);font-size:14px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}.field-wide{grid-column:1/-1}.field-grid>div{min-width:0}
input,textarea,select{background:#110d19;color:var(--text);border-color:#51415f;border-radius:9px;padding:11px 12px;font-family:inherit;font-size:14px;min-height:44px;margin:0;transition:border-color .16s,box-shadow .16s}input::placeholder,textarea::placeholder{color:#9d8eaf}input:hover,textarea:hover,select:hover{border-color:#8c70ac}input:focus,textarea:focus,select:focus{outline:2px solid #bda2ff;outline-offset:2px;border-color:#bda2ff;box-shadow:0 0 0 4px #8b5cf61a}textarea{height:80px;resize:vertical}button{min-height:44px;padding:10px 18px;border-radius:9px;color:#1c1031;background:var(--btn);font-size:13px;transition:background .16s,box-shadow .16s;touch-action:manipulation}button:hover{filter:none;background:#c4b5fd;box-shadow:0 3px 16px #8b5cf626}button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid #d2bdff;outline-offset:3px}.secondary{background:#30233f;color:#e8def6;border:1px solid #57426d}.secondary:hover{background:#433055}.danger{background:#642836;color:#ffe0e5;border:1px solid #b45b6b}.danger:hover{background:#7e3446}.row{gap:12px;align-items:end;margin-bottom:16px}.row>*{min-width:0}.row>button{flex:0 0 auto}.row>div>label{margin-top:0}.toolbar{gap:10px;margin-top:12px}.toolbar button{min-width:130px}#btnCreate{background:#8b5cf6;color:#fff;padding-inline:28px}#btnCreate:hover{background:#7c3aed}.status{border:1px solid #48325c;background:#120d1c;padding:13px 16px;border-radius:10px;font-size:13px;min-height:48px;overflow-wrap:anywhere}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:#f4cd88}pre{background:#100b18;border-color:var(--line);color:#d8c5fa;padding:16px;font-size:13px;overflow-wrap:anywhere}details{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-top:20px}summary{cursor:pointer;color:var(--purple);font-size:14px;font-weight:600;min-height:28px}details[open] summary{margin-bottom:18px}.tableBox{background:#120d1c;border-color:var(--line);border-radius:12px}table{font-size:13px;font-variant-numeric:tabular-nums}td,th{padding:12px;border-color:#352940}th{color:#d5baff}.tableBox thead th{background:#251a34}tbody tr:hover{background:#22162f}code{color:#d8c5fa}#table{overflow:auto}#token{min-width:220px}.token-row input{flex:1 1 auto}.token-row{margin-top:6px}.token-row #btnSaveToken{background:#30233f;color:#e8def6;border:1px solid #57426d}
@media(max-width:900px){header{padding:14px 20px}.intro{align-items:start}.intro h2{font-size:28px}.workspace-tag{display:none}.row{flex-wrap:wrap;flex-direction:row;align-items:end}.row>input{flex-basis:100%}.row>select,.row>div{flex:1 1 180px}.row>button{flex:1 1 auto}.token-row input{flex-basis:100%}.wrap{padding:24px 16px}.card{padding:20px}}
@media(max-width:540px){header{gap:10px}.brand-sub{display:none}h1{font-size:16px}.brand-mark{width:32px;height:32px}#healthBadge{font-size:11px;padding:4px 8px}.intro h2{font-size:26px}.field-grid{grid-template-columns:1fr;gap:16px}.field-wide{grid-column:auto}.card{padding:18px}.quick-nav{gap:6px}.quick-nav a{flex:1 1 40%;justify-content:center;font-size:12px}.row>div{flex-basis:100%}#token{min-width:0}input,textarea,select{font-size:16px}.toolbar button{flex:1 1 auto}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
</style>
</head><body><header><span class="brand-mark" aria-hidden="true">R</span><div><h1>RemiX Duo</h1><div class="brand-sub">License Console</div></div><span id="healthBadge" class="muted" role="status">Chưa kết nối</span></header><main class="wrap" id="main">
<section class="intro"><div><span class="eyebrow">Không gian quản trị</span><h2>Quản lý bản quyền Duo</h2><p>Cấp license, duyệt yêu cầu kích hoạt và quản lý thiết bị trong một không gian.</p></div><span class="workspace-tag">RemiX Audio · Duo</span></section>
<nav class="quick-nav" aria-label="Điều hướng quản trị"><a href="#issue">Cấp license</a><a href="#requests">Yêu cầu kích hoạt</a><a href="#licenses">Kho license</a><a href="#devices">Thiết bị</a></nav>
<div class="card" id="connection">
  <label for="token">Kết nối quản trị · Admin Token</label>
  <div class="row token-row"><input id="token" type="password" autocomplete="current-password" placeholder="Nhập Admin Token của Duo"><button id="btnSaveToken">Lưu token</button><button id="btnHealth" class="secondary">Test kết nối</button><button id="btnLoad" class="secondary">Tải danh sách</button></div>
  <div id="status" class="status muted" role="status" aria-live="polite">Nhập token và kiểm tra kết nối để bắt đầu quản lý license.</div>
</div>
<div class="grid">
<div class="card" id="issue" style="grid-column:1/-1"><h2>Cấp license mới</h2><p class="section-note">Thông tin khách hàng và thiết bị cần kích hoạt.</p>
<div class="field-grid"><div><label for="customerName">Tên khách hàng</label><input id="customerName" placeholder="VD: Hùng Quảng" autocomplete="name"></div>
<div><label for="customerPhone">Số điện thoại / License ID</label><input id="customerPhone" placeholder="VD: 0795718440"></div>
<div class="field-wide"><label for="hwIds">HW ID / Machine Code</label><textarea id="hwIds" placeholder="DUO2-… · Nhập mã máy, cách nhau bằng dấu phẩy"></textarea></div></div>
<div class="muted small">Mỗi HWID chỉ được có 1 license còn hiệu lực cho cùng edition. Nâng Pro lên Suite được phép tạo thêm license PREMIUM cùng HWID; còn gia hạn cùng gói thì dùng nút Gia hạn hoặc Đổi hạn.</div>
<div class="row"><div><label>Platform</label><select id="platform"><option>WIN</option><option>MAC</option><option>ANY</option></select></div><div><label>FPV</label><select id="fpv"><option>3</option><option>2</option><option>4</option></select></div><div><label>Max Rebind</label><input id="maxRebind" value="3"></div></div>
<div class="row"><div><label>Gói/Edition</label><select id="plan"><option>PRO</option><option>BASIC</option><option>PREMIUM</option><option>LIFETIME</option><option>TRIAL</option></select></div><div><label>Days</label><input id="days" value="365"></div><div><label>Giá/thu</label><input id="price" placeholder="VD: 1500000"></div></div>
<details><summary>Tùy chọn nâng cao · Tính năng, mã đơn và ghi chú</summary><div class="field-grid">
<div class="field-wide"><label for="features">Tính năng</label><input id="features" value="${DEFAULT_FEATURES.join(',')}"></div>
<div><label for="orderCode">Mã đơn</label><input id="orderCode" placeholder="Mã đơn"></div>
<div><label for="note">Ghi chú</label><textarea id="note" placeholder="Ghi chú nội bộ"></textarea></div></div></details>
<br><div class="toolbar"><button id="btnCreate">Ký & lưu license</button><button id="btnClear" class="secondary">Xóa form</button></div>
<h3>Token vừa tạo</h3><pre id="tokenOut">Chưa tạo.</pre><div class="toolbar"><button id="btnCopy" class="secondary">Copy token</button><button id="btnDownload" class="secondary">Tải file .lic</button></div>
</div>
<div class="card" id="licenses" style="grid-column:1/-1"><h2>Kho license</h2><div class="row"><input id="search" aria-label="Tìm license" placeholder="Tên, SĐT, HWID, License ID…"><button id="btnSearch">Tìm</button><button id="btnExportCsv" class="secondary">Xuất CSV</button><button id="btnExportLedger" class="secondary">Tải ledger TXT</button></div><div id="table" style="margin-top:10px"></div></div>


<div class="card" id="requests" style="grid-column:1/-1">
  <h2>Yêu cầu kích hoạt từ app</h2>
  <div class="row">
    <input id="requestSearch" placeholder="Tìm yêu cầu: SĐT/license, HWID, tên máy, app...">
    <select id="requestStatus">
      <option value="PENDING" selected>Đang chờ</option>
      <option value="ALL">Tất cả</option>
      <option value="APPROVED">Đã xử lý</option>
      <option value="REJECTED">Từ chối</option>
    </select>
    <select id="requestLimit"><option value="50">50 yêu cầu mới nhất</option><option value="100" selected>100 yêu cầu mới nhất</option><option value="300">300 yêu cầu mới nhất</option><option value="1000">1000 yêu cầu mới nhất</option></select>
    <button id="btnLoadRequests" class="secondary">Tải yêu cầu</button>
  </div>
  <div class="muted small" style="margin-top:8px">Khi user nhập SĐT/License ID trong app và bấm Kích hoạt online nhưng chưa có license, app sẽ gửi yêu cầu lên đây. Admin bấm Nạp form để cấp license đúng SĐT + HWID.</div>
  <div id="requestSummary" class="muted small" style="margin-top:6px">Chưa tải yêu cầu.</div>
  <div class="tableBox" style="margin-top:10px"><div id="requestTable"><div class="muted" style="padding:10px">Chưa tải danh sách yêu cầu.</div></div></div>
</div>

<div class="card" id="devices" style="grid-column:1/-1">
  <h2>Thiết bị đã kích hoạt</h2>
  <div class="row">
    <input id="activationSearch" placeholder="Tìm thiết bị: tên khách, SĐT, license, machine hash, tên máy...">
    <select id="activationLimit"><option value="50">50 máy mới nhất</option><option value="100" selected>100 máy mới nhất</option><option value="300">300 máy mới nhất</option><option value="1000">1000 máy mới nhất</option></select>
    <button id="btnLoadActivations" class="secondary">Tải thiết bị</button>
  </div>
  <div class="muted small" style="margin-top:8px">Bảng này có khung cuộn riêng, không làm web kéo dài xuống khi có nhiều máy. Mặc định chỉ tải 100 máy mới nhất; dùng ô tìm kiếm để lọc nhanh. Nút Xóa máy sẽ xóa hẳn dòng active khỏi database.</div>
  <div id="activationSummary" class="muted small" style="margin-top:6px">Chưa tải thiết bị.</div>
  <div class="tableBox" style="margin-top:10px"><div id="activationTable"><div class="muted" style="padding:10px">Chưa tải danh sách thiết bị.</div></div></div>
</div>
</div></main>
<script>
(function(){
'use strict';
const DEFAULT_FEATURES = ${JSON.stringify(DEFAULT_FEATURES)};
const $ = (id)=>document.getElementById(id);
document.querySelectorAll('label:not([for])').forEach(label=>{const field=label.nextElementSibling;if(field&&field.id)label.htmlFor=field.id;});
[['requestSearch','Tìm yêu cầu kích hoạt'],['requestStatus','Trạng thái yêu cầu'],['requestLimit','Số yêu cầu hiển thị'],['activationSearch','Tìm thiết bị'],['activationLimit','Số thiết bị hiển thị']].forEach(([id,name])=>$(id).setAttribute('aria-label',name));
let lastToken = '';
let lastLicenseName = 'remix_license.lic';
function setStatus(msg, cls='muted'){ $('status').innerHTML='<span class="'+cls+'">'+esc(msg)+'</span>'; }
function saveToken(){ const v=$('token').value.trim(); if(v) localStorage.setItem('adminToken',v); setStatus(v?'Đã lưu token trên trình duyệt này.':'Chưa nhập Admin Token.', v?'ok':'warn'); }
$('token').value=localStorage.getItem('adminToken')||'';
async function api(path, opt={}){
  const t=($('token').value||localStorage.getItem('adminToken')||'').trim();
  const headers = Object.assign({'authorization':'Bearer '+t}, opt.headers||{});
  if(opt.body && !headers['content-type']) headers['content-type']='application/json';
  let r, text, j;
  try{ r=await fetch(path,Object.assign({},opt,{headers})); }
  catch(e){ throw new Error('Không gọi được Worker API: '+e.message); }
  text = await r.text();
  try{ j = text ? JSON.parse(text) : {}; }catch(e){ throw new Error('API trả về không phải JSON. HTTP '+r.status+': '+text.slice(0,300)); }
  if(!r.ok || j.ok===false) {
    let msg = j.error || ('HTTP '+r.status);
    if(j.status==='DUPLICATE_HWID'){
      msg += '\\nHWID trùng: ' + (j.duplicate_hwid || '');
      msg += '\\nLicense cũ: ' + (j.existing_license_id || '');
      msg += '\\nGói cũ: ' + (j.existing_plan || j.existing_edition || '');
      msg += '\\nKhách: ' + (j.existing_customer_name || '');
      msg += '\\nSĐT: ' + (j.existing_customer_phone || '');
    }
    throw new Error(msg);
  }
  return j;
}
async function health(){
  try{ saveToken(); setStatus('Đang kiểm tra kết nối...', 'muted'); const j=await api('/api/admin/health'); if(j.db!=='OK'||j.privateKey!=='OK')throw new Error('Hệ thống cấp license chưa sẵn sàng. Vui lòng kiểm tra cấu hình server.'); $('healthBadge').textContent='Đã kết nối'; setStatus('Kết nối thành công. Hệ thống đã sẵn sàng cấp và quản lý license Duo.', 'ok'); }
  catch(e){ $('healthBadge').textContent=' • lỗi'; setStatus('Lỗi test kết nối: '+e.message, 'bad'); }
}
function formBody(){
  return {customerName:$('customerName').value.trim(),customerPhone:$('customerPhone').value.trim(),hwIds:$('hwIds').value.trim(),platform:$('platform').value,fpv:Number($('fpv').value),maxRebind:Number($('maxRebind').value),plan:$('plan').value,edition:$('plan').value,days:Number($('days').value),price:$('price').value.trim(),features:$('features').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),orderCode:$('orderCode').value.trim(),note:$('note').value.trim()};
}
async function createLicense(){
  try{ saveToken(); const body=formBody(); if(!body.customerName) throw new Error('Tên khách không được trống.'); if(!body.hwIds) throw new Error('HW ID không được trống.'); setStatus('Đang ký license...', 'muted'); const j=await api('/api/admin/licenses',{method:'POST',body:JSON.stringify(body)}); lastToken=j.license.token; lastLicenseName=(j.license.customerPhone||j.license.licenseId||'remix_license').replace(/[^a-zA-Z0-9_-]+/g,'_')+'.lic'; $('tokenOut').textContent=lastToken; setStatus('Đã ký license cho '+j.license.customerName+' — có thể Copy hoặc Tải .lic', 'ok'); await loadAll(false); }
  catch(e){ setStatus('Lỗi ký license: '+e.message, 'bad'); }
}
async function loadAll(showOk=true){
  try{ saveToken(); const q=encodeURIComponent($('search').value||''); const j=await api('/api/admin/licenses?q='+q); const rows=j.results||[]; $('table').innerHTML='<table><thead><tr><th>Ngày</th><th>Khách</th><th>SĐT/ID</th><th>HWID</th><th>Gói</th><th>Hạn</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>'+rows.map(r=>{let exp=Number(r.exp||0); let expTxt=exp===0?'Vĩnh viễn':new Date(exp*1000).toLocaleDateString('vi-VN'); return '<tr><td>'+esc(r.created_at)+'</td><td>'+esc(r.customer_name)+'</td><td>'+esc(r.customer_phone||r.license_id)+'</td><td>'+esc(r.hw_ids_json)+'</td><td>'+esc(r.plan)+'</td><td>'+expTxt+'</td><td>'+esc(r.status)+'</td><td class="nowrap"><button class="secondary" data-token="'+esc(r.id)+'">Token</button> <button class="secondary" data-fill="'+esc(r.id)+'">Nạp</button> <button class="secondary" data-renew-license="'+esc(r.id)+'">Gia hạn</button> <button class="secondary" data-set-expiry="'+esc(r.id)+'">Đổi hạn</button> <button class="danger" data-revoke="'+esc(r.id)+'">Khóa</button> <button class="danger" data-delete-license="'+esc(r.id)+'">Xóa</button></td></tr>';}).join('')+'</tbody></table>'; if(showOk) setStatus('Đã tải '+rows.length+' license.', 'ok'); }
  catch(e){ setStatus('Lỗi tải danh sách: '+e.message, 'bad'); }
}
async function getLicense(id){ return await api('/api/admin/licenses/'+encodeURIComponent(id)); }
async function showToken(id){ try{ const j=await getLicense(id); lastToken=j.license.token; lastLicenseName=(j.license.customer_phone||j.license.license_id||'remix_license').replace(/[^a-zA-Z0-9_-]+/g,'_')+'.lic'; $('tokenOut').textContent=lastToken; setStatus('Đã nạp token của '+(j.license.customer_name||id), 'ok'); }catch(e){ setStatus('Lỗi lấy token: '+e.message, 'bad'); } }
async function fillLicense(id){ try{ const j=await getLicense(id); const r=j.license; $('customerName').value=r.customer_name||''; $('customerPhone').value=r.customer_phone||r.license_id||''; $('hwIds').value=JSON.parse(r.hw_ids_json||'[]').join(','); $('platform').value=r.platform||'WIN'; $('fpv').value=String(r.fpv||3); $('maxRebind').value=String(r.max_rebind||3); $('plan').value=r.plan||r.edition||'PRO'; $('days').value=String(r.days||365); $('price').value=r.price||''; $('features').value=JSON.parse(r.features_json||'[]').join(','); $('orderCode').value=r.order_code||''; $('note').value=r.note||''; await showToken(id); }catch(e){ setStatus('Lỗi nạp form: '+e.message, 'bad'); } }
function fmtDateTime(v){
  if(!v) return '--';
  try { return new Date(v).toLocaleString('vi-VN'); }
  catch(e){ return String(v); }
}
function activationStatusText(r){
  if(r.revoked_at) return 'REVOKED';
  if(r.released_at) return 'RELEASED';
  return r.activation_status || 'ACTIVE';
}
function requestStatusText(s){
  s=String(s||'').toUpperCase();
  if(s==='PENDING') return 'ĐANG CHỜ';
  if(s==='APPROVED') return 'ĐÃ XỬ LÝ';
  if(s==='REJECTED') return 'TỪ CHỐI';
  return s || '--';
}
async function loadActivationRequests(showOk=true){
  try{
    const box=$('requestTable');
    const summary=$('requestSummary');
    if(!box) return;
    saveToken();
    const q=encodeURIComponent(($('requestSearch') && $('requestSearch').value) || '');
    const st=encodeURIComponent(($('requestStatus') && $('requestStatus').value) || 'PENDING');
    const limit=encodeURIComponent(($('requestLimit') && $('requestLimit').value) || '100');
    box.innerHTML='<div class="muted" style="padding:10px">Đang tải yêu cầu kích hoạt...</div>';
    if(summary) summary.textContent='Đang tải yêu cầu kích hoạt...';
    const j=await api('/api/admin/activation-requests?q='+q+'&status='+st+'&limit='+limit);
    const rows=j.results||[];
    if(!rows.length){
      box.innerHTML='<div class="muted" style="padding:10px">Không có yêu cầu phù hợp.</div>';
      if(summary) summary.textContent='Đang hiển thị 0 yêu cầu.';
      if(showOk) setStatus('Không có yêu cầu kích hoạt phù hợp.', 'warn');
      return;
    }
    box.innerHTML='<table><thead><tr>'+
      '<th>STT</th><th>Ngày gửi</th><th>SĐT / License</th><th>Machine Hash</th><th>Tên máy</th><th>App</th><th>Edition</th><th>Lần gửi</th><th>Trạng thái</th><th>Ghi chú</th><th>Thao tác</th>'+
      '</tr></thead><tbody>'+rows.map((r, idx)=>{
        return '<tr>'+
          '<td class="nowrap">'+String(idx+1)+'</td>'+
          '<td class="nowrap">'+esc(fmtDateTime(r.updated_at || r.created_at))+'<br><span class="muted">Tạo: '+esc(fmtDateTime(r.created_at))+'</span></td>'+
          '<td class="nowrap"><b>'+esc(r.license_input||'')+'</b><br><span class="muted">'+esc(r.customer_phone||'')+'</span></td>'+
          '<td><code>'+esc(r.machine_hash||'')+'</code></td>'+
          '<td>'+esc(r.machine_label||'')+'</td>'+
          '<td class="nowrap">'+esc(r.app_version||'')+'</td>'+
          '<td class="nowrap">'+esc(r.client_edition||'PRO')+'</td>'+
          '<td class="nowrap">'+esc(r.request_count||1)+'</td>'+
          '<td class="nowrap">'+esc(requestStatusText(r.status))+'</td>'+
          '<td>'+esc(r.client_note||r.admin_note||'')+'</td>'+
          '<td class="nowrap">'+
            '<button class="secondary" data-req-fill="'+esc(r.id)+'" data-req-phone="'+esc(r.license_input||r.customer_phone||'')+'" data-req-hwid="'+esc(r.machine_hash||'')+'" data-req-label="'+esc(r.machine_label||'')+'" data-req-edition="'+esc(r.client_edition||'PRO')+'">Nạp form</button> '+
            '<button class="secondary" data-req-approve="'+esc(r.id)+'">Đã xử lý</button> '+
            '<button class="danger" data-req-reject="'+esc(r.id)+'">Từ chối</button> '+
            '<button class="danger" data-req-delete="'+esc(r.id)+'">Xóa</button>'+
          '</td>'+
        '</tr>';
      }).join('')+'</tbody></table>';
    if(summary) summary.textContent='Đang hiển thị '+rows.length+' yêu cầu / giới hạn tải '+decodeURIComponent(limit)+' dòng.';
    if(showOk) setStatus('Đã tải '+rows.length+' yêu cầu kích hoạt.', 'ok');
  }catch(e){
    const box=$('requestTable');
    const summary=$('requestSummary');
    if(box) box.innerHTML='<div class="bad" style="padding:10px">Lỗi tải yêu cầu kích hoạt: '+esc(e.message)+'</div>';
    if(summary) summary.textContent='Lỗi tải yêu cầu kích hoạt.';
    setStatus('Lỗi tải yêu cầu kích hoạt: '+e.message, 'bad');
  }
}
function fillActivationRequestFromButton(el){
  const phone=el.getAttribute('data-req-phone')||'';
  const hwid=el.getAttribute('data-req-hwid')||'';
  const label=el.getAttribute('data-req-label')||'';
  const edition=(el.getAttribute('data-req-edition')||'PRO').toUpperCase();
  $('customerPhone').value=phone;
  $('hwIds').value=hwid;
  if(hwid.toUpperCase().startsWith('DUOM4-')){$('platform').value='MAC';$('fpv').value='4';}
  else if(hwid.toUpperCase().startsWith('DUO2-')){$('platform').value='WIN';$('fpv').value='3';}
  $('plan').value=(edition==='PREMIUM'||edition==='SUITE'||edition==='LUX')?'PREMIUM':'PRO';
  if(!$('customerName').value.trim()) $('customerName').value=phone || 'Khách mới';
  const oldNote=$('note').value.trim();
  $('note').value=(oldNote?oldNote+'\\n':'')+'Yêu cầu kích hoạt từ app. Máy: '+label+' | HWID: '+hwid;
  setStatus('Đã nạp SĐT/HWID từ yêu cầu vào form cấp license. Kiểm tra thông tin rồi bấm Ký & lưu license.', 'ok');
  window.scrollTo({top:0, behavior:'smooth'});
}
async function setActivationRequestStatus(id, status){
  try{
    const label=status==='APPROVED'?'đã xử lý':'từ chối';
    if(!confirm('Đánh dấu yêu cầu này là '+label+'?')) return;
    await api('/api/admin/activation-requests/'+encodeURIComponent(id)+'/'+(status==='APPROVED'?'approve':'reject'),{method:'POST',body:JSON.stringify({})});
    setStatus('Đã cập nhật yêu cầu kích hoạt.', 'ok');
    await loadActivationRequests(false);
  }catch(e){ setStatus('Lỗi cập nhật yêu cầu: '+e.message, 'bad'); }
}
async function deleteActivationRequest(id){
  try{
    if(!confirm('Xóa hẳn yêu cầu kích hoạt này khỏi database?')) return;
    await api('/api/admin/activation-requests/'+encodeURIComponent(id),{method:'DELETE'});
    setStatus('Đã xóa yêu cầu kích hoạt.', 'ok');
    await loadActivationRequests(false);
  }catch(e){ setStatus('Lỗi xóa yêu cầu: '+e.message, 'bad'); }
}
async function loadActivations(showOk=true){
  try{
    const box=$('activationTable');
    const summary=$('activationSummary');
    if(!box) return;
    saveToken();
    const searchBox=$('activationSearch');
    const q=encodeURIComponent((searchBox && searchBox.value) ? searchBox.value : ($('search').value||''));
    const limSel=$('activationLimit');
    const limit=encodeURIComponent((limSel && limSel.value) ? limSel.value : '100');
    box.innerHTML='<div class="muted" style="padding:10px">Đang tải thiết bị...</div>';
    if(summary) summary.textContent='Đang tải danh sách thiết bị...';
    const j=await api('/api/admin/activations?q='+q+'&limit='+limit);
    const rows=j.results||[];
    if(!rows.length){
      box.innerHTML='<div class="muted" style="padding:10px">Không có thiết bị phù hợp.</div>';
      if(summary) summary.textContent='Đang hiển thị 0 thiết bị.';
      if(showOk) setStatus('Không có thiết bị phù hợp.', 'warn');
      return;
    }
    box.innerHTML='<table><thead><tr>'+
      '<th>STT</th><th>Khách</th><th>License</th><th>Machine Hash</th><th>Tên máy</th><th>App</th><th>First Seen</th><th>Last Seen</th><th>License</th><th>Thiết bị</th><th>Thao tác</th>'+
      '</tr></thead><tbody>'+rows.map((r, idx)=>{
        let exp=Number(r.exp||0);
        let expTxt=exp===0?'Vĩnh viễn':new Date(exp*1000).toLocaleDateString('vi-VN');
        let devStatus=activationStatusText(r);
        return '<tr>'+
          '<td class="nowrap">'+String(idx+1)+'</td>'+
          '<td class="nowrap">'+esc(r.customer_name||'')+'<br><span class="muted">'+esc(r.customer_phone||'')+'</span></td>'+
          '<td class="nowrap">'+esc(r.license_id||'')+'<br><span class="muted">'+esc(r.plan||r.edition||'')+' / '+esc(expTxt)+'</span></td>'+
          '<td><code>'+esc(r.machine_hash||'')+'</code></td>'+
          '<td>'+esc(r.machine_label||'')+'</td>'+
          '<td class="nowrap">'+esc(r.app_version||'')+'</td>'+
          '<td class="nowrap">'+esc(fmtDateTime(r.first_seen_at))+'</td>'+
          '<td class="nowrap">'+esc(fmtDateTime(r.last_seen_at))+'</td>'+
          '<td class="nowrap">'+esc(r.license_status||'')+'</td>'+
          '<td class="nowrap">'+esc(devStatus)+'</td>'+
          '<td class="nowrap"><button class="secondary" data-act-release="'+esc(r.id)+'">Gỡ máy</button> <button class="danger" data-act-revoke="'+esc(r.id)+'">Khóa máy</button> <button class="danger" data-act-delete="'+esc(r.id)+'">Xóa máy</button></td>'+
        '</tr>';
      }).join('')+'</tbody></table>';
    const filterTxt = decodeURIComponent(q || '').trim();
    const limitTxt = decodeURIComponent(limit || '100');
    if(summary) summary.textContent = 'Đang hiển thị ' + rows.length + ' thiết bị' + (filterTxt ? ' theo bộ lọc: "' + filterTxt + '"' : '') + ' / giới hạn tải ' + limitTxt + ' dòng. Cột STT là thứ tự trong danh sách đang lọc.';
    if(showOk) setStatus('Đã tải '+rows.length+' thiết bị kích hoạt.', 'ok');
  }catch(e){
    setStatus('Lỗi tải thiết bị: '+e.message, 'bad');
  }
}
async function releaseActivation(id){
  try{
    if(!confirm('Gỡ kích hoạt máy này? Máy này sẽ được giải phóng slot active.')) return;
    await api('/api/admin/activations/'+encodeURIComponent(id)+'/release',{method:'POST'});
    setStatus('Đã gỡ kích hoạt thiết bị.', 'ok');
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi gỡ máy: '+e.message, 'bad'); }
}
async function revokeActivation(id){
  try{
    if(!confirm('Khóa riêng thiết bị này? Máy này sẽ không được activate lại.')) return;
    await api('/api/admin/activations/'+encodeURIComponent(id)+'/revoke',{method:'POST'});
    setStatus('Đã khóa thiết bị.', 'ok');
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi khóa máy: '+e.message, 'bad'); }
}
async function renewLicenseUi(id){
  try{
    const daysRaw = prompt('Nhập số ngày muốn GIA HẠN thêm cho license này. Ví dụ: 30, 90, 365', '365');
    if(daysRaw===null) return;
    const extraDays = Math.floor(Number(daysRaw));
    if(!Number.isFinite(extraDays) || extraDays < 1){
      setStatus('Số ngày gia hạn không hợp lệ.', 'bad');
      return;
    }
    if(!confirm('Gia hạn thêm '+extraDays+' ngày cho license này?')) return;

    const j = await api('/api/admin/licenses/'+encodeURIComponent(id)+'/renew',{
      method:'POST',
      body:JSON.stringify({extraDays})
    });

    lastToken = j.token || lastToken;
    if(j.token){
      $('tokenOut').textContent = j.token;
    }
    setStatus('Đã gia hạn thêm '+extraDays+' ngày. Hạn mới: '+(j.exp===0?'Vĩnh viễn':new Date(Number(j.exp)*1000).toLocaleDateString('vi-VN')), 'ok');
    await loadAll(false);
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi gia hạn: '+e.message, 'bad'); }
}

async function setLicenseExpiryUi(id){
  try{
    const daysRaw = prompt('Nhập số ngày còn lại muốn ĐỔI HẠN. Nhập 0 để đặt VĨNH VIỄN. Ví dụ: 7, 30, 365, 0', '365');
    if(daysRaw===null) return;
    const days = Math.floor(Number(daysRaw));
    if(!Number.isFinite(days) || days < 0){
      setStatus('Số ngày đổi hạn không hợp lệ.', 'bad');
      return;
    }
    const msg = days===0 ? 'Đặt license này thành VĨNH VIỄN?' : 'Đổi license này còn '+days+' ngày tính từ hôm nay?';
    if(!confirm(msg)) return;

    const j = await api('/api/admin/licenses/'+encodeURIComponent(id)+'/set-expiry',{
      method:'POST',
      body:JSON.stringify({days, permanent: days===0})
    });

    lastToken = j.token || lastToken;
    if(j.token){
      $('tokenOut').textContent = j.token;
    }
    setStatus('Đã đổi hạn license. Hạn mới: '+(j.exp===0?'Vĩnh viễn':new Date(Number(j.exp)*1000).toLocaleDateString('vi-VN')), 'ok');
    await loadAll(false);
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi đổi hạn: '+e.message, 'bad'); }
}
async function revoke(id){ try{ if(!confirm('Khóa license này?'))return; await api('/api/admin/licenses/'+encodeURIComponent(id)+'/revoke',{method:'POST'}); setStatus('Đã khóa license.', 'ok'); await loadAll(false); }catch(e){ setStatus('Lỗi khóa license: '+e.message, 'bad'); } }
async function deleteLicenseHard(id){
  try{
    if(!confirm('XÓA HẲN license này khỏi database? Hành động này sẽ xóa cả thiết bị đã active của license và không thể hoàn tác.')) return;
    if(!confirm('Xác nhận lần 2: xóa hẳn license này?')) return;
    await api('/api/admin/licenses/'+encodeURIComponent(id),{method:'DELETE'});
    setStatus('Đã xóa hẳn license và các thiết bị active liên quan.', 'ok');
    await loadAll(false);
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi xóa license: '+e.message, 'bad'); }
}
async function deleteActivationHard(id){
  try{
    if(!confirm('XÓA HẲN thiết bị này khỏi danh sách active? Hành động này chỉ xóa dòng thiết bị, không xóa license.')) return;
    await api('/api/admin/activations/'+encodeURIComponent(id),{method:'DELETE'});
    setStatus('Đã xóa hẳn thiết bị khỏi danh sách active.', 'ok');
    await loadActivations(false);
  }catch(e){ setStatus('Lỗi xóa máy: '+e.message, 'bad'); }
}
async function exportCsv(){ try{ const q=encodeURIComponent($('search').value||''); const r=await fetch('/api/admin/licenses.csv?q='+q,{headers:{authorization:'Bearer '+(($('token').value||localStorage.getItem('adminToken')||'').trim())}}); const text=await r.text(); if(!r.ok) throw new Error(text); downloadText(text,'remix_licenses.csv','text/csv;charset=utf-8'); setStatus('Đã xuất CSV.', 'ok'); }catch(e){ setStatus('Lỗi xuất CSV: '+e.message, 'bad'); } }
async function exportLedgerTxt(){ try{ const q=encodeURIComponent($('search').value||''); const r=await fetch('/api/admin/license_ledger.txt?q='+q,{headers:{authorization:'Bearer '+(($('token').value||localStorage.getItem('adminToken')||'').trim())}}); const text=await r.text(); if(!r.ok) throw new Error(text); downloadText(text,'license_ledger.txt','text/plain;charset=utf-8'); setStatus('Đã tải license_ledger.txt.', 'ok'); }catch(e){ setStatus('Lỗi tải ledger TXT: '+e.message, 'bad'); } }
function copyToken(){ const t=($('tokenOut').textContent||'').trim(); if(!t || t==='Chưa tạo.'){setStatus('Chưa có token để copy.','warn');return;} navigator.clipboard.writeText(t).then(()=>setStatus('Đã copy token.','ok')).catch(()=>setStatus('Không copy được, hãy copy thủ công.','bad')); }
function downloadLic(){ const t=($('tokenOut').textContent||'').trim(); if(!t || t==='Chưa tạo.'){setStatus('Chưa có token để tải.','warn');return;} downloadText(t,lastLicenseName||'remix_license.lic','text/plain;charset=utf-8'); setStatus('Đã tạo file .lic để tải.', 'ok'); }
function downloadText(text, filename, type){ const blob=new Blob([text],{type}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=filename; document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href); a.remove();},1000); }
function clearForm(){ ['customerName','customerPhone','hwIds','price','orderCode','note'].forEach(id=>$(id).value=''); $('days').value='365'; $('maxRebind').value='3'; $('plan').value='PRO'; $('features').value=DEFAULT_FEATURES.join(','); setStatus('Đã xóa form.', 'muted'); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function bind(){
  $('btnSaveToken').addEventListener('click', saveToken);
  $('btnHealth').addEventListener('click', health);
  $('btnLoad').addEventListener('click', ()=>{ loadAll(true); loadActivationRequests(false); loadActivations(false); });
  $('btnCreate').addEventListener('click', createLicense);
  $('btnClear').addEventListener('click', clearForm);
  $('btnSearch').addEventListener('click', ()=>{ loadAll(true); loadActivationRequests(false); loadActivations(false); });
  $('btnCopy').addEventListener('click', copyToken);
  $('btnDownload').addEventListener('click', downloadLic);
  $('btnExportCsv').addEventListener('click', exportCsv);
  $('btnExportLedger').addEventListener('click', exportLedgerTxt);
  if($('btnLoadRequests')) $('btnLoadRequests').addEventListener('click', ()=>loadActivationRequests(true));
  if($('requestSearch')) $('requestSearch').addEventListener('keydown', e=>{ if(e.key==='Enter') loadActivationRequests(true); });
  if($('requestStatus')) $('requestStatus').addEventListener('change', ()=>loadActivationRequests(true));
  if($('requestLimit')) $('requestLimit').addEventListener('change', ()=>loadActivationRequests(true));
  if($('btnLoadActivations')) $('btnLoadActivations').addEventListener('click', ()=>loadActivations(true));
  if($('activationSearch')) $('activationSearch').addEventListener('keydown', e=>{ if(e.key==='Enter') loadActivations(true); });
  if($('activationLimit')) $('activationLimit').addEventListener('change', ()=>loadActivations(true));
  $('search').addEventListener('keydown', e=>{if(e.key==='Enter'){loadAll(true);loadActivations(false);}});
  document.addEventListener('click', e=>{
    const el=e.target;
    if(!(el instanceof HTMLElement)) return;
    const id=el.getAttribute('data-token'); if(id) showToken(id);
    const fid=el.getAttribute('data-fill'); if(fid) fillLicense(fid);
    const renewId=el.getAttribute('data-renew-license'); if(renewId) renewLicenseUi(renewId);
    const setExpId=el.getAttribute('data-set-expiry'); if(setExpId) setLicenseExpiryUi(setExpId);
    const rid=el.getAttribute('data-revoke'); if(rid) revoke(rid);
    const delLic=el.getAttribute('data-delete-license'); if(delLic) deleteLicenseHard(delLic);
    const rel=el.getAttribute('data-act-release'); if(rel) releaseActivation(rel);
    const revDev=el.getAttribute('data-act-revoke'); if(revDev) revokeActivation(revDev);
    const delDev=el.getAttribute('data-act-delete'); if(delDev) deleteActivationHard(delDev);
    const reqFill=el.getAttribute('data-req-fill'); if(reqFill) fillActivationRequestFromButton(el);
    const reqApprove=el.getAttribute('data-req-approve'); if(reqApprove) setActivationRequestStatus(reqApprove, 'APPROVED');
    const reqReject=el.getAttribute('data-req-reject'); if(reqReject) setActivationRequestStatus(reqReject, 'REJECTED');
    const reqDelete=el.getAttribute('data-req-delete'); if(reqDelete) deleteActivationRequest(reqDelete);
  });
}
function duoPlatformProfile(){ if($('platform').value==='MAC') $('fpv').value='4'; else if($('fpv').value==='4') $('fpv').value='3'; }
$('platform').addEventListener('change',duoPlatformProfile);
$('hwIds').addEventListener('input',()=>{if($('hwIds').value.trim().toUpperCase().startsWith('DUOM4-')){$('platform').value='MAC';$('fpv').value='4';}});

bind();
if($('token').value) health();
})();

</script></body></html>`);
}

async function getLicenseById(request: Request, env: Env, id: string) {
  const row: any = await env.DB.prepare('SELECT * FROM licenses WHERE id=? LIMIT 1').bind(id).first();
  if (!row) return json({ ok: false, error: 'Không tìm thấy license.' }, 404);
  return json({ ok: true, license: row });
}
function parseJsonArraySafe(raw: any): string[] {
  try {
    const arr = JSON.parse(String(raw || '[]'));
    return Array.isArray(arr) ? arr.map(x => String(x).trim()).filter(Boolean) : [];
  } catch {
    return [];
  }
}

function normalizeMachineHash(raw: any): string {
  const s = String(raw || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9._:-]/g, '');

  if (!s) throw new Error('machine_hash không được trống.');
  if (s.length < 8) throw new Error('machine_hash quá ngắn.');
  if (s.length > 256) throw new Error('machine_hash quá dài.');
  return s;
}

function offlineGraceDays(env: Env): number {
  const n = Math.floor(Number(env.PUBLIC_OFFLINE_GRACE_DAYS || 14));
  return Math.max(1, Math.min(90, n));
}

function isLicenseExpired(lic: any): boolean {
  const exp = Number(lic.exp || 0);
  return exp > 0 && exp < nowTs();
}

function maxActiveDevices(lic: any): number {
  // Tạm dùng max_rebind làm giới hạn số máy active.
  // Sau này nếu muốn tách riêng, thêm cột max_devices.
  const n = Math.floor(Number(lic.max_rebind || 1));
  return Math.max(1, Math.min(99, n));
}

function requestedClientEdition(input: any): string {
  return normalizeLicenseEdition(
    input?.client_edition ||
    input?.app_edition ||
    input?.edition ||
    input?.plan ||
    'PRO'
  );
}

function publicLicenseError(status: string, reason: string, httpStatus = 400, extra: Record<string, any> = {}) {
  const err: any = new Error(reason);
  err.publicLicenseError = true;
  err.httpStatus = httpStatus;
  err.response = { ok: false, status, reason, error: reason, ...extra };
  return err;
}

function publicLicenseErrorResponse(e: any): Response | null {
  if (!e?.publicLicenseError || !e.response) return null;
  return json(e.response, Number(e.httpStatus || 400));
}

async function findLicenseForClient(env: Env, input: any): Promise<any> {
  const key = String(
    input.license_id ||
    input.licenseId ||
    input.key ||
    input.customer_phone ||
    input.phone ||
    ''
  ).trim();

  if (!key) throw new Error('Thiếu license_id hoặc key.');

  const requestedEdition = requestedClientEdition(input);
  const rows = await env.DB.prepare(`
    SELECT * FROM licenses
    WHERE license_id = ? OR customer_phone = ?
    ORDER BY created_at DESC
    LIMIT 50
  `).bind(key, key).all();

  const results = Array.isArray((rows as any)?.results) ? (rows as any).results : [];
  if (!results.length) throw new Error('Không tìm thấy license.');

  // Exact license IDs stay exact. Phone lookups may return both WIN and MAC.
  const exact = results.filter((lic: any) => String(lic.license_id || '') === key);
  const candidates = exact.length ? exact : results;
  const editionMatches = candidates.filter((lic: any) => licenseEditionFromRow(lic) === requestedEdition);
  if (editionMatches.length) {
    const machine = normalizeMachineHash(input.machine_hash || input.machineId || input.machine_id || input.hw_id);
    const profileMatches = editionMatches.filter((lic: any) => !clientProfileMismatch(lic, machine));
    if (!profileMatches.length) throw publicLicenseError('PLATFORM_MISMATCH', 'License không khớp platform/FPV của máy.', 403);
    const authorized = profileMatches.filter((lic: any) => macMachineAuthorized(lic, machine));
    if (!authorized.length) throw publicLicenseError('MACHINE_NOT_REGISTERED', 'Machine ID chưa được đăng ký cho license MAC này.', 403);
    return authorized[0];
  }

  const existing = candidates[0];
  const existingEdition = licenseEditionFromRow(existing);
  throw publicLicenseError(
    'EDITION_MISMATCH',
    `License/SĐT này đang là ${existingEdition}, không dùng được cho bản ${requestedEdition}.`,
    403,
    {
      requested_edition: requestedEdition,
      existing_edition: existingEdition,
      existing_license_id: existing.license_id,
      existing_plan: existing.plan || existing.edition || ''
    }
  );
}

function buildClientPayload(lic: any, machineHash: string): any {
  const features = parseJsonArraySafe(lic.features_json);
  const platform = String(lic.platform || 'WIN').toUpperCase();
  const fpv = Number(lic.fpv || 3);
  const edition = String(lic.edition || lic.plan || 'PRO').toUpperCase();
  const plan = String(lic.plan || edition || 'PRO').toUpperCase();
  const licenseId = String(lic.license_id || lic.id || '').trim();

  return {
    v: 3,
    fpv,
    platform,

    // Token trả về cho app được bind theo máy đang activate.
    hw_ids: [machineHash],
    machine_ids: [machineHash],
    machine: machineHash,
    machine_id: machineHash,

    lic_id: licenseId,
    edition,
    plan,
    features,

    name: lic.customer_name || '',
    customer_phone: lic.customer_phone || '',
    order_code: lic.order_code || '',

    iat: nowTs(),
    exp: Number(lic.exp || 0),
    max_rebind: Number(lic.max_rebind || 1),

    online: true,
    server: 'cloudflare-d1'
  };
}

function publicLicenseResponse(env: Env, lic: any, machineHash: string, signedToken: string, status = 'ACTIVE') {
  return {
    ok: true,
    status,
    license_id: lic.license_id,
    plan: lic.plan || lic.edition || 'PRO',
    edition: lic.edition || lic.plan || 'PRO',
    features: parseJsonArraySafe(lic.features_json),
    expires_at: Number(lic.exp || 0),
    offline_grace_days: offlineGraceDays(env),
    machine_hash: machineHash,
    signed_token: signedToken,
    server_time: nowTs()
  };
}

async function activateLicense(request: Request, env: Env) {
  try {
    return await activateLicenseImpl(request, env);
  } catch (e: any) {
    const businessError = publicLicenseErrorResponse(e);
    if (businessError) return businessError;

    const msg = String(e?.message || e || '');
    const detail = String(e?.stack || e?.message || e || 'Unknown activation error').slice(0, 1800);
    console.error('activateLicense exception:', detail);

    // Những lỗi nghiệp vụ bình thường phải trả JSON dễ hiểu,
    // không để Cloudflare/Worker hiện 500 làm app tưởng lỗi server.
    if (msg.includes('Không tìm thấy license')) {
      return json({
        ok: false,
        status: 'LICENSE_NOT_FOUND',
        reason: 'Không tìm thấy license. Hãy cấp license trên web admin trước, hoặc kiểm tra lại License ID / SĐT.',
        error: 'Không tìm thấy license.',
        detail: msg
      }, 404);
    }

    if (msg.includes('Thiếu license_id')) {
      return json({
        ok: false,
        status: 'MISSING_LICENSE_ID',
        reason: 'Thiếu License ID / SĐT.',
        error: 'Thiếu License ID / SĐT.',
        detail: msg
      }, 400);
    }

    if (msg.includes('machine_hash')) {
      return json({
        ok: false,
        status: 'BAD_MACHINE_HASH',
        reason: 'Machine Hash / HWID không hợp lệ.',
        error: 'Machine Hash / HWID không hợp lệ.',
        detail: msg
      }, 400);
    }

    return json({
      ok: false,
      status: 'ACTIVATE_EXCEPTION',
      error: 'Worker activate exception',
      detail
    }, 500);
  }
}

async function activateLicenseImpl(request: Request, env: Env) {
  const input: any = await request.json().catch(() => ({}));
  const machineHash = normalizeMachineHash(input.machine_hash || input.machineId || input.machine_id || input.hw_id);
  const machineLabel = String(input.machine_label || input.device_name || '').trim().slice(0, 120);
  const appVersion = String(input.app_version || '').trim().slice(0, 40);

  const lic = await findLicenseForClient(env, input);
  if (clientProfileMismatch(lic, machineHash)) {
    return json({ok:false,status:'PLATFORM_MISMATCH',reason:'License không khớp platform/FPV của máy.'},403);
  }
  if (!macMachineAuthorized(lic,machineHash)) {
    return json({ok:false,status:'MACHINE_NOT_REGISTERED',reason:'Machine ID chưa được đăng ký cho license MAC này.'},403);
  }

  if (String(lic.status || '').toUpperCase() !== 'ACTIVE') {
    return json({ ok: false, status: lic.status || 'INVALID', reason: 'LICENSE_NOT_ACTIVE' }, 403);
  }

  if (isLicenseExpired(lic)) {
    return json({ ok: false, status: 'EXPIRED', reason: 'LICENSE_EXPIRED', expires_at: Number(lic.exp || 0) }, 403);
  }

  const existing: any = await env.DB.prepare(`
    SELECT * FROM license_activations
    WHERE license_row_id = ? AND machine_hash = ?
    LIMIT 1
  `).bind(lic.id, machineHash).first();

  const t = nowIso();

  if (existing) {
    if (existing.revoked_at) {
      return json({ ok: false, status: 'REVOKED_DEVICE', reason: 'DEVICE_REVOKED' }, 403);
    }

    await env.DB.prepare(`
      UPDATE license_activations
      SET status='ACTIVE', machine_label=?, app_version=?, last_seen_at=?, released_at=NULL
      WHERE id=?
    `).bind(machineLabel, appVersion, t, existing.id).run();

    const token = signLicenseToken(env, buildClientPayload(lic, machineHash));
    await audit(env, 'license.activate.existing', { licenseRowId: lic.id, licenseId: lic.license_id, machineHash, appVersion }, 'client');

    return json(publicLicenseResponse(env, lic, machineHash, token, 'ACTIVE'));
  }

  const countRow: any = await env.DB.prepare(`
    SELECT COUNT(*) AS n
    FROM license_activations
    WHERE license_row_id = ?
      AND revoked_at IS NULL
      AND released_at IS NULL
      AND status = 'ACTIVE'
  `).bind(lic.id).first();

  const activeCount = Number(countRow?.n || 0);
  const limit = maxActiveDevices(lic);

  if (activeCount >= limit) {
    return json({
      ok: false,
      status: 'DEVICE_LIMIT_REACHED',
      reason: 'Đã đạt giới hạn số máy được kích hoạt.',
      active_devices: activeCount,
      max_devices: limit
    }, 403);
  }

  const activationId = uuid('ACT-');

  await env.DB.prepare(`
    INSERT INTO license_activations(
      id, license_row_id, license_id, machine_hash, machine_label,
      status, app_version, first_seen_at, last_seen_at, released_at, revoked_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(license_row_id, machine_hash) DO UPDATE SET
      status='ACTIVE',
      machine_label=excluded.machine_label,
      app_version=excluded.app_version,
      last_seen_at=excluded.last_seen_at,
      released_at=NULL
  `).bind(
    activationId,
    lic.id,
    lic.license_id,
    machineHash,
    machineLabel,
    'ACTIVE',
    appVersion,
    t,
    t,
    null,
    null
  ).run();

  const token = signLicenseToken(env, buildClientPayload(lic, machineHash));
  await audit(env, 'license.activate.new', { licenseRowId: lic.id, licenseId: lic.license_id, activationId, machineHash, appVersion }, 'client');

  return json(publicLicenseResponse(env, lic, machineHash, token, 'ACTIVE'));
}

async function verifyLicense(request: Request, env: Env) {
  const input: any = await request.json().catch(() => ({}));
  const machineHash = normalizeMachineHash(input.machine_hash || input.machineId || input.machine_id || input.hw_id);
  const appVersion = String(input.app_version || '').trim().slice(0, 40);

  const lic = await findLicenseForClient(env, input);
  if (clientProfileMismatch(lic, machineHash)) {
    return json({ok:false,status:'PLATFORM_MISMATCH',reason:'License không khớp platform/FPV của máy.'},403);
  }
  if (!macMachineAuthorized(lic,machineHash)) {
    return json({ok:false,status:'MACHINE_NOT_REGISTERED',reason:'Machine ID chưa được đăng ký cho license MAC này.'},403);
  }

  if (String(lic.status || '').toUpperCase() !== 'ACTIVE') {
    return json({ ok: false, status: lic.status || 'INVALID', reason: 'LICENSE_NOT_ACTIVE' }, 403);
  }

  if (isLicenseExpired(lic)) {
    return json({ ok: false, status: 'EXPIRED', reason: 'LICENSE_EXPIRED', expires_at: Number(lic.exp || 0) }, 403);
  }

  const act: any = await env.DB.prepare(`
    SELECT * FROM license_activations
    WHERE license_row_id = ? AND machine_hash = ?
    LIMIT 1
  `).bind(lic.id, machineHash).first();

  if (!act) {
    return json({ ok: false, status: 'NOT_ACTIVATED', reason: 'Máy này chưa được kích hoạt.' }, 403);
  }

  if (act.revoked_at) {
    return json({ ok: false, status: 'REVOKED_DEVICE', reason: 'Thiết bị này đã bị thu hồi.' }, 403);
  }

  if (act.released_at || String(act.status || '').toUpperCase() !== 'ACTIVE') {
    return json({ ok: false, status: 'RELEASED', reason: 'Thiết bị này đã được gỡ kích hoạt.' }, 403);
  }

  await env.DB.prepare(`
    UPDATE license_activations
    SET last_seen_at=?, app_version=?
    WHERE id=?
  `).bind(nowIso(), appVersion, act.id).run();

  const token = signLicenseToken(env, buildClientPayload(lic, machineHash));

  return json(publicLicenseResponse(env, lic, machineHash, token, 'ACTIVE'));
}

async function heartbeatLicense(request: Request, env: Env) {
  const input: any = await request.json().catch(() => ({}));
  const machineHash = normalizeMachineHash(input.machine_hash || input.machineId || input.machine_id || input.hw_id);
  const appVersion = String(input.app_version || '').trim().slice(0, 40);

  const lic = await findLicenseForClient(env, input);
  if (clientProfileMismatch(lic, machineHash)) {
    return json({ok:false,status:'PLATFORM_MISMATCH',reason:'License không khớp platform/FPV của máy.'},403);
  }
  if (!macMachineAuthorized(lic,machineHash)) {
    return json({ok:false,status:'MACHINE_NOT_REGISTERED',reason:'Machine ID chưa được đăng ký cho license MAC này.'},403);
  }

  const act: any = await env.DB.prepare(`
    SELECT * FROM license_activations
    WHERE license_row_id = ? AND machine_hash = ?
    LIMIT 1
  `).bind(lic.id, machineHash).first();

  if (!act) {
    return json({ ok: false, status: 'NOT_ACTIVATED', reason: 'Máy này chưa được kích hoạt.' }, 403);
  }

  if (String(lic.status || '').toUpperCase() !== 'ACTIVE') {
    return json({ ok: false, status: lic.status || 'INVALID', reason: 'LICENSE_NOT_ACTIVE' }, 403);
  }

  if (isLicenseExpired(lic)) {
    return json({ ok: false, status: 'EXPIRED', reason: 'LICENSE_EXPIRED', expires_at: Number(lic.exp || 0) }, 403);
  }

  if (act.revoked_at) {
    return json({ ok: false, status: 'REVOKED_DEVICE', reason: 'Thiết bị này đã bị thu hồi.' }, 403);
  }

  await env.DB.prepare(`
    UPDATE license_activations
    SET last_seen_at=?, app_version=?
    WHERE id=?
  `).bind(nowIso(), appVersion, act.id).run();

  return json({
    ok: true,
    status: 'ACTIVE',
    license_id: lic.license_id,
    machine_hash: machineHash,
    expires_at: Number(lic.exp || 0),
    offline_grace_days: offlineGraceDays(env),
    server_time: nowTs()
  });
}

async function releaseLicense(request: Request, env: Env) {
  const input: any = await request.json().catch(() => ({}));
  const machineHash = normalizeMachineHash(input.machine_hash || input.machineId || input.machine_id || input.hw_id);

  const lic = await findLicenseForClient(env, input);
  if (clientProfileMismatch(lic, machineHash)) {
    return json({ok:false,status:'PLATFORM_MISMATCH',reason:'License không khớp platform/FPV của máy.'},403);
  }
  if (!macMachineAuthorized(lic,machineHash)) {
    return json({ok:false,status:'MACHINE_NOT_REGISTERED',reason:'Machine ID chưa được đăng ký cho license MAC này.'},403);
  }

  const act: any = await env.DB.prepare(`
    SELECT * FROM license_activations
    WHERE license_row_id = ? AND machine_hash = ?
    LIMIT 1
  `).bind(lic.id, machineHash).first();

  if (!act) {
    return json({ ok: true, status: 'NOT_FOUND', message: 'Máy này chưa có activation trên server.' });
  }

  const t = nowIso();

  await env.DB.prepare(`
    UPDATE license_activations
    SET status='RELEASED', released_at=?, last_seen_at=?
    WHERE id=?
  `).bind(t, t, act.id).run();

  await audit(env, 'license.release', { licenseRowId: lic.id, licenseId: lic.license_id, machineHash }, 'client');

  return json({
    ok: true,
    status: 'RELEASED',
    license_id: lic.license_id,
    machine_hash: machineHash
  });
}

async function appInfo(request: Request, env: Env) {
  return json({
    ok: true,
    app_name: 'RemiX Duo',
    version: env.PUBLIC_LATEST_VERSION || '8.77',
    codename: env.PUBLIC_CODENAME || 'Duo',
    display_version: env.PUBLIC_DISPLAY_VERSION || 'RemiX Duo V8.77',
    installer_name: env.PUBLIC_INSTALLER_NAME || 'RemiXDuo_QA_Setup_V8.77.exe',
    installer_url: env.PUBLIC_INSTALLER_URL || '',
    sha256: env.PUBLIC_INSTALLER_SHA256 || '',
    server_time: nowTs()
  });
}
async function healthCheck(request: Request, env: Env) {
  let db = "FAIL";
  try {
    await env.DB.prepare("SELECT 1 AS ok").first();
    db = "OK";
  } catch (e: any) {
    db = "FAIL: " + (e?.message || e);
  }

  let privateKey = "MISSING";
  let rawLen = 0;
  let cleanLen = 0;
  let seedLen = 0;
  let keyError = "";

  try {
    const raw = env.ED25519_PRIVATE_SEED_B64 || "";
    rawLen = raw.length;

    const clean = String(raw).trim().replace(/\s+/g, "");
    cleanLen = clean.length;

    const seed = b64DecodeAny(clean);
    seedLen = seed.length;

    if (seed.length === 32) {
      privateKey = "OK";
    } else if (seed.length === 64) {
      privateKey = "OK_64_USING_FIRST32";
    } else {
      privateKey = "BAD_LENGTH_" + seed.length;
    }
  } catch (e: any) {
    privateKey = "BAD_BASE64";
    keyError = String(e?.message || e);
  }

  return json({
    ok: true,
    db,
    privateKey,
    rawLen,
    cleanLen,
    seedLen,
    keyError,
    time: nowIso()
  });
}

function safeTsv(v: any): string {
  return String(v ?? '')
    .replace(/\t/g, ' ')
    .replace(/\r?\n/g, ' ')
    .trim();
}

function fmtTsHuman(ts: any): string {
  const n = Number(ts || 0);
  if (!n) return 'Vĩnh viễn';
  try {
    return new Date(n * 1000).toLocaleString('vi-VN');
  } catch {
    return '';
  }
}

function parseJsonArrayText(raw: any): string {
  try {
    const arr = JSON.parse(String(raw || '[]'));
    return Array.isArray(arr) ? arr.join(',') : String(raw || '');
  } catch {
    return String(raw || '');
  }
}

async function exportLicenseLedgerTxt(request: Request, env: Env) {
  const url = new URL(request.url);
  const qRaw = (url.searchParams.get('q') || '').trim();
  const q = `%${qRaw}%`;

  const rows = await env.DB.prepare(`SELECT * FROM licenses
    WHERE id LIKE ? OR license_id LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?
       OR hw_ids_json LIKE ? OR order_code LIKE ? OR note LIKE ?
    ORDER BY created_at DESC LIMIT 5000`)
    .bind(q, q, q, q, q, q, q)
    .all();

  const header = [
    'STT', 'Platform', 'FPV', 'HwIDs', 'LicenseID', 'TenKhach', 'SDT',
    'Days', 'IAT', 'EXP', 'IAT_H', 'EXP_H', 'MaxRebind',
    'Plan', 'Features', 'Price', 'OrderCode', 'Status', 'Note'
  ];

  const lines = [header.join('\t')];

  for (const [idx, r] of ((rows.results || []) as any[]).entries()) {
    const exp = Number(r.exp || 0);
    const iat = Number(r.iat || 0);

    lines.push([
      idx + 1,
      r.platform,
      r.fpv,
      parseJsonArrayText(r.hw_ids_json),
      r.license_id,
      r.customer_name,
      r.customer_phone,
      r.days,
      iat,
      exp,
      fmtTsHuman(iat),
      exp === 0 ? 'Vĩnh viễn' : fmtTsHuman(exp),
      r.max_rebind,
      r.plan,
      parseJsonArrayText(r.features_json),
      r.price,
      r.order_code,
      r.status,
      r.note
    ].map(safeTsv).join('\t'));
  }

  return new Response(lines.join('\n'), {
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'content-disposition': 'attachment; filename="license_ledger.txt"'
    }
  });
}

async function listActivations(request: Request, env: Env) {
  const url = new URL(request.url);
  const qRaw = (url.searchParams.get('q') || '').trim();
  const q = `%${qRaw}%`;
  const limit = Math.min(1000, Math.max(1, Number(url.searchParams.get('limit') || 100)));

  const rows = await env.DB.prepare(`
    SELECT
      a.id,
      a.license_row_id,
      a.license_id,
      a.machine_hash,
      a.machine_label,
      a.status AS activation_status,
      a.app_version,
      a.first_seen_at,
      a.last_seen_at,
      a.released_at,
      a.revoked_at,
      a.note AS activation_note,
      l.customer_name,
      l.customer_phone,
      l.plan,
      l.edition,
      l.exp,
      l.status AS license_status
    FROM license_activations a
    LEFT JOIN licenses l ON l.id = a.license_row_id
    WHERE
      a.id LIKE ?
      OR a.license_id LIKE ?
      OR a.machine_hash LIKE ?
      OR a.machine_label LIKE ?
      OR a.app_version LIKE ?
      OR l.customer_name LIKE ?
      OR l.customer_phone LIKE ?
      OR l.plan LIKE ?
    ORDER BY a.last_seen_at DESC
    LIMIT ?
  `).bind(q, q, q, q, q, q, q, q, limit).all();

  return json({ ok: true, results: rows.results || [], limit });
}

async function releaseActivationAdmin(request: Request, env: Env, id: string) {
  const t = nowIso();
  const act: any = await env.DB.prepare('SELECT * FROM license_activations WHERE id=? LIMIT 1').bind(id).first();
  if (!act) return json({ ok: false, error: 'Không tìm thấy thiết bị kích hoạt.' }, 404);

  await env.DB.prepare(`
    UPDATE license_activations
    SET status='RELEASED', released_at=?, last_seen_at=?
    WHERE id=?
  `).bind(t, t, id).run();

  await audit(env, 'activation.released.admin', { id, license_id: act.license_id, machine_hash: act.machine_hash });
  return json({ ok: true, status: 'RELEASED' });
}

async function revokeActivationAdmin(request: Request, env: Env, id: string) {
  const t = nowIso();
  const act: any = await env.DB.prepare('SELECT * FROM license_activations WHERE id=? LIMIT 1').bind(id).first();
  if (!act) return json({ ok: false, error: 'Không tìm thấy thiết bị kích hoạt.' }, 404);

  await env.DB.prepare(`
    UPDATE license_activations
    SET status='REVOKED', revoked_at=?, last_seen_at=?
    WHERE id=?
  `).bind(t, t, id).run();

  await audit(env, 'activation.revoked.admin', { id, license_id: act.license_id, machine_hash: act.machine_hash });
  return json({ ok: true, status: 'REVOKED' });
}

async function deleteActivationAdmin(request: Request, env: Env, id: string) {
  const act: any = await env.DB.prepare('SELECT * FROM license_activations WHERE id=? LIMIT 1').bind(id).first();
  if (!act) return json({ ok: false, error: 'Không tìm thấy thiết bị kích hoạt để xóa.' }, 404);

  await env.DB.prepare('DELETE FROM license_activations WHERE id=?').bind(id).run();

  await audit(env, 'activation.deleted.admin', {
    id,
    license_id: act.license_id,
    machine_hash: act.machine_hash,
    machine_label: act.machine_label
  });

  return json({
    ok: true,
    deleted: true,
    id,
    license_id: act.license_id,
    machine_hash: act.machine_hash
  });
}

async function exportLicensesCsv(request: Request, env: Env) {
  const url = new URL(request.url);
  const q = `%${(url.searchParams.get('q') || '').trim()}%`;
  const rows = await env.DB.prepare(`SELECT * FROM licenses
    WHERE id LIKE ? OR license_id LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ? OR hw_ids_json LIKE ? OR order_code LIKE ? OR note LIKE ?
    ORDER BY created_at DESC LIMIT 1000`).bind(q, q, q, q, q, q, q).all();
  const cols = ['created_at','license_id','customer_name','customer_phone','platform','fpv','hw_ids_json','edition','plan','features_json','days','exp','max_rebind','price','order_code','note','status','token'];
  const escCsv = (v: any) => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const csv = [cols.join(',')].concat((rows.results || []).map((r: any) => cols.map(c => escCsv(r[c])).join(','))).join('\n');
  return new Response(csv, { headers: { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': 'attachment; filename="remix_licenses.csv"' } });
}

async function handle(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === '/' && request.method === 'GET') return adminPage(env.PUBLIC_APP_NAME || 'RemiX Duo License Admin');
  // Public API cho app Windows.
  // Không dùng ADMIN_TOKEN, vì app khách cần gọi trực tiếp.
  try {
    if (url.pathname === '/api/appinfo' && request.method === 'GET') {
      return appInfo(request, env);
    }

    if (url.pathname === '/api/license/activate' && request.method === 'POST') {
      return activateLicense(request, env);
    }
    if (url.pathname === '/api/license/request-activation' && request.method === 'POST') {
      return requestActivation(request, env);
    }


    if (url.pathname === '/api/license/verify' && request.method === 'POST') {
      return verifyLicense(request, env);
    }

    if (url.pathname === '/api/license/heartbeat' && request.method === 'POST') {
      return heartbeatLicense(request, env);
    }

    if (url.pathname === '/api/license/release' && request.method === 'POST') {
      return releaseLicense(request, env);
    }
  } catch (e: any) {
    const businessError = publicLicenseErrorResponse(e);
    if (businessError) return businessError;
    return json({ ok: false, error: e?.message || String(e) }, 400);
  }
  if (url.pathname.startsWith('/api/admin/')) {
    const authErr = requireAdmin(request, env); if (authErr) return authErr;
    try {
      if (url.pathname === '/api/admin/health' && request.method === 'GET') return healthCheck(request, env);
      if (url.pathname === '/api/admin/customers' && request.method === 'GET') return listCustomers(request, env);
      if (url.pathname === '/api/admin/customers' && request.method === 'POST') {
        const c = await upsertCustomer(env, await request.json()); await audit(env, 'customer.upsert', c); return json({ ok: true, customer: c });
      }
      if (url.pathname === '/api/admin/license_ledger.txt' && request.method === 'GET') return exportLicenseLedgerTxt(request, env);

      // Admin: danh sách yêu cầu kích hoạt từ app Windows.
      if (url.pathname === '/api/admin/activation-requests' && request.method === 'GET') return listActivationRequests(request, env);
      const mReqApprove = url.pathname.match(/^\/api\/admin\/activation-requests\/([^/]+)\/approve$/);
      if (mReqApprove && request.method === 'POST') return updateActivationRequestStatus(request, env, mReqApprove[1], 'APPROVED');
      const mReqReject = url.pathname.match(/^\/api\/admin\/activation-requests\/([^/]+)\/reject$/);
      if (mReqReject && request.method === 'POST') return updateActivationRequestStatus(request, env, mReqReject[1], 'REJECTED');
      const mReqDelete = url.pathname.match(/^\/api\/admin\/activation-requests\/([^/]+)$/);
      if (mReqDelete && request.method === 'DELETE') return deleteActivationRequestAdmin(request, env, mReqDelete[1]);

      if (url.pathname === '/api/admin/activations' && request.method === 'GET') return listActivations(request, env);
      const mActRelease = url.pathname.match(/^\/api\/admin\/activations\/([^/]+)\/release$/);
      if (mActRelease && request.method === 'POST') return releaseActivationAdmin(request, env, mActRelease[1]);
      const mActRevoke = url.pathname.match(/^\/api\/admin\/activations\/([^/]+)\/revoke$/);
      if (mActRevoke && request.method === 'POST') return revokeActivationAdmin(request, env, mActRevoke[1]);
      const mActDelete = url.pathname.match(/^\/api\/admin\/activations\/([^/]+)$/);
      if (mActDelete && request.method === 'DELETE') return deleteActivationAdmin(request, env, mActDelete[1]);
      if (url.pathname === '/api/admin/licenses.csv' && request.method === 'GET') return exportLicensesCsv(request, env);
      if (url.pathname === '/api/admin/licenses' && request.method === 'GET') return listLicenses(request, env);
      if (url.pathname === '/api/admin/licenses' && request.method === 'POST') return createLicense(request, env);
      const mGet = url.pathname.match(/^\/api\/admin\/licenses\/([^/]+)$/);
      if (mGet && request.method === 'GET') return getLicenseById(request, env, mGet[1]);
      if (mGet && request.method === 'DELETE') return deleteLicenseAdmin(request, env, mGet[1]);
      const mRevoke = url.pathname.match(/^\/api\/admin\/licenses\/([^/]+)\/revoke$/);
      if (mRevoke && request.method === 'POST') return revokeLicense(request, env, mRevoke[1]);
      const mRenew = url.pathname.match(/^\/api\/admin\/licenses\/([^/]+)\/renew$/);
      if (mRenew && request.method === 'POST') return renewLicense(request, env, mRenew[1]);
      const mSetExpiry = url.pathname.match(/^\/api\/admin\/licenses\/([^/]+)\/set-expiry$/);
      if (mSetExpiry && request.method === 'POST') return setLicenseExpiry(request, env, mSetExpiry[1]);
      return json({ ok: false, error: 'Not found' }, 404);
    } catch (e: any) {
      return json({ ok: false, error: e?.message || String(e) }, 400);
    }
  }

  return json({ ok: false, error: 'Not found' }, 404);
}

export default { fetch: handle };
