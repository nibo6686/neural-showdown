import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {validatePreparedProtocolAsset} from '../src/prepared_protocol_contract';
import {loadPreparedProtocolAsset,protocolContext,helperContext,NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT} from '../src/version_profile';
import {validateProtocolContract} from '../src/protocol_contract';
const root=path.resolve(__dirname,'../../..');
const file=(p:string)=>path.join(root,'trainer/src/neural',p==='native11'?'protocol_contract_b8f23c99.json':'protocol_contract_replay_compat_v1.json');
const read=(p:string)=>JSON.parse(fs.readFileSync(file(p),'utf8'));
const emit=(name:string,data:object)=>console.log('P37_WITNESS '+JSON.stringify({name,...data}));
function mutate(v:any,c:any){
 if(c.op==='set'){let target=v;for(const key of c.path.slice(0,-1))target=target[key];target[c.path.at(-1)]=c.value;}
 else if(c.op==='duplicate-token')v.protocol.supported_commands.push(v.protocol.supported_commands[0]);
 else if(c.op==='add-token')v.protocol.supported_commands.push('unreviewed');
 else if(c.op==='missing-fixture')v.protocol.record_fixtures.pop();
 else if(c.op==='invalid-positive'){const f=v.protocol.record_fixtures.find((x:any)=>x.token==='switch');const i=Number(f.fixture_reference.slice(8));f.record='|switch|p1z: Invalid|Regice, L88|100/100';v.protocol.valid_record_controls[i].record=f.record;}
 else if(c.op==='accepted-negative')v.protocol.rejection_fixtures[0].record='|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure|[silent]';
 else if(c.op==='wrong-negative-reason')v.protocol.rejection_fixtures[0].kind='unproved_semantic_family';
 else if(c.op==='replay-rule')v.protocol.validation_rules.major_status.cure_forms.at(-1).tags.push('[of] opposing-active');
 else throw Error('Unknown mutation');
}
test('P37 full assets direct mutations and integrity',()=>{
 const results:any[]=[];
 for(const p of ['native11','replay-compat-v1'] as const){const v=read(p);const out=validatePreparedProtocolAsset(v,p);assert.notEqual(out,v);
  assert.equal(out.protocol.record_fixtures.length,p==='native11'?111:108);assert.ok(Object.isFrozen(out));
  assert.throws(()=>helperContext(out as any),/unsupported-context/);assert.throws(()=>protocolContext(out as any),/unsupported-context/);
  assert.deepEqual(loadPreparedProtocolAsset(p),out);
 }
 const cases=JSON.parse(fs.readFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt37-mutations.json'),'utf8'));
 for(const c of cases){const v=read(c.profile);mutate(v,c);assert.equal(createHash('sha256').update(JSON.stringify(v)).digest('hex').length,64);
  assert.throws(()=>validatePreparedProtocolAsset(v,c.profile),new RegExp('prepared-protocol-contract/v1/'+c.expected),c.name);results.push({name:c.name,invariant:c.expected});}
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'P37-contracts-'));
 try{for(const p of ['native11','replay-compat-v1'] as const){const v=read(p);v.adopted=true;const f=path.join(tmp,p+'.json');fs.writeFileSync(f,JSON.stringify(v));assert.throws(()=>loadPreparedProtocolAsset(p,f),/version-asset-integrity/);assert.throws(()=>loadPreparedProtocolAsset(p,path.join(tmp,'missing')),/missing-version-asset/);}}
 finally{fs.rmSync(tmp,{recursive:true,force:true});}
 validateProtocolContract(JSON.parse(fs.readFileSync(path.join(root,'trainer/src/neural/protocol_contract.json'),'utf8')));
 emit('full-validation',{mutations:results,fixture_counts:[111,108],native_runtime:'UNEXECUTED'});
});
test('P37 owned bootstrap and sticky failure fresh processes',()=>{
 const good=`const assert=require('assert/strict'),Module=require('module');const load=Module._load;let attempts=0;Module._load=function(name,...args){if(String(name).includes('pokemon-showdown')){attempts++;throw Error('engine forbidden')}return load.call(this,name,...args)};
 const v=require('./sim-core/dist/src/version_profile'),c=require('./sim-core/dist/src/prepared_protocol_contract');const original=c.checkPreparedProtocolRecords;let taps=0;
 c.checkPreparedProtocolRecords=function(asset,profile){if(profile==='native11'&&taps++===0){assert.equal(v.protocolContext(v.NATIVE11_GRAMMAR_CONTEXT),v.NATIVE11_GRAMMAR_CONTEXT);assert.throws(()=>v.protocolContext(v.REPLAY_COMPAT_CONTEXT),/prepared-validation-context/);assert.throws(()=>v.protocolContext({...v.NATIVE11_GRAMMAR_CONTEXT}),/unsupported-context/);assert.throws(()=>c.validatePreparedProtocolAsset(JSON.parse(JSON.stringify(asset)),profile),/prepared-validation-context/);}return original(asset,profile)};
 try{v.protocolContext(v.NATIVE11_GRAMMAR_CONTEXT);v.protocolContext(v.REPLAY_COMPAT_CONTEXT);assert.equal(attempts,0)}finally{c.checkPreparedProtocolRecords=original}console.log(JSON.stringify({owned_reentry:true,copied_and_other_profile_rejected:true,arbitrary_validation_blocked:true,engine_load_attempts:attempts}));`;
 const bad=`const assert=require('assert/strict');const v=require('./sim-core/dist/src/version_profile'),c=require('./sim-core/dist/src/prepared_protocol_contract');const original=c.checkPreparedProtocolRecords;let calls=0;c.checkPreparedProtocolRecords=function(){calls++;throw Error('P37 owned-check fault')};try{for(let i=0;i<2;i++)assert.throws(()=>v.protocolContext(v.NATIVE11_GRAMMAR_CONTEXT),/P37 owned-check fault/);assert.equal(calls,1)}finally{c.checkPreparedProtocolRecords=original}assert.throws(()=>v.protocolContext(v.NATIVE11_GRAMMAR_CONTEXT),/P37 owned-check fault/);console.log(JSON.stringify({sticky_failed_context:true,checks: calls}));`;
 const rows=[];for(const code of [good,bad]){const p=spawnSync(process.execPath,['-e',code],{cwd:root,encoding:'utf8',timeout:20000});assert.equal(p.status,0,p.stderr);rows.push(JSON.parse(p.stdout));}
 emit('bootstrap',{controls:rows,model_only:false,target_emitter:'UNEXECUTED'});
});
