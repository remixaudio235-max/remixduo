/** V8.76 Cloudflare Worker unit tests with in-memory fake D1; never production. */
import test from "node:test";
import assert from "node:assert/strict";
import {generateKeyPairSync,webcrypto} from "node:crypto";
import worker from "./cloudflare_duo_license_worker_v876.mjs";

if(!globalThis.crypto) globalThis.crypto=webcrypto;
const {privateKey, publicKey}=generateKeyPairSync("ed25519");
const signer=privateKey.export({format:"der",type:"pkcs8"}).toString("base64url");
const machine="DUO2-"+"A".repeat(32);
const machine2="DUO2-"+"B".repeat(32);

function db() {
  const licenses=new Map(), activations=new Map();
  const fake={
    licenses,activations,
    prepare(sql) {
      const obj={
        args:[],
        bind(...args){this.args=args;return this;},
        async first(){
          const a=this.args;
          if(sql.includes("FROM license_keys WHERE key_sha256="))
            return [...licenses.values()].find(l=>l.key_sha256===a[0])||null;
          if(sql.includes("FROM license_keys WHERE id="))
            return licenses.get(a[0])||null;
          if(sql.includes("SELECT id FROM activations"))
            return activations.get(a[0]+"|"+a[1])||null;
          if(sql.includes("count(*) AS seats_used")) {
            return {seats_used:[...activations.values()].filter(x=>x.license_id===a[0]).length};
          }
          throw Error("UNMOCKED_SQL_SELECT "+sql);
        },
        async run(){
          const a=this.args;
          if(sql.startsWith("INSERT INTO license_keys")) {
            const [id,key_sha256,order_id,customer,edition,max_seats,issued_at,expires_at]=a;
            licenses.set(id,{id,key_sha256,order_id,customer,edition,status:"ACTIVE",max_seats,
                             issued_at,expires_at});
            return {meta:{changes:1}};
          }
          if(sql.startsWith("INSERT INTO activations")){
            const [id,license_id,machine_id,created_at,last_seen_at]=a;
            const key=license_id+"|"+machine_id;
            const lic=licenses.get(license_id);
            const count=[...activations.values()].filter(x=>x.license_id===license_id).length;
            if(count>=lic.max_seats) throw Error("LICENSE_SEAT_LIMIT");
            activations.set(key,{id,license_id,machine_id,created_at,last_seen_at});
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE activations SET last_seen_at=")) {
            const row=activations.get(a[1]+"|"+a[2]);row.last_seen_at=a[0];
            return {meta:{changes:1}};
          }
          if(sql.startsWith("UPDATE license_keys SET status='REVOKED'")){
            const item=licenses.get(a[0]);
            if(item && item.status==="ACTIVE"){item.status="REVOKED";return {meta:{changes:1}};}
            return {meta:{changes:0}};
          }
          throw Error("UNMOCKED_SQL_RUN "+sql);
        }
      };
      return obj;
    }
  };
  return fake;
}
function env(database=db()){
  return { LICENSE_DB:database,LICENSE_ADMIN_TOKEN:"TEST_ONLY_ADMIN_SECRET",
           LICENSE_ED25519_PRIVATE_PKCS8_B64:signer };
}
function request(path, method="POST",body={},auth=false){
  return new Request("https://remix-duo-license.example.workers.dev"+path,{
    method,headers:{"content-type":"application/json",
                    ...(auth?{"authorization":"Bearer TEST_ONLY_ADMIN_SECRET"}:{})},
    ...(method==="POST"?{body:JSON.stringify(body)}:{})
  });
}
async function send(e,p,m,b,auth){
  const r=await worker.fetch(request(p,m,b,auth),e);
  return [r.status,await r.json()];
}
test("Cloudflare-hosted admin portal and admin JS use no local storage",async()=>{
  const e=env();
  const r=await worker.fetch(request("/admin","GET"),e);
  assert.equal(r.status,200);
  assert.match(r.headers.get("content-security-policy"),/frame-ancestors/);
  const html=await r.text();
  assert.match(html,/License Center/);
  const j=await worker.fetch(request("/admin/app.js","GET"),e);
  assert.equal(j.status,200);
  const js=await j.text();
  assert.match(js,/\/v1\/admin\/issue/);
  assert.equal(js.includes("localStorage"),false);
});
test("provisioning fail-closed; no public issuance",async()=>{
  const r=await worker.fetch(request("/health","GET"),{});
  assert.equal((await r.json()).configured,false);
  const [status,body]=await send({}, "/v1/activate","POST",
    {key:"RDX-"+("A".repeat(8)+"-").repeat(3)+"A".repeat(8),machine_id:machine});
  assert.equal(status,503);
  assert.equal(body.error,"SERVICE_NOT_PROVISIONED");
});
test("admin auth and issue-only under Cloudflare",async()=>{
  const e=env();
  const [unauth,deny]=await send(e,"/v1/admin/issue","POST",
    {order_id:"order",customer:"QA",days:365});
  assert.equal(unauth,401);assert.equal(deny.error,"UNAUTHORIZED");
  const [invalid]=await send(e,"/v1/admin/issue","POST",
    {order_id:"",customer:"QA",days:-1},true);
  assert.equal(invalid,400);
});
test("issue activation, seats, fresh 72h cert and revocation",async()=>{
  const e=env();
  const [created,lic]=await send(e,"/v1/admin/issue","POST",
    {order_id:"ORDER-001",customer:"QA",days:365,seats:1},true);
  assert.equal(created,201);
  assert.match(lic.license_key,/^RDX-(?:[0-9A-F]{8}-){3}[0-9A-F]{8}$/);
  assert.equal(lic.product,"DUO_PRO");
  const row=e.LICENSE_DB.licenses.get(lic.license_id);
  assert.equal(row.key_sha256.length,64);
  assert.equal(JSON.stringify(row).includes(lic.license_key),false);
  const [activated,proof]=await send(e,"/v1/activate","POST",
    {key:lic.license_key,machine_id:machine});
  assert.equal(activated,200);
  assert.equal(proof.ok,true);
  const [header,payloadB64,signatureB64]=proof.token.split(".");
  assert.equal(header,"LIC1");
  const payload=JSON.parse(Buffer.from(payloadB64,"base64url").toString("utf8"));
  assert.equal(payload.issuer,"CLOUDFLARE");
  assert.equal(payload.machine_ids[0],machine);
  assert.equal(payload.edition,"DUO_PRO");
  assert.equal(payload.exp-payload.iat,72*3600);
  const ok=publicKey.verify ? true : true;
  const {verify}=await import("node:crypto");
  assert.equal(verify(null,Buffer.from(payloadB64,"base64url"),publicKey,
                      Buffer.from(signatureB64,"base64url")),true);
  const [again]=await send(e,"/v1/activate","POST",{key:lic.license_key,machine_id:machine});
  assert.equal(again,200);
  assert.equal(e.LICENSE_DB.activations.size,1);
  const [full,denied]=await send(e,"/v1/activate","POST",
    {key:lic.license_key,machine_id:machine2});
  assert.equal(full,409); assert.equal(denied.error,"SEAT_LIMIT_OR_STORAGE_ERROR");
  const [status,item]=await send(e,"/v1/admin/status?id="+lic.license_id,
                                "GET",null,true);
  assert.equal(status,200);
  assert.equal(item.license.seats_used,1);
  const [revoked]=await send(e,"/v1/admin/revoke","POST",
                              {license_id:lic.license_id},true);
  assert.equal(revoked,200);
  const [blocked,reason]=await send(e,"/v1/activate","POST",
    {key:lic.license_key,machine_id:machine});
  assert.equal(blocked,403);assert.equal(reason.error,"LICENSE_REVOKED");
});
test("missing key, invalid shape, wrong auth, non-existent routes",async()=>{
  const e=env();
  const [bad]=await send(e,"/v1/activate","POST",
     {key:"NOT-A-KEY",machine_id:machine});
  assert.equal(bad,400);
  const [missing]=await send(e,"/v1/activate","POST",
     {key:"RDX-"+("A".repeat(8)+"-").repeat(3)+"A".repeat(8),machine_id:machine});
  assert.equal(missing,404);
  const r=await worker.fetch(request("/v1/admin/status?id=BAD","GET",null,true),e);
  assert.equal(r.status,400);
  const [notfound]=await send(e,"/v1/nonexistent","POST",{});
  assert.equal(notfound,404);
});
test("two seats and perpetual issuance",async()=>{
  const e=env();
  const [status,item]=await send(e,"/v1/admin/issue","POST",
    {order_id:"ORDER-PERP",customer:"Customer",days:0,seats:2},true);
  assert.equal(status,201);assert.equal(item.expires_at,0);
  for (const mid of [machine,machine2]){
    const [code,payload]=await send(e,"/v1/activate","POST",
      {key:item.license_key,machine_id:mid});
    assert.equal(code,200);assert.equal(payload.ok,true);
  }
  assert.equal(e.LICENSE_DB.activations.size,2);
});
