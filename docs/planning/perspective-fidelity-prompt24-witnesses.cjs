const fs=require('node:fs');
const assert=require('node:assert/strict');
const {BattleStream,Teams}=require('../../sim-core/node_modules/pokemon-showdown');
const {LocalBattleEnv}=require('../../sim-core/dist/src/env_manager');
const {PlayerStateExtractor}=require('../../sim-core/dist/src/state_extractor');
const options={include_wait_requests:true,include_possible_roles:false};
const produced={p1:[],p2:[]},received={p1:[],p2:[]};
const send=BattleStream.prototype.pushMessage,consume=PlayerStateExtractor.prototype.consumeChunk,generate=Teams.generate;
const unicode='\u00e9-\u03a9\u{1f600}';let generated=0;
Teams.generate=()=>Teams.import(`${unicode}${generated++===0?'':'-foe'} (Snorlax)\nAbility: Immunity\n- Splash`);
BattleStream.prototype.pushMessage=function(type,data){if(type==='sideupdate'){const i=data.indexOf('\n'),p=data.slice(0,i),r=data.slice(i+1);if(r.startsWith('|request|'))produced[p].push(r);}return send.call(this,type,data);};
PlayerStateExtractor.prototype.consumeChunk=function(chunk){for(const r of chunk.split('\n'))if(r.startsWith('|request|'))received[this.player].push(r);return consume.call(this,chunk);};
const env=new LocalBattleEnv('prompt24-witness', 'gen9randombattle',[1,2,3,4]);
const inspect=p=>env.inspectRequestEmissionTrace(env.getRequestEmissionTraceHandle(p),p);
(async()=>{try{
  await env.resetWithOptions(options);
  await env.battleStream.write('>eval p1.emitRequest(p1.activeRequest); p2.emitRequest(p2.activeRequest);');
  await env.stepWithOptions({},options);
  const output={scope:'diagnostic literals; synthetic Unicode inputs through actual native producer/routed receipt, no transported authority',owners:{}};
  for(const p of ['p1','p2']){
    const trace=inspect(p);assert.deepEqual(trace.map(r=>r.request_record),produced[p]);assert.deepEqual(trace.map(r=>r.receipt.record),received[p]);
    assert.equal(trace[0].request_record,trace[1].request_record);assert.ok(trace[0].request_json.includes(unicode));
    output.owners[p]={rows:trace.map(r=>({...r,producer_occurrence:'diagnostic-marker-only',record_utf8_hex:Buffer.from(r.request_record,'utf8').toString('hex')})),independent_producer_records:produced[p],independent_receipt_records:received[p]};
  }
  fs.writeFileSync(__dirname+'/perspective-fidelity-prompt24-literal-witnesses.json',JSON.stringify(output,null,2)+'\n','utf8');
  console.log('both owners: exact native producer/routed receipts, Unicode bytes, two equal-text distinct occurrences');
}finally{Teams.generate=generate;BattleStream.prototype.pushMessage=send;PlayerStateExtractor.prototype.consumeChunk=consume;await env.close();}})().catch(e=>{console.error(e);process.exitCode=1});
