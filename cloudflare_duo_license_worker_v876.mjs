/**
 * RemiX Duo Cloud Licensing V8.76 - Cloudflare Worker + D1 (standalone).
 * Issuance, seats and revocation are centrally authoritative in Cloudflare.
 * Only signed short-lived activation certificates may be cached offline.
 * Never reuse or edit MeTube/VietKTV Workers or D1 databases.
 *
 * Secrets: LICENSE_ADMIN_TOKEN (random high entropy)
 *          LICENSE_ED25519_PRIVATE_PKCS8_B64 (Ed25519 PKCS8 DER base64url)
 * D1 binding: LICENSE_DB
 * Provision & deploy under the authenticated RemiX Audio Cloudflare account.
 */
import {adminHTML, adminJS} from './cloudflare_duo_admin_ui_v876.mjs';
const encoder = new TextEncoder();
const json = (value, status=200) => new Response(JSON.stringify(value), {
  status, headers: {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff"
  }
});
const error = (code, status=400) => json({ok:false,error:code},status);
const mask = (v) => typeof v === "string" && v.length <= 128 ? v.trim() : "";
const keySyntax = /^RDX-[0-9A-F]{8}-[0-9A-F]{8}-[0-9A-F]{8}-[0-9A-F]{8}$/;
const machineSyntax = /^DUO2-[0-9A-F]{32}$/;
const b64url = (arr) => {
  let s=""; for(const b of new Uint8Array(arr)) s+=String.fromCharCode(b);
  return btoa(s).replaceAll("+","-").replaceAll("/","_").replace(/=+$/,"");
};
const unb64 = (s) => {
  if (!/^[A-Za-z0-9_-]+$/.test(s) || s.length>300) throw Error("INVALID_SIGNER_SECRET");
  const raw=atob(s.replaceAll("-","+").replaceAll("_","/")+"=".repeat((4-s.length%4)%4));
  return Uint8Array.from(raw,c=>c.charCodeAt(0));
};
async function sha256(value) {
  const hash = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(hash), b=>b.toString(16).padStart(2,"0")).join("");
}
function randomKey() {
  const bytes=crypto.getRandomValues(new Uint8Array(16));
  const text=Array.from(bytes, n=>n.toString(16).padStart(2,"0")).join("").toUpperCase();
  return "RDX-"+text.match(/.{8}/g).join("-");
}
async function readJson(request) {
  if(!request.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
    throw Error("JSON_REQUIRED");
  const len=Number(request.headers.get("content-length")||"0");
  if(len>8192) throw Error("BODY_TOO_LARGE");
  const body=await request.text();
  if(body.length>8192) throw Error("BODY_TOO_LARGE");
  const data=JSON.parse(body);
  if(!data || Array.isArray(data) || typeof data!=="object") throw Error("INVALID_JSON");
  return data;
}
function equalSecrets(a,b) {
  if(typeof a!=="string" || typeof b!=="string" || !a || !b) return false;
  // Constant-time compare for matched-length secrets (cannot remove length signal).
  const left=encoder.encode(a), right=encoder.encode(b);
  let diff=left.length^right.length;
  const limit=Math.max(left.length,right.length);
  for(let i=0;i<limit;i++) diff |= (left[i]||0)^(right[i]||0);
  return diff===0;
}
const adminOK=(req, env) => {
  const value=req.headers.get("authorization")||"";
  return !!env.LICENSE_ADMIN_TOKEN &&
         equalSecrets(value, "Bearer "+env.LICENSE_ADMIN_TOKEN);
};
const seconds=() => Math.floor(Date.now()/1000);
async function signCertificate(env, claims) {
  if(!env.LICENSE_ED25519_PRIVATE_PKCS8_B64) throw Error("ISSUER_NOT_PROVISIONED");
  const bytes=unb64(env.LICENSE_ED25519_PRIVATE_PKCS8_B64);
  const key=await crypto.subtle.importKey("pkcs8",bytes,
                                         {name:"Ed25519"},false,["sign"]);
  const raw=encoder.encode(JSON.stringify(claims));
  const sig=await crypto.subtle.sign("Ed25519",key,raw);
  return "LIC1."+b64url(raw)+"."+b64url(sig);
}
function verifyEnv(env) {
  return !!(env.LICENSE_DB && env.LICENSE_ADMIN_TOKEN &&
            env.LICENSE_ED25519_PRIVATE_PKCS8_B64);
}
async function issue(req,env) {
  if(!adminOK(req,env)) return error("UNAUTHORIZED",401);
  let data; try { data=await readJson(req); } catch(e) { return error(e.message||"INVALID_JSON"); }
  const order=mask(data.order_id), customer=mask(data.customer);
  const days=data.days, seats=data.seats===undefined ? 1 : data.seats;
  if(!order || !customer || !Number.isInteger(days) || days<0 || days>36500 ||
     !Number.isInteger(seats) || seats<1 || seats>500)
    return error("INVALID_ISSUANCE_FIELDS");
  const id=crypto.randomUUID();
  const key=randomKey();
  const hash=await sha256(key);
  const now=seconds(), exp=days===0 ? 0 : now+days*86400;
  try {
    await env.LICENSE_DB.prepare(
      "INSERT INTO license_keys (id,key_sha256,order_id,customer,edition,status,"+
      "max_seats,issued_at,expires_at) VALUES (?,?,?,?,?,'ACTIVE',?,?,?)"
    ).bind(id,hash,order,customer,"DUO_PRO",seats,now,exp).run();
    return json({ok:true,license_id:id,license_key:key,
                 product:"DUO_PRO",order_id:order,max_seats:seats,
                 expires_at:exp},201);
  } catch(e) {
    return error("ISSUE_STORAGE_FAILED",503);
  }
}
async function activate(req,env) {
  let data; try { data=await readJson(req); } catch(e) { return error(e.message||"INVALID_JSON"); }
  const key=mask(data.key).toUpperCase(), machine=mask(data.machine_id).toUpperCase();
  if(!keySyntax.test(key) || !machineSyntax.test(machine))
    return error("INVALID_ACTIVATION_FIELDS");
  const hash=await sha256(key);
  const lic=await env.LICENSE_DB.prepare(
    "SELECT id,customer,edition,status,max_seats,expires_at FROM license_keys WHERE key_sha256=?"
  ).bind(hash).first();
  if(!lic) return error("KEY_NOT_FOUND",404);
  if(lic.status!=="ACTIVE") return error("LICENSE_REVOKED",403);
  if(lic.edition!=="DUO_PRO") return error("WRONG_PRODUCT",403);
  const now=seconds();
  if(lic.expires_at!==0 && lic.expires_at<=now) return error("LICENSE_EXPIRED",403);
  const existing=await env.LICENSE_DB.prepare(
    "SELECT id FROM activations WHERE license_id=? AND machine_id=?"
  ).bind(lic.id,machine).first();
  try {
    if(!existing) {
      // D1 BEFORE INSERT trigger caps seats atomically under concurrency.
      await env.LICENSE_DB.prepare(
        "INSERT INTO activations (id,license_id,machine_id,created_at,last_seen_at) VALUES (?,?,?,?,?)"
      ).bind(crypto.randomUUID(),lic.id,machine,now,now).run();
    } else {
      await env.LICENSE_DB.prepare(
        "UPDATE activations SET last_seen_at=? WHERE license_id=? AND machine_id=?"
      ).bind(now,lic.id,machine).run();
    }
  } catch(e) {
    return error("SEAT_LIMIT_OR_STORAGE_ERROR",409);
  }
  const exp=Math.min(now+72*3600,lic.expires_at || Number.MAX_SAFE_INTEGER);
  const claims={
    v:2,fpv:2,platform:"WIN",issuer:"CLOUDFLARE",edition:"DUO_PRO",
    machine_ids:[machine],machine:machine,machine_id:machine,
    lic_id:lic.id,name:lic.customer,iat:now,exp:exp
  };
  try {
    const token=await signCertificate(env,claims);
    return json({ok:true,token,license_id:lic.id,expires_at:exp,
                 offline_grace_seconds:72*3600});
  } catch(e) {
    return error("SIGNER_NOT_READY",503);
  }
}
async function revoke(req,env) {
  if(!adminOK(req,env)) return error("UNAUTHORIZED",401);
  let data; try {data=await readJson(req);}catch(e){return error("INVALID_JSON");}
  const id=mask(data.license_id);
  if(!/^[0-9a-f-]{36}$/i.test(id)) return error("INVALID_LICENSE_ID");
  const r=await env.LICENSE_DB.prepare(
    "UPDATE license_keys SET status='REVOKED' WHERE id=? AND status='ACTIVE'"
  ).bind(id).run();
  return json({ok:!!r.meta?.changes,license_id:id,
               status:r.meta?.changes ? "REVOKED" : "UNCHANGED"});
}
async function status(req,env) {
  if(!adminOK(req,env)) return error("UNAUTHORIZED",401);
  const id=new URL(req.url).searchParams.get("id")||"";
  if(!/^[0-9a-f-]{36}$/i.test(id)) return error("INVALID_LICENSE_ID");
  const item=await env.LICENSE_DB.prepare(
    "SELECT id,order_id,customer,status,edition,max_seats,issued_at,expires_at "+
    "FROM license_keys WHERE id=?"
  ).bind(id).first();
  if(!item) return error("NOT_FOUND",404);
  const count=await env.LICENSE_DB.prepare(
    "SELECT count(*) AS seats_used FROM activations WHERE license_id=?"
  ).bind(id).first();
  return json({ok:true,license:{...item,seats_used:count?.seats_used||0}});
}
export default {
  async fetch(request,env) {
    try {
      const url=new URL(request.url);
      if(url.pathname==="/health" && request.method==="GET")
        return json({service:"remix-duo-license",configured:verifyEnv(env)});
      if(!verifyEnv(env)) return error("SERVICE_NOT_PROVISIONED",503);
      if(url.pathname==="/admin" && request.method==="GET")
        return new Response(adminHTML,{headers:{
          "content-type":"text/html; charset=utf-8","cache-control":"no-store",
          "content-security-policy":"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
          "x-frame-options":"DENY","x-content-type-options":"nosniff"
        }});
      if(url.pathname==="/admin/app.js" && request.method==="GET")
        return new Response(adminJS,{headers:{
          "content-type":"application/javascript; charset=utf-8",
          "cache-control":"no-store","x-content-type-options":"nosniff"
        }});
      if(url.pathname==="/v1/activate" && request.method==="POST") return activate(request,env);
      if(url.pathname==="/v1/admin/issue" && request.method==="POST") return issue(request,env);
      if(url.pathname==="/v1/admin/revoke" && request.method==="POST") return revoke(request,env);
      if(url.pathname==="/v1/admin/status" && request.method==="GET") return status(request,env);
      return error("NOT_FOUND",404);
    } catch(e) {
      return error("INTERNAL_SERVER_ERROR",500);
    }
  }
};
