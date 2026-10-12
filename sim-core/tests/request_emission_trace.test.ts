import assert from 'node:assert/strict';
import test from 'node:test';
import { BattleStream, Teams } from 'pokemon-showdown';
import { RequestEmissionTrace } from '../src/request_emission_trace';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';

const FORMAT='gen9randombattle', SEED=[1,2,3,4];
const OPTIONS={include_wait_requests:true,include_possible_roles:false};
const UNICODE='\u00e9-\u03a9\u{1f600}';
const rows=(env:LocalBattleEnv,owner:PlayerID)=>env.inspectRequestEmissionTrace(env.getRequestEmissionTraceHandle(owner),owner);
const other=(owner:PlayerID):PlayerID=>owner==='p1'?'p2':'p1';
const record=`|request| { "z":"${UNICODE}", "wait":true, "side":{"id":"p1","pokemon":[]} }\t `;
function controller() {
  const trace=new RequestEmissionTrace(), p1={},p2={};trace.bind('p1',p1);trace.bind('p2',p2);return {trace,p1,p2};
}
function emission(trace:RequestEmissionTrace,owner:PlayerID,text=record) {
  trace.atProducer('native_emission',()=>{trace.emitted('sideupdate',`${owner}\n${text}`);});
}

test('literal exact text, owner FIFO, repeated equal bytes and distinct process occurrences',()=>{
  const {trace,p1,p2}=controller();emission(trace,'p1');emission(trace,'p2');emission(trace,'p1');
  assert.throws(()=>trace.inspect(trace.handle('p1'),'p1'),/unreceived-emission/);
  trace.received('p1',p1,record);trace.received('p1',p1,record);trace.received('p2',p2,record);
  const a=trace.inspect(trace.handle('p1'),'p1'),b=trace.inspect(trace.handle('p2'),'p2');
  assert.deepEqual(a.map(r=>r.emission_index),[1,3]);assert.deepEqual(a.map(r=>r.owner_emission_index),[1,2]);
  assert.deepEqual(a.map(r=>r.receipt.owner_receipt_index),[1,2]);assert.equal(b[0].emission_index,2);
  assert.equal(a[0].request_record,record);assert.equal(a[0].request_json,` { "z":"${UNICODE}", "wait":true, "side":{"id":"p1","pokemon":[]} }\t `);
  assert.equal(a[0].receipt.record,record);assert.equal(a[0].receipt.json,a[0].request_json);
  assert.equal(a[0].producer_occurrence,b[0].producer_occurrence);assert.ok(Object.isFrozen(a) && Object.isFrozen(a[0]) && Object.isFrozen(a[0].receipt));
  assert.throws(()=>trace.inspect(a[0].producer_occurrence,'p1'),/foreign-or-forged/);
  const second=controller();emission(second.trace,'p1');second.trace.received('p1',second.p1,record);
  const foreign=second.trace.inspect(second.trace.handle('p1'),'p1')[0];
  assert.equal(foreign.emission_index,1);assert.notEqual(foreign.producer_occurrence,a[0].producer_occurrence);
  assert.throws(()=>trace.inspect(second.trace.handle('p1'),'p1'),/foreign-or-forged/);
  // Same-byte substitution inside a monkeypatched held stream is undetectable.
});

test('forged handles, owner swaps and diagnostic/transport copies do not grant trace access',()=>{
  const {trace}=controller(),handle=trace.handle('p1');
  for(const fake of [{},{...handle},JSON.parse(JSON.stringify(handle)),structuredClone(handle),{owner:'p1',emission_index:1}]) {
    assert.throws(()=>trace.inspect(fake,'p1'),/foreign-or-forged/);
  }
  assert.throws(()=>trace.inspect(handle,'p2'),/foreign-or-forged/);
  assert.throws(()=>trace.handle('p3' as PlayerID),/invalid-owner/);
});

