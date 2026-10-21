import {validateProtocolContract, ProtocolContractError} from './protocol_contract';
import {assertPreparedInspectionAvailable, assertPreparedRecordCheckInput, HISTORICAL10_CONTEXT, NATIVE11_GRAMMAR_CONTEXT, REPLAY_COMPAT_CONTEXT} from './version_profile';
import {validateRawProtocolRecord} from './observable_state';
export type PreparedProfile = 'native11' | 'replay-compat-v1';
const scope = 'PRE grammar only; no native runtime, semantic closure or publication acceptance';
const framing = 'Historical separator shape reused for PRE grammar; target emission UNEXECUTED';
const oldNC = '|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure';
const nativeNC = oldNC + '|[silent]';
const commonStops = ['heal', 'cant', '-swapsideconditions'];
const lifted = ['-start','-end','-sidestart','-sideend','-weather','-fieldstart','-fieldend','cant','heal','-swapsideconditions'];
const semantic = {natural_cure:'prepared-status-clear-existing-helper-path',ability_setter:'unsupported-unproved-typed-base-current-transition',
 heal_failure:'unsupported-unproved-attribution-routing',chilly_reception:'unsupported-premajor-helper-gap',partial_trap:'unsupported-sourceEffect-semantics',
 court_change:'unsupported-retargeted-lifecycle',magician:'unsupported-actor-source-attribution',psychic_terrain_hint:'raw-only-presentation-no-typed-consequence',
 effect_lifecycle:'unsupported-target-closure-unproved',admin_nonselected:'unsupported-existing-stop'};
const provenance = {historical_contract_sha256:'4cbea57639e3a5d11e8387f9f84befcc531a613b13175351630b4377d087c213',
 old_abilities_sha256:'7975eb69496fb38ec8c9f2d7288dedea14e78ec81579f6e2b58ad1c9716d3ce6',target_abilities_sha256:'175067b1e827ca11ae4728169215c9bdd27ac4cb3e35d2e83eaaaee7e9e8c842',
 target_revision:'739a5e1fee432ad80ff7136d70cca993be358b59',source:'Prompt29 verified npm artifacts; abilities.ts old onSwitchOut and target 2868–2875; ordinary add routes shared/public',runtime:'UNEXECUTED'};
