import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
const root=path.resolve(__dirname,'../../..');
const directory=path.join(root,'sim-core/tests/fixtures/replay-real');
const manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));

if(!isMainThread){
 (async()=>{
  const {replaySession}=require(path.join(root,'tools/replay_repro/replay_session.cjs'));
  for(const row of workerData){
   let result:any;
   try{const r=await replaySession(JSON.parse(fs.readFileSync(path.join(directory,row.id+'.json'),'utf8')),{collect:false,kdiff:true,ownerMoves:true});result={id:row.id,boundaries:r.boundaries,kdiff:r.kdiff};}
   catch(error){const e=error as any;result={id:row.id,error:e.message,kdiff:e.replayResult?.kdiff};}
   parentPort!.postMessage(result);
  }
 })().catch(error=>{throw error;});
}else{
 test('curated real replays retain exact public logs, canonical choices and all adopted K rows',{timeout:95000},async()=>{
  const results:any[]=[];
  const {targets}=require(path.join(root,'tools/replay_repro/select_fixtures.cjs'));
  for(const row of manifest.fixtures){
   const replay=JSON.parse(fs.readFileSync(path.join(directory,row.id+'.json'),'utf8'));
   assert.equal(replay.id,row.id);
   assert.ok(replay.inputlog.includes('>version '+row.server_commit));
   for(const target of row.targets)assert.ok(targets[target](replay.log),row.id+' '+target);
  }
  const batches=Array.from({length:4},()=>({cost:0,rows:[] as any[]}));
  const selected=manifest.fixtures.filter((row:any)=>!row.long_only);
  for(const row of [...selected].sort((a,b)=>b.turns-a.turns)){
   const batch=[...batches].sort((a,b)=>a.cost-b.cost)[0];batch.rows.push(row);batch.cost+=row.turns+1;
  }
  await Promise.all(batches.map(batch=>new Promise<void>((resolve,reject)=>{
   const worker=new Worker(__filename,{workerData:batch.rows});
   const timer=setTimeout(()=>{void worker.terminate();reject(new Error('curated replay worker exceeded 90 seconds'));},90000);
   worker.on('message',row=>results.push(row));worker.on('error',reject);
   worker.on('exit',code=>{clearTimeout(timer);code===0?resolve():reject(new Error('fixture worker exit '+code));});
  })));
  assert.equal(results.length,selected.length);
  for(const row of selected){const actual=results.find(r=>r.id===row.id);
   assert.equal(actual.error,row.expected_failure,JSON.stringify(actual));
   if(actual.kdiff)assert.equal(actual.kdiff.mismatches,0,row.id+' K differential');
   else assert.ok(row.expected_failure,'A completed replay must measure K');
   if(!row.expected_failure)assert.ok(actual.boundaries>0);
  }
  const registry=JSON.parse(fs.readFileSync(path.join(root,'docs/contracts/knowledge-coverage.json'),'utf8'));
  for(const row of registry.rows.filter((r:any)=>r.status==='adopted')){
   const key=[row.family,row.property,row.context,row.perspective].join('/');
   assert.ok(results.some(result=>result.kdiff?.rows[key]?.checks>0),'No K checks for adopted '+key);
  }
 });
 test('long curated real replay (40+ turns)',{skip:process.env.NEURAL_LONG_TESTS!=='1'?'40-turn full K replay exceeds the fast fixture budget; NEURAL_LONG_TESTS=1 opts in':false,timeout:120000},async()=>{
  const {replaySession}=require(path.join(root,'tools/replay_repro/replay_session.cjs'));
  for(const row of manifest.fixtures.filter((r:any)=>r.long_only)){
   const result=await replaySession(JSON.parse(fs.readFileSync(path.join(directory,row.id+'.json'),'utf8')),{collect:false,kdiff:true,ownerMoves:true});
   assert.equal(result.kdiff.mismatches,0);assert.ok(result.boundaries>0);
  }
 });
}