for(const violation of ['foreign','cross-owner','missing','duplicate','order','text','origin','unscoped'] as const) {
  test(`unsupported ${violation} join invalidates the entire trace atomically`,()=>{
    const {trace,p1}=controller();const handle=trace.handle('p1');
    if(violation!=='missing'&&violation!=='origin'&&violation!=='unscoped') emission(trace,'p1');
    assert.throws(()=>{
      if(violation==='foreign') trace.received('p1',controller().p1,record);
      if(violation==='cross-owner') trace.received('p2',p1,record);
      if(violation==='missing') trace.received('p1',p1,record);
      if(violation==='duplicate') {trace.received('p1',p1,record);trace.received('p1',p1,record);}
      if(violation==='order') {emission(trace,'p1','|request|{"wait":false}');trace.received('p1',p1,'|request|{"wait":false}');}
      if(violation==='text') trace.received('p1',p1,record.trimEnd());
      if(violation==='origin') trace.atProducer('imported' as any,()=>{});
      if(violation==='unscoped') trace.emitted('sideupdate',`p1\n${record}`);
    },/request-trace\/v1\//);
    assert.throws(()=>trace.inspect(handle,'p1'),/invalidated/);assert.throws(()=>trace.handle('p2'),/invalidated/);
  });
}

test('producer scope is synchronous, restore classification is explicit and does not leak',()=>{
  const {trace,p1}=controller();
  trace.atProducer('restore_reemit',()=>{trace.emitted('sideupdate',`p1\n${record}`);});
  emission(trace,'p1');trace.received('p1',p1,record);trace.received('p1',p1,record);
  assert.deepEqual(trace.inspect(trace.handle('p1'),'p1').map(r=>r.origin),['restore_reemit','native_emission']);
  assert.throws(()=>trace.atProducer('native_emission',()=>Promise.resolve()),/non-synchronous-producer/);
  assert.throws(()=>trace.handle('p1'),/invalidated/);
});

test('actual session native producer and routed ManagedPlayer receipt retain both owner literals before parsing',async()=>{
  const send=BattleStream.prototype.pushMessage,consume=PlayerStateExtractor.prototype.consumeChunk;
  const produced:Record<PlayerID,string[]>={p1:[],p2:[]},received:Record<PlayerID,string[]>={p1:[],p2:[]};
  BattleStream.prototype.pushMessage=function(type,data) {
    if(type==='sideupdate') {const [owner,...text]=data.split('\n');if(text[0]?.startsWith('|request|')) produced[owner as PlayerID].push(text.join('\n'));}
    return send.call(this,type,data);
  };
  PlayerStateExtractor.prototype.consumeChunk=function(chunk) {
    const owner=this.player;
    for(const text of chunk.split('\n')) if(text.startsWith('|request|')) received[owner].push(text);
    return consume.call(this,chunk);
  };
  let session:PipelineIntegrationSession|undefined;
  try {
    session=await PipelineIntegrationSession.create({battle_id:'prompt24-actual',format:FORMAT,seed:SEED});
    const env=(session as any).environment as LocalBattleEnv;
    for(const owner of ['p1','p2'] as const) {
      const trace=rows(env,owner);assert.equal(trace.length,1);assert.equal(trace[0].origin,'native_emission');
      assert.deepEqual(trace.map(r=>r.request_record),produced[owner]);assert.deepEqual(trace.map(r=>r.receipt.record),received[owner]);
      assert.ok(trace[0].request_json.startsWith('{"active":'));assert.ok(trace[0].request_json.includes(`"id":"${owner}"`));
    }
    const old=env.getRequestEmissionTraceHandle('p1');await session.step();
    assert.throws(()=>env.inspectRequestEmissionTrace(old,'p1'),/unavailable/);
    const candidate=(session as any).environment as LocalBattleEnv;
    for(const owner of ['p1','p2'] as const) assert.deepEqual(rows(candidate,owner).map(r=>r.origin),['restore_reemit','native_emission']);
    const wire=JSON.stringify({boundary:session.boundary,snapshot:candidate.serializeBattle(),diagnostics:candidate.diagnostics()});
    assert.ok(!wire.includes('producer_occurrence') && !wire.includes('owner_emission_index') && !wire.includes('request_record'));
  } finally {BattleStream.prototype.pushMessage=send;PlayerStateExtractor.prototype.consumeChunk=consume;await session?.close();}
});

async function state(own:string,foe:string,owner:PlayerID,rounds:string[]=[]):Promise<Record<string,any>> {
  const stream=new BattleStream({keepAlive:true});const teams={[owner]:own,[other(owner)]:foe};
  try {
    await stream.write([`>start ${JSON.stringify({formatid:FORMAT,seed:SEED})}`,
      ...(['p1','p2'] as const).map(p=>`>player ${p} ${JSON.stringify({name:p,team:Teams.pack(Teams.import(teams[p]))})}`)].join('\n'));
    for(const round of rounds) {const [a,b]=round.split('/');await stream.write([a&&`>${owner} ${a}`,b&&`>${other(owner)} ${b}`].filter(Boolean).join('\n'));}
    return structuredClone((stream as any).battle.toJSON());
  } finally {stream.destroy();}
}

test('actual Unicode and formatted literal producer records, repeated equal emissions preserve receipt FIFO',async()=>{
  const generate=Teams.generate;let i=0;
  Teams.generate=function(){return Teams.import(`${UNICODE}${i++===0?'':'-foe'} (Snorlax)\nAbility: Immunity\n- Splash`)!;};
  const env=new LocalBattleEnv('literal',FORMAT,SEED);
  try {
    await env.resetWithOptions(OPTIONS);
    for(const owner of ['p1','p2'] as const) assert.ok(rows(env,owner)[0].request_json.includes(UNICODE));
    await (env as any).battleStream.write('>eval p1.emitRequest(p1.activeRequest); p1.emitRequest(p1.activeRequest); p2.emitRequest(p2.activeRequest);');
    await env.stepWithOptions({},OPTIONS);
    assert.equal(rows(env,'p1').length,3);assert.equal(rows(env,'p2').length,2);
    assert.equal(rows(env,'p1')[0].request_record,rows(env,'p1')[2].request_record);
    assert.deepEqual(rows(env,'p1').map(r=>r.owner_emission_index),[1,2,3]);
    for(const owner of ['p1','p2'] as const) {
      const literal=`|request| { "wait":true, "side":{"id":"${owner}","pokemon":[]}, "literal":"${UNICODE}" }\t `;
      await (env as any).battleStream.write(`>eval battle.send("sideupdate",${JSON.stringify(owner+'\n'+literal)});`);
      await env.stepWithOptions({},OPTIONS);
      assert.equal(rows(env,owner).at(-1)!.request_record,literal);assert.equal(rows(env,owner).at(-1)!.receipt.record,literal);
      assert.equal(rows(env,owner).at(-1)!.request_json,literal.slice(9));
      await (env as any).battleStream.write(`>eval ${owner}.emitRequest(${owner}.activeRequest);`);
      await env.stepWithOptions({},OPTIONS);
    }
  } finally {Teams.generate=generate;await env.close();}
});

test('actual restore receipt delayed beyond later native emission keeps producer classifications',async()=>{
  const donor=new LocalBattleEnv('delay-donor',FORMAT,SEED),env=new LocalBattleEnv('delayed',FORMAT,SEED);
  const bind=RequestEmissionTrace.prototype.bind,atProducer=RequestEmissionTrace.prototype.atProducer;
  let release!:()=>void,ready!:()=>void,restoreCalls=0;
  const gate=new Promise<void>(r=>{release=r;}),produced=new Promise<void>(r=>{ready=r;});
  let restoring:Promise<unknown>|undefined;
  try {
    await donor.reset();const snapshot=donor.serializeBattle();
    RequestEmissionTrace.prototype.bind=function(owner,stream) {
      const held=stream as any,iterate=held[Symbol.asyncIterator];
      held[Symbol.asyncIterator]=function() {
        const iterator=iterate.call(this);
        return {next:async()=>{await gate;return iterator.next();},[Symbol.asyncIterator](){return this;}};
      };
      return bind.call(this,owner,stream);
    };
    RequestEmissionTrace.prototype.atProducer=function(origin,emit) {
      atProducer.call(this,origin,emit);
      if(origin==='restore_reemit' && ++restoreCalls===2) ready();
    };
    restoring=env.resetFromSerialized(snapshot,OPTIONS);await produced;
    assert.throws(()=>rows(env,'p1'),/unreceived-emission/);
    await (env as any).battleStream.write('>eval p1.emitRequest(p1.activeRequest); p2.emitRequest(p2.activeRequest);');
    assert.throws(()=>rows(env,'p2'),/unreceived-emission/);
    release();await restoring;
    for(const owner of ['p1','p2'] as const) {
      const trace=rows(env,owner);assert.deepEqual(trace.map(r=>r.origin),['restore_reemit','native_emission']);
      assert.equal(trace[0].request_record,trace[1].request_record);
      assert.deepEqual(trace.map(r=>r.receipt.owner_receipt_index),[1,2]);
    }
  } finally {
    release();await restoring?.catch(()=>{});
    RequestEmissionTrace.prototype.bind=bind;RequestEmissionTrace.prototype.atProducer=atProducer;
    await donor.close();await env.close();
  }
});

for(const owner of ['p1','p2'] as const) {
  test(`restore receipts remain restore-labelled; later native trap resend/force/wait/revival for ${owner}`,async()=>{
    const cases=[
      {label:'trap',own:'Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n\nBlissey\n- Splash',foe:'Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\n- Splash',rounds:[],choice:'switch 2'},
      {label:'force',own:'Mewtwo\nAbility: Pressure\n- Psystrike\n- Splash\n\nBlissey\n- Splash',foe:'Magikarp\n- Splash\n\nSnorlax\n- Splash',rounds:['move 1/move 1'],choice:''},
      {label:'revival',own:'Lead (Snorlax)\nAbility: Immunity\n- Memento\n\nPawmot\n- Revival Blessing\n- Splash',foe:'Terminus (Snorlax)\nAbility: Immunity\n- Splash\n- Memento\n\nReserve (Blissey)\n- Splash',rounds:['move 1/move 1','switch 2/','move 1/move 2'],choice:''},
    ];
    for(const c of cases) {
      const snapshot=await state(c.own,c.foe,owner,c.rounds),env=new LocalBattleEnv(c.label,FORMAT,SEED);
      try {
        const result=await env.resetFromSerialized(snapshot,OPTIONS);
        for(const p of ['p1','p2'] as const) assert.ok(rows(env,p).every(r=>r.origin==='restore_reemit'));
        if(c.label==='trap') {
          await env.stepWithOptions({[owner]:c.choice},OPTIONS);
          const traced=rows(env,owner);assert.equal(traced.length,2);assert.equal(traced[1].origin,'native_emission');
          assert.equal(JSON.parse(traced[1].request_json).active[0].trapped,true);
          await env.stepWithOptions({[owner]:'move 2',[other(owner)]:'move 1'},OPTIONS);
          assert.equal(rows(env,owner).at(-1)!.origin,'native_emission');
        } else {
          const waiting=c.label==='force'?owner:other(owner),selector=other(waiting);
          assert.ok(result.requests[waiting]!.wait);assert.ok(result.requests[selector]!.force_switch);
          assert.equal(JSON.parse(rows(env,waiting)[0].request_json).wait,true);
          if(c.label==='revival') assert.ok(JSON.parse(rows(env,selector)[0].request_json).side.pokemon.some((p:any)=>p.reviving));
          await (env as any).battleStream.write(`>eval ${owner}.emitRequest(${owner}.activeRequest); ${other(owner)}.emitRequest(${other(owner)}.activeRequest);`);
          await env.stepWithOptions({},OPTIONS);
          for(const p of ['p1','p2'] as const) assert.equal(rows(env,p).at(-1)!.origin,'native_emission');
          const counts={p1:rows(env,'p1').length,p2:rows(env,'p2').length};
          const select=result.requests[selector]!.legal_actions.actions.find(a=>a?.kind===(c.label==='revival'?'revive':'switch'))!;
          assert.ok(select);await env.stepWithOptions({[selector]:select.choice},OPTIONS);
          for(const p of ['p1','p2'] as const) {
            const continued=rows(env,p).slice(counts[p]);assert.ok(continued.length>0);
            assert.ok(continued.every(r=>r.origin==='native_emission'));
          }
        }
      } finally {await env.close();}
    }
  });
}

test('no-emission and terminal/history restoration do not invent requests; reset and close revoke old access',async()=>{
  const env=new LocalBattleEnv('lifetime',FORMAT,SEED),restored=new LocalBattleEnv('terminal',FORMAT,SEED);
  try {
    await env.resetWithOptions(OPTIONS);const old=env.getRequestEmissionTraceHandle('p1'),before=rows(env,'p1');
    await env.stepWithOptions({},OPTIONS);assert.deepEqual(rows(env,'p1'),before);
    await env.resetWithOptions(OPTIONS);assert.throws(()=>env.inspectRequestEmissionTrace(old,'p1'),/foreign-or-forged/);
    assert.notEqual(rows(env,'p1')[0].producer_occurrence,before[0].producer_occurrence);
    assert.equal(rows(env,'p1')[0].emission_index,before[0].emission_index);
    await (env as any).battleStream.write('>forcewin p1');const terminal=await env.stepWithOptions({},OPTIONS);
    assert.equal(terminal.requests.p1,null);assert.equal(rows(env,'p1').length,1);
    await restored.resetFromSerialized(env.serializeBattle(),OPTIONS);
    assert.deepEqual(rows(restored,'p1'),[]);assert.deepEqual(rows(restored,'p2'),[]);
    const handle=env.getRequestEmissionTraceHandle('p1'),stream=(env as any).battleStream;
    const end=stream.writeEnd;stream.writeEnd=async function(){assert.throws(()=>env.inspectRequestEmissionTrace(handle,'p1'),/unavailable/);throw new Error('synthetic cleanup failure');};
    await assert.rejects(env.close(),/cleanup failure/);assert.throws(()=>env.getRequestEmissionTraceHandle('p1'),/unavailable/);
    stream.writeEnd=end;
  } finally {await env.close();await restored.close();}
});

test('failed initialization and unknown direct producer cannot leave usable partial trace',async()=>{
  const generate=Teams.generate,env=new LocalBattleEnv('failure',FORMAT,SEED);let calls=0;
  Teams.generate=function(...args){if(++calls===2)throw new Error('synthetic generation failure');return generate.apply(this,args);};
  try {await assert.rejects(env.reset(),/generation failure/);assert.throws(()=>env.getRequestEmissionTraceHandle('p1'),/unavailable/);}
  finally {Teams.generate=generate;await env.close();}
  const live=new LocalBattleEnv('unknown',FORMAT,SEED);
  try {await live.reset();assert.throws(()=>(live as any).battleStream.pushMessage('sideupdate',`p1\n${record}`),/unsupported-producer/);
    assert.throws(()=>live.getRequestEmissionTraceHandle('p1'),/invalidated/);}
  finally {await live.close();}
});
