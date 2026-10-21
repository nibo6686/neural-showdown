const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const {Teams}=require('../node_modules/pokemon-showdown');
const {PipelineIntegrationSession}=require('../dist/src/pipeline_integration');
const {OwnedRequestHealthHost}=require('../dist/src/owned_request_health');
const {activeRequestOverrideDiagnostics:diagnostics}=require('../dist/src/env_manager');
const {canonicalActionFromLegalAction}=require('../dist/src/canonical_action');
const versions=require('../dist/src/version_profile');
const emit=(name,data)=>console.log('P51_WITNESS '+JSON.stringify({name,...data}));
function historicalVersions(){
 assert.ok(process.env.NEURAL_HISTORICAL_SIM_CORE,'NEURAL_HISTORICAL_SIM_CORE must name an installed 0.11.10 sim-core checkout for historical controls');
 return require(path.resolve(process.env.NEURAL_HISTORICAL_SIM_CORE,'dist/src/version_profile'));
}
function validator(historical=false){
 const filename=path.resolve(__dirname,'../dist/src/env_manager.js'),m=new Module(filename,module);
 m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));
 if(historical){const load=m.require.bind(m);m.require=name=>name==='./version_profile'?historicalVersions():load(name);}
 m._compile(fs.readFileSync(filename,'utf8')+'\nexports.exactValidatorTestOnly=validateActiveRequestOverride;',filename);
 return m.exports.exactValidatorTestOnly;
}
test('P51 exact target marker and historical strict validator controls',t=>{
 const check=validator(),runtime=versions.installedNativeProfile();
 const base={side:{id:'p1',pokemon:[{ident:'p1: Alpha',condition:'10/10'}]},active:[{maybeTrapped:true,moves:[{id:'splash',move:'Splash',pp:10,maxpp:10,target:'self',disabled:false}]}]};
 const side={activeRequest:base,active:[{trapped:true,getLockedMove:()=>null,getMoves:()=>[{id:'splash',disabled:true}]}]};
 const trap=()=>{const live=structuredClone(base);delete live.active[0].maybeTrapped;live.active[0].trapped=true;live.update=true;return live;};
 const disabled=()=>{const live=structuredClone(base);live.active[0].moves[0].disabled=true;live.active[0].moves[0].disabledSource='Disable';live.update=true;return live;};
 for(const live of [trap(),disabled()]){const bytes=JSON.stringify(live);check(live,side,'p1',runtime);assert.equal(JSON.stringify(live),bytes);}
 const noMarker=trap();delete noMarker.update;check(noMarker,side,'p1',runtime);
 for(const marker of [false,'true',null,0]){const live=trap();live.update=marker;assert.throws(()=>check(live,side,'p1',runtime),/literal native update:true/);}
 const faults={unknown:l=>l.extra=true,noop:l=>Object.assign(l,structuredClone(base),{update:true}),owner:l=>l.side.id='p2',health:l=>l.side.pokemon[0].condition='1/10',move:l=>l.active[0].moves[0].pp=9};
 for(const [fault,edit] of Object.entries(faults)){const live=trap();edit(live);assert.throws(()=>check(live,side,'p1',runtime),fault==='noop'?/does not edit/:fault==='unknown'?/keys that differ/:/engine-legal edit/);}
 assert.throws(()=>check(trap(),{...side,active:[{...side.active[0],trapped:false}]},'p1',runtime),/not trapped/);
 assert.throws(()=>check(disabled(),{...side,active:[{...side.active[0],getMoves:()=>[{id:'splash',disabled:false}]}]},'p1',runtime),/not disabled/);
 assert.throws(()=>check(trap(),side,'p1',{...runtime}),/unowned-runtime-profile/);
 if(!process.env.NEURAL_HISTORICAL_SIM_CORE) { t.diagnostic('Retired live 0.11.10 marker controls; committed historical reader fixtures remain in version_context'); return; }
 const oldVersions=historicalVersions(),old=oldVersions.installedNativeProfile(),oldCheck=validator(true);
 assert.equal(old.package_version,'0.11.10');assert.throws(()=>oldCheck(trap(),side,'p1',old),/keys that differ/);oldCheck(noMarker,side,'p1',old);
 emit('finite-validator',{level:'lower-level-validator-with-model-side-not-native-authority',target_true_and_real_edit:true,disabled_and_trap_truth_checks:true,literal_input_unchanged:true,update_only_noop_rejected:true,owned_historical_runtime:old.package_version,historical_marker_rejected:true,copied_runtime_rejected:true});
});
test('P51 actual native update serializer and committed-source boundary',async()=>{
 const generate=Teams.generate,received=OwnedRequestHealthHost.prototype.received,onDrop=diagnostics.onDrop;
 const recipients={p1:{},p2:{}},teams=['Snorlax\nAbility: Immunity\n- Splash\n\nBlissey\nAbility: Healer\n- Splash','Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash'];
 let count=0,s,overlay,emitted,drop,sourceSeen=false;
 Teams.generate=()=>Teams.import(teams[count++]);diagnostics.onDrop=row=>drop=row;
 OwnedRequestHealthHost.prototype.received=function(e,producer,receipt){
  received.call(this,e,producer,receipt);
  if(!sourceSeen&&receipt.owner==='p1'&&JSON.parse(receipt.request_json)?.update===true){sourceSeen=true;emitted=receipt.request_json;overlay=e.serializeBattle().__neural_active_request_overrides?.requests?.p1;}
 };
 try{
  s=await PipelineIntegrationSession.create({battle_id:'P51-native-update',format:'gen9randombattle',seed:[1,2,3,4],knowledge_recipients:recipients});
  const boundary=s.boundary,handle=s.getOwnerKnowledgeHandle(recipients.p1),pair=s.readOwnerKnowledge(handle,recipients.p1),history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),native=s.getNativeObjectHolding('p1');
  const action=(p,text)=>{const req=s.boundary.perspectives[p].observation.request;return canonicalActionFromLegalAction(req,req.legal_actions.actions.find(a=>a?.choice===text).index);};
  await assert.rejects(s.step({p1:action('p1','switch 2'),p2:action('p2','move 1')}),/rejected-action/);assert.ok(sourceSeen);
  if(!overlay){emit('native-overlay-blocker',{actual_native_update:true,serializer_drop:drop?.reason,committed_overlay_consumer:'UNPROVED'});assert.fail('genuine updated overlay still dropped: '+drop?.reason);}
  assert.equal(overlay.update,true);assert.equal(overlay.active[0].trapped,true);assert.equal(Object.hasOwn(overlay.active[0],'maybeTrapped'),false);assert.equal(JSON.stringify(overlay),emitted);
  assert.equal(s.boundary,boundary);assert.equal(s.getOwnerKnowledgeHandle(recipients.p1),handle);assert.equal(s.readOwnerKnowledge(handle,recipients.p1),pair);assert.equal(s.getNativeObjectHolding('p1'),native);assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),history);
  assert.equal(history.deliveries.length,1);const initial=s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(recipients.p2),recipients.p2);assert.equal(initial.projection.owner,'p2');
  // Fresh retry follows the supported session path; it does not adopt the discarded overlay.
  await s.step({p1:action('p1','move 1'),p2:action('p2','move 1')});assert.equal(s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(recipients.p1),recipients.p1).projection.starting,pair.projection.starting);
  emit('native-serializer',{level:'actual-constructed-native-error-update-and-serializer',literal_overlay_equals_emitted_json:true,marker_retained:true,genuine_trap_edit:true,affected_snapshot_delta:'adds exact __neural_active_request_overrides.requests.p1 payload formerly dropped',rejected_candidate_not_committed:true,parent_and_original_history_unchanged:true,fresh_retry:true,held_overlay_B2_delivery_consumer:'UNPROVED-no-supported-rejected-choice-commit'});
 }finally{Teams.generate=generate;OwnedRequestHealthHost.prototype.received=received;diagnostics.onDrop=onDrop;await s?.close();}
});
