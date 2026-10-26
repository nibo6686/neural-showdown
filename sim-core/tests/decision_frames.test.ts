import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';
import test from 'node:test';
import os from 'node:os';
import {invarianceCases} from './helpers/decision_frame_cases';
const root=path.resolve(__dirname,'../../..');
const {exportReplay,decisionFrame}=require(path.join(root,'tools/replay_repro/export_frames.cjs'));

test('fixture selection is deterministic, shortest and admitted-only',()=>{
 const {selectFixtures}=require(path.join(root,'tools/replay_repro/select_fixtures.cjs'));
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'neural-fixture-selection-'));
 try{
  const entries=[{id:'rejected',turns:0,admitted:false},{id:'missed',turns:0,admitted:true},{id:'later',turns:2,admitted:true},{id:'short-b',turns:1,admitted:true},{id:'short-a',turns:1,admitted:true}];
  fs.writeFileSync(path.join(directory,'admission.jsonl'),entries.map(row=>JSON.stringify(row)).join('\n'));
  for(const row of entries)fs.writeFileSync(path.join(directory,row.id+'.json'),JSON.stringify({id:row.id,
   log:'|move|p1a: A|U-turn|p2a: B\n'+(row.id==='missed'?'':'|switch|p1a: C|C|100/100|[from] U-turn\n')}));
  const a=selectFixtures(directory,path.join(directory,'out'));
  fs.writeFileSync(path.join(directory,'admission.jsonl'),entries.reverse().map(row=>JSON.stringify(row)).join('\n'));
  assert.deepEqual(selectFixtures(directory,path.join(directory,'out')),a);
  assert.equal(a.fixtures.length,1);assert.equal(a.fixtures[0].id,'short-a');assert.deepEqual(a.fixtures[0].targets,['U-turn']);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('decision frames round trip three committed replays with addressed adopted profiles',{timeout:40000},async()=>{
 for(const id of ['2695493840','2695512325','2695618222']){
  const frames:any[]=[];
  await exportReplay(JSON.parse(fs.readFileSync(path.join(root,'sim-core/tests/fixtures/replay-real/gen9randombattle-'+id+'.json'),'utf8')),(frame:any)=>frames.push(frame));
  assert.ok(frames.length>=2);
  for(const frame of frames){
   assert.deepEqual(JSON.parse(JSON.stringify(frame)),frame);
   assert.equal(frame.knowledge.projection.owner,frame.owner);
   assert.equal(frame.knowledge.projection.owned_moves.owner,frame.owner);
   assert.equal(frame.legal_actions.length,frame.observation.request?.legal_actions.available_indices.length??0);
   if(frame.action)assert.ok(frame.legal_actions.some((a:any)=>a.action_id===frame.action.action_id));
   const forged=structuredClone(frame);forged.owner=frame.owner==='p1'?'p2':'p1';
   assert.throws(()=>decisionFrame({...forged,step_index:frame.step_index}),/address-binding/);
  }
 }
});

test('born decision frames are byte invariant to either opponent hidden bench until reveal',{timeout:40000},async()=>{
 for(const {variants:[a,b]} of await invarianceCases()){
  for(const index of [0,1])assert.equal(JSON.stringify(a[index]),JSON.stringify(b[index]));
  assert.notEqual(JSON.stringify(a[2]),JSON.stringify(b[2]));
 }
});