function fail(code:string):never {throw new ProtocolContractError('prepared-protocol-contract/v1/'+code);}
function equal(a:any,b:any):boolean {
 if(Array.isArray(a)||Array.isArray(b))return Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>equal(v,b[i]));
 if(a&&b&&typeof a==='object'&&typeof b==='object')return equal(Object.keys(a).sort(),Object.keys(b).sort())&&Object.keys(a).every(k=>equal(a[k],b[k]));
 return a===b;
}
function keys(v:any,wanted:string[],label:string):void {
 if(!v||typeof v!=='object'||Array.isArray(v)||!equal(Object.keys(v).sort(),wanted.slice().sort()))fail(label+'-keys');
}
function plain(v:any,active=new Set<object>()):void {
 if(v===null||typeof v==='string'||typeof v==='boolean'||typeof v==='number'&&Number.isFinite(v))return;
 if(!v||typeof v!=='object'||active.has(v))fail('plain-json');
 const proto=Object.getPrototypeOf(v);if(!Array.isArray(v)&&proto!==Object.prototype&&proto!==null)fail('plain-json');
 if(Array.isArray(v)&&!equal(Object.keys(v),Array.from({length:v.length},(_,i)=>String(i))))fail('plain-json');
 active.add(v);for(const key of Reflect.ownKeys(v)){
  if(typeof key!=='string')fail('plain-json');if(Array.isArray(v)&&key==='length')continue;
  const descriptor=Object.getOwnPropertyDescriptor(v,key)!;if(!Object.hasOwn(descriptor,'value'))fail('plain-json');plain(descriptor.value,active);
 }active.delete(v);
}
function selected(profile:unknown):asserts profile is PreparedProfile {if(profile!=='native11'&&profile!=='replay-compat-v1')fail('profile');}
/** Inspection only. Explicit normalization follows checks on the original data; no keys/records are dropped. */
export function validatePreparedProtocolStructure(value:any,profile:PreparedProfile):void {
 selected(profile);plain(value);
 const common=['schema_version','profile','adopted','provenance','protocol','inherited_raw_shape_evidence'];
 keys(value,common.concat(profile==='native11'?['admission_scope','semantic_dispositions']:['base_lookup_profile','publication','authority','changed_forms']),'container');
 if(value.profile!==profile||value.adopted!==false||value.schema_version!==(profile==='native11'?'inactive-native-protocol/v1':'importer-replay-compatibility/v1'))fail('profile-identity');
 const selectedProvenance=profile==='native11'?{...provenance,target_revision:'b8f23c99629132611ba59e99480cb148ea8c5d3d',target_abilities_sha256:'52298a24ba0fa5b33750455042ce1b8d66a14d95250368f15cbdd96b356b6796',engine_integrity:'sha512-ihktUZgY1oy6U7TyCDmHg4lUlPeMb2jcedhqOnc/R0GIAeMgMFTlIDzmVsZ1xjBJ4ddaa/OM8dpfNsqo1dNe3Q==',source:"P0.4 pinned compiled abilities and gen9 set inputs; inherited finite Natural Cure, Trace and Revival grammar",runtime:"Prompt41 Trace and Prompt42 finite Revival native integration checks; broader runtime closure unproved"}:provenance;
 if(!equal(value.provenance,selectedProvenance))fail('provenance');
 if(!equal(value.inherited_raw_shape_evidence,{contract_sha256:provenance.historical_contract_sha256,scope:'Historical raw rule baseline; fresh PRE fixture checks, no target acceptance'}))fail('inherited-evidence');
 if(profile==='native11'){
  if(!equal(value.admission_scope,['Inherited historical raw-shape baseline, not semantic acceptance','Natural Cure exact ordered source-tag then silent','Trace exact prior-Trace positional field and opposing active source','Revival Blessing exact public bench 50/100 heal; silent faint/status clear'])||!equal(value.semantic_dispositions,{...semantic,effect_lifecycle:'source-reviewed classes; uncovered deltas unsupported-fail-closed',partial_trap:'public-damage-only; binding-source-and-duration-untyped',chilly_reception:'exact-premajor-prepare; transient-state-raw-only',heal_failure:'historical-raw-shapes; no inferred attribution',trace:'finite-source-qualified-current-copy; prior field is provenance only',revival:'finite-public-bench-health-status-faint-clear; owned selection remains required'}))fail('closure-claims');
 }else if(value.base_lookup_profile!=='historical10'||value.publication!=='unsupported-without-persisted-profile-contract'||value.authority!==false||!equal(value.changed_forms,['Natural Cure historical ordered from-tag','Natural Cure native11 ordered from-tag then silent']))fail('closure-claims');
 const base=JSON.parse(JSON.stringify(HISTORICAL10_CONTEXT.protocol)),p=value.protocol;
 keys(p,Object.keys(base),'protocol');
 if(!equal(p.source_basis,[profile==='native11'?"Historical raw rule templates and Prompt29 Natural Cure; Prompt41 source-qualified target Trace; only finite Trace emitter/audience and owned publication controls executed, broader closure unproved; Prompt42 finite public Revival bench heal":'Historical raw rule templates and Prompt29 exact Natural Cure writer; PRE only, runtime/publication UNEXECUTED']))fail('source-claims');
 if(!equal(p.simulator,{...base.simulator,version:profile==='native11'?'0.11.11':'0.11.10',...(profile==='native11'?{engine_commit:'b8f23c99629132611ba59e99480cb148ea8c5d3d'}:{})}))fail('simulator');
 const rules=JSON.parse(JSON.stringify(base.validation_rules));
 const form={tags:['[from] ability: Natural Cure','[silent]']};
 if(profile==='native11')rules.major_status.cure_forms=rules.major_status.cure_forms.map((x:any)=>equal(x.tags,['[from] ability: Natural Cure'])?form:x);
 else rules.major_status.cure_forms.push(form);
 if(profile==='native11'){
  rules.item.payloads=[...rules.item.payloads,'Covert Cloak','Expert Belt','Insect Plate','Life Orb','Rusted Shield','Rusted Sword'].sort();
  rules.partial_trap={move_names:['Bind','Clamp','Fire Spin','Infestation','Magma Storm','Sand Tomb','Snap Trap','Thunder Cage','Whirlpool','Wrap']};
  rules.item.dash_item_forms.push({tags:['[from] ability: Harvest'],payloads:rules.item.payloads.filter((name:string)=>name.endsWith(' Berry'))});
  rules.ability.dash_templates=['reveal','boost','trace-copy-prior-Trace'];
  rules.ability.payload_domains.dash_trace_copy=rules.ability.payload_domains.dash_trace_copy.filter((a:string)=>a!=='Steely Spirit').concat('Gale Wings').sort();
  rules.ability.source_evidence.dash_trace_copy='Target 0.11.11 gen9 sets candidate abilities filtered by target Trace notrace/noability guard; Gardevoir sole Trace selector; Prompt41 finite source qualification';
 }
 if(!equal(p.validation_rules,rules))fail('rule-template');
 if(!equal(p.framing_only_records,[{...base.framing_only_records[0],evidence:framing}]))fail('framing');
 if(!equal(p.disposition_rules,Object.fromEntries(Object.keys(base.disposition_rules).map(k=>[k,scope]))))fail('disposition-claims');
 const stops=new Set(profile==='native11'?[]:commonStops);
 const wanted=base.supported_commands.filter((x:string)=>!stops.has(x));
 if(!Array.isArray(p.supported_commands)||!equal(p.supported_commands.slice().sort(),wanted.slice().sort()))fail('token-partition');
 if(!Array.isArray(p.recognized_unsupported_commands))fail('unsupported-entries');
 const expected=new Map<string,string>(base.recognized_unsupported_commands.map((x:any)=>[x.token,x.kind]));
 // The existing prepared assets also classify the pre-existing bare swap alias as unproved.
 expected.set('swapsideconditions','unproved_semantic_family');for(const token of stops)expected.set(token,'unproved_semantic_family');
 const actual=new Map<string,string>();for(const x of p.recognized_unsupported_commands){
  if(!x||typeof x.token!=='string'||actual.has(x.token)||x.kind!==expected.get(x.token))fail('unsupported-classification');actual.set(x.token,x.kind);
 }
 if(!equal([...actual.keys()].sort(),[...expected.keys()].sort()))fail('token-partition');
 const entries=new Map<string,any>(base.recognized_unsupported_commands.map((x:any)=>[x.token,x]));
 for(const token of stops)entries.set(token,{token,kind:'unproved_semantic_family',reason:'Prepared profile rejects this token; semantic/runtime closure unproved'});
 entries.set('swapsideconditions',{token:'swapsideconditions',kind:'unproved_semantic_family',reason:'Prepared Court Change family quarantine, including bare alias'});
 for(const x of p.recognized_unsupported_commands)if(!equal(x,entries.get(x.token)))fail('unsupported-evidence');

 const projection=JSON.parse(JSON.stringify(p));projection.simulator=base.simulator;projection.validation_rules=base.validation_rules;projection.framing_only_records=base.framing_only_records;
 for(const x of projection.recognized_unsupported_commands)if(x.kind==='unproved_semantic_family')x.kind='unsupported_stop';
 if(!Array.isArray(p.rejection_fixtures))fail('negative-controls');
 for(const x of p.rejection_fixtures)if(!x||typeof x!=='object'||Array.isArray(x))fail('negative-controls');
 for(let i=0;i<p.rejection_fixtures.length;i++)if(p.rejection_fixtures[i].kind==='unproved_semantic_family'){
  const token=typeof p.rejection_fixtures[i].record==='string'?p.rejection_fixtures[i].record.split('|')[1]:'';
  if(!wanted.includes(token)&&actual.get(token)!=='unproved_semantic_family')fail('negative-classification');
  projection.rejection_fixtures[i].kind=wanted.includes(token)?'malformed':'unsupported_stop';
 }
 try{validateProtocolContract(projection);}catch(e){fail('protocol-structure: '+(e as Error).message);}
 if(profile==='native11'&&!p.valid_record_controls.some((x:any)=>x.record==="|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey"))fail('trace-controls');
 for(const fixture of p.record_fixtures){
  if(fixture.inventory_classification!=='raw-only')fail('fixture-acceptance-claim');
  if(fixture.grammar_summary!==scope||fixture.evidence!==(profile==='native11'&&lifted.includes(fixture.token)?'P0.5b source-compared historical grammar control':'Prompt37 fixed selected grammar control')||!equal(fixture.inventory_grammar,{required:'exact selected profile record',optional:'only reviewed rule-template forms',shape:'validated against fixed grammar and quarantine'})||Object.hasOwn(fixture,'pinned_emitter_sources')||Object.hasOwn(fixture,'pinned_dynamic_emitter_source'))fail('fixture-evidence');
  const match=/^control:(0|[1-9][0-9]*)$/.exec(fixture.fixture_reference);const control=match&&p.valid_record_controls[Number(match[1])];
  if(!control||fixture.record!==control.record||fixture.token!==control.token)fail('fixture-reference');
 }
 for(const control of p.valid_record_controls){
  if(control.reconstruction_scope!==scope)fail('control-scope');
  const evidence=profile==='native11'&&lifted.includes(control.token)?'P0.5b source-compared historical grammar control':profile==='native11'&&control.record==="|-heal|p1: First|50/100|[from] move: Revival Blessing"?"Prompt42 source-qualified Revival public bench heal and bounded held-restoration publication; no general healing or completeness acceptance":profile==='native11'&&control.record==="|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey"?"Prompt41 source-qualified target Trace; actual native emitter/audience witness and bounded owned publication controls; no completeness or positive fidelity acceptance":profile==='replay-compat-v1'&&control.record===nativeNC?'Verified target Natural Cure source form; PRE only':'Prompt37 bounded fixed-grammar fixture check; no target engine execution';
  if(control.evidence!==evidence)fail('control-evidence');
 }
 const records=p.valid_record_controls.map((x:any)=>x.record);
 if(profile==='native11'&&!records.includes("|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey"))fail('trace-controls');
 if(profile==='native11'&&!records.includes("|-heal|p1: First|50/100|[from] move: Revival Blessing"))fail('revival-controls');
 if(!records.includes(nativeNC)||(profile==='replay-compat-v1'&&!records.includes(oldNC)))fail('natural-cure-controls');
 for(const kind of ['malformed','unknown','unproved_semantic_family'])if(!p.rejection_fixtures.some((x:any)=>x.kind===kind))fail('negative-coverage');
}
/** Called with owned frozen data during bootstrap, or inspection data after fixed contexts validate. */
export function checkPreparedProtocolRecords(value:any,profile:PreparedProfile):void {
 assertPreparedRecordCheckInput(value,profile);
 const context=profile==='native11'?NATIVE11_GRAMMAR_CONTEXT:REPLAY_COMPAT_CONTEXT;
 for(const x of [...value.protocol.record_fixtures,...value.protocol.valid_record_controls]){
  try {
   if(profile==='native11'&&lifted.includes(x.token)) {
    // These are historical shape controls, not acceptance claims for changed IDs.
    validateRawProtocolRecord(x.record,HISTORICAL10_CONTEXT);
    try {validateRawProtocolRecord(x.record,context);} catch(e) {
     if((e as {code?:string}).code!=='simulator-coverage/v1/unclassified-effect-value'
       && !(x.token==='-swapsideconditions'&&(e as Error).message.includes('prepared-family-unsupported/court-change')))throw e;
    }
   } else validateRawProtocolRecord(x.record,context);
  } catch(e){fail('positive-rejected: '+x.token+' '+(e as Error).message);}
 }
 for(const x of value.protocol.rejection_fixtures){
  let error:Error|undefined;try{validateRawProtocolRecord(x.record,context);}catch(e){error=e as Error;}
  if(!error)fail('negative-accepted');
  const token=x.record.startsWith('|')?x.record.split('|')[1]:null;
  const declared=value.protocol.recognized_unsupported_commands.find((v:any)=>v.token===token)?.kind;
  const actual=error.message.includes('prepared-family-unsupported/')?'unproved_semantic_family'
   :error.message.startsWith('Malformed raw ')?'malformed'
   :error.message.startsWith('Unsupported raw protocol event:')?(declared||'unknown'):null;
  if(actual!==x.kind)fail('negative-reason');
 }
}
export function validatePreparedProtocolAsset(value:any,profile:PreparedProfile):any {
 assertPreparedInspectionAvailable();plain(value);const snapshot=JSON.parse(JSON.stringify(value));
 validatePreparedProtocolStructure(snapshot,profile);checkPreparedProtocolRecords(snapshot,profile);
 const freeze=(v:any):any=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};return freeze(snapshot);
}
