const root='/private/tmp/neural-showdown-native11-prompt38';
const assert=require('node:assert/strict');
const {Teams}=require(root+'/sim-core/node_modules/pokemon-showdown');
const {PipelineIntegrationSession}=require(root+'/sim-core/dist/src/pipeline_integration');
const {OwnedRequestHealthHost}=require(root+'/sim-core/dist/src/owned_request_health');
const {activeRequestOverrideDiagnostics:diag}=require(root+'/sim-core/dist/src/env_manager');
const {canonicalActionFromLegalAction}=require(root+'/sim-core/dist/src/canonical_action');
const generate=Teams.generate,received=OwnedRequestHealthHost.prototype.received,onDrop=diag.onDrop;
const teams=['Snorlax\nAbility: Immunity\n- Splash\n\nBlissey\nAbility: Healer\n- Splash','Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash'];
let calls=0,s,observed=false,hasOverlay,drop;
Teams.generate=()=>Teams.import(teams[calls++]);
diag.onDrop=row=>{if(row.player==='p1')drop={path:row.path,reason:row.reason};};
OwnedRequestHealthHost.prototype.received=function(e,emission,receipt){
 received.call(this,e,emission,receipt);
 if(!observed&&receipt.owner==='p1'&&JSON.parse(receipt.request_json)?.update===true){
  observed=true;hasOverlay=!!e.serializeBattle().__neural_active_request_overrides?.requests?.p1;
 }
};
(async()=>{
 try{
  s=await PipelineIntegrationSession.create({battle_id:'P50-overlay-boundary',format:'gen9randombattle',seed:[1,2,3,4],knowledge_recipients:{p1:{},p2:{}}});
  const action=(p,text)=>{const request=s.boundary.perspectives[p].observation.request;return canonicalActionFromLegalAction(request,request.legal_actions.actions.find(a=>a?.choice===text).index);};
  await assert.rejects(s.step({p1:action('p1','switch 2'),p2:action('p2','move 1')}),/rejected-action/);
  assert.ok(observed);assert.equal(hasOverlay,false);assert.match(drop?.reason??'',/keys that differ from the regenerated request/);
  console.log('P50_OVERLAY_BOUNDARY '+JSON.stringify({actual_native_updatedRequest:true,existing_validator_drop:drop,health_overlay_positive_integration:'UNPROVED',validator_preserved:true}));
 }finally{Teams.generate=generate;OwnedRequestHealthHost.prototype.received=received;diag.onDrop=onDrop;await s?.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
