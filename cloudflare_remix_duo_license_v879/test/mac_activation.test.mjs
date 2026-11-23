import assert from 'node:assert/strict';
import test from 'node:test';
import {buildSync} from 'esbuild';
import {ed25519} from '@noble/curves/ed25519';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
const output=buildSync({entryPoints:[fileURLToPath(new URL('../src/independent.ts',import.meta.url))],bundle:true,write:false,format:'esm',platform:'browser'});
const {default:worker}=await import('data:text/javascript;base64,'+Buffer.from(output.outputFiles[0].text).toString('base64'));

function setup(platform='MAC',machine='DUOM4-'+'C'.repeat(64)){
  const writes=[];
  const license={id:'row',license_id:'qa-mac',platform,fpv:platform==='MAC'?4:3,
    status:'ACTIVE',edition:'PRO',plan:'PRO',customer_name:'QA',exp:0,max_rebind:1,
    hw_ids_json:JSON.stringify([machine])};
  const DB={prepare(sql){return {bind(){return this;},async all(){return {results:[license]};},
    async first(){return /COUNT\(\*\)/i.test(sql)?{n:0}:null;},async run(){writes.push(sql);return {success:true};}};}};
  // Disposable fixture key; never a production issuer secret.
  const seed=new Uint8Array(32).fill(7);
  return {env:{DB,ED25519_PRIVATE_SEED_B64:Buffer.from(seed).toString('base64url')},writes,seed,machine};
}
function request(machine){return new Request('https://qa.example/api/license/activate',{
  method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({license_id:'qa-mac',machine_hash:machine,platform:'MAC',fpv:4})});}

test('actual Worker returns a valid signed MAC fpv4 token',async()=>{
 const {env,seed,machine}=setup();const response=await worker.fetch(request(machine),env);
 assert.equal(response.status,200);const data=await response.json();
 const token=data.signed_token||data.token;assert.ok(token);
 const [,raw,sig]=token.split('.');const payload=JSON.parse(Buffer.from(raw,'base64url'));
 assert.equal(payload.platform,'MAC');assert.equal(payload.fpv,4);assert.equal(payload.machine,machine);
 assert.ok(ed25519.verify(Buffer.from(sig,'base64url'),Buffer.from(raw,'base64url'),ed25519.getPublicKey(seed)));
});
test('wrong platform fails before inserting or updating a device',async()=>{
 const {env,writes,machine}=setup('WIN');const response=await worker.fetch(request(machine),env);
 assert.equal(response.status,403);assert.equal((await response.json()).status,'PLATFORM_MISMATCH');
 assert.equal(writes.length,0);
});
test('unregistered MAC hardware cannot steal another registered device slot',async()=>{
 const {env,writes}=setup();const response=await worker.fetch(request('DUOM4-'+'D'.repeat(64)),env);
 assert.equal(response.status,403);assert.equal(writes.length,0);
});
test('existing Windows v3 activation protocol remains signed and valid',async()=>{
 const {env,machine}=setup('WIN','DUO2-'+'E'.repeat(32));
 const response=await worker.fetch(request(machine),env);assert.equal(response.status,200);
 const data=await response.json();const token=data.signed_token||data.token;
 const payload=JSON.parse(Buffer.from(token.split('.')[1],'base64url'));
 assert.equal(payload.platform,'WIN');assert.equal(payload.fpv,3);assert.equal(payload.machine,machine);
});
test('admin script loads and pending MAC request selects MAC fpv4 automatically',async()=>{
 const response=await worker.fetch(new Request('https://qa.example/'),{});
 const html=await response.text();const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
 const elements=new Map(),events={};
 const get=id=>{if(!elements.has(id))elements.set(id,{value:'',style:{},textContent:'',innerHTML:'',
   setAttribute(){},addEventListener(event,callback){this[event]=callback;}});return elements.get(id);};
 get('platform').value='WIN';get('fpv').value='3';
 const context={document:{getElementById:get,querySelectorAll:()=>[],addEventListener:(event,callback)=>{events[event]=callback;}},
   localStorage:{getItem:()=>'',setItem:()=>{}},window:{scrollTo:()=>{}},HTMLElement:Object,console,URL,Blob,setTimeout};
 vm.runInNewContext(script,context);
 get('platform').value='MAC';get('platform').change();assert.equal(get('fpv').value,'4');
 get('platform').value='WIN';get('fpv').value='3';
 const attrs={'data-req-fill':'request1','data-req-phone':'qa-mac','data-req-hwid':'DUOM4-'+'A'.repeat(64)};
 const button={closest:()=>button,getAttribute:name=>attrs[name]||null};
 events.click({target:button});
 assert.equal(get('platform').value,'MAC');assert.equal(get('fpv').value,'4');
});
test('same phone WIN and MAC licenses resolve correctly in either creation order on all client routes',async()=>{
 const phone='0937000111',mac='DUOM4-'+'C'.repeat(64),win='DUO2-'+'E'.repeat(32);
 const row=(platform,machine)=>({id:platform,license_id:'qa-'+platform,customer_phone:phone,
   platform,fpv:platform==='MAC'?4:3,status:'ACTIVE',edition:'PRO',plan:'PRO',customer_name:'QA',
   hw_ids_json:JSON.stringify([machine]),exp:0,max_rebind:1});
 for(const rows of [[row('MAC',mac),row('WIN',win)],[row('WIN',win),row('MAC',mac)]]){
  for(const [platform,machine] of [['MAC',mac],['WIN',win]]){
   for(const endpoint of ['activate','verify','heartbeat','release']){
    const {env}=setup(platform,machine);
    env.DB={prepare(sql){return {bind(){return this;},async all(){return {results:rows};},
      async first(){return /COUNT\(\*\)/i.test(sql)?{n:0}:{id:'activation',status:'ACTIVE',revoked_at:null,released_at:null};},
      async run(){return {success:true};}};}};
    const response=await worker.fetch(new Request('https://qa.example/api/license/'+endpoint,{
      method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({license_id:phone,machine_hash:machine})}),env);
    assert.equal(response.status,200,platform+' '+endpoint+' order '+rows[0].platform+' '+await response.clone().text());
    const data=await response.json(),token=data.signed_token||data.token;
    if(token)assert.equal(JSON.parse(Buffer.from(token.split('.')[1],'base64url')).platform,platform);
   }
  }
 }
});
test('explicit license ID never falls back to another platforms matching phone',async()=>{
 const win='DUO2-'+'E'.repeat(32),{env}=setup('WIN',win);
 const rows=[{license_id:'qa-mac',customer_phone:'shared',platform:'MAC',fpv:4,edition:'PRO',plan:'PRO'},
             {license_id:'qa-win',customer_phone:'qa-mac',platform:'WIN',fpv:3,edition:'PRO',plan:'PRO'}];
 env.DB={prepare(){return {bind(){return this;},async all(){return {results:rows};},async run(){throw Error('must not mutate');}};}};
 const response=await worker.fetch(request(win),env);
 assert.equal(response.status,403);assert.equal((await response.json()).status,'PLATFORM_MISMATCH');
});
