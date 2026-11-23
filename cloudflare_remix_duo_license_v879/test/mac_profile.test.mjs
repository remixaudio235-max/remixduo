import assert from 'node:assert/strict';
import test from 'node:test';
import {buildSync} from 'esbuild';
import {fileURLToPath} from 'node:url';
const built=buildSync({entryPoints:[fileURLToPath(new URL('../src/clientProfiles.ts',import.meta.url))],bundle:true,write:false,format:'esm'});
const {validateClientProfile,clientProfileMismatch}=await import('data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].text).toString('base64'));

test('MAC issuance is fpv4 and strictly bound to DUOM4 hardware hashes',()=>{
  const mac='DUOM4-'+'A'.repeat(64);
  assert.doesNotThrow(()=>validateClientProfile('MAC',4,[mac]));
  for(const [p,f,ids] of [['MAC',3,[mac]],['MAC',4,['DUO2-'+'A'.repeat(32)]],['WIN',4,[mac]],['ANY',4,[mac]],['WIN',3,[mac]],['ANY',3,[mac]]])
    assert.throws(()=>validateClientProfile(p,f,ids));
  assert.doesNotThrow(()=>validateClientProfile('WIN',3,['DUO2-'+'A'.repeat(32)]));
});

test('MAC activation cannot consume a Windows license/device slot',()=>{
  const mid='DUOM4-'+'B'.repeat(64);
  assert.equal(clientProfileMismatch({platform:'WIN',fpv:3},mid),true);
  assert.equal(clientProfileMismatch({platform:'ANY',fpv:4},mid),true);
  assert.equal(clientProfileMismatch({platform:'MAC',fpv:4},mid),false);
  assert.equal(clientProfileMismatch({platform:'MAC',fpv:3},mid),true);
  assert.equal(clientProfileMismatch({platform:'WIN',fpv:3},'DUO2-'+'B'.repeat(32)),false);
});
