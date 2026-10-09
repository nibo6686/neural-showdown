import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import test from 'node:test';
import {projectObservableBattleState} from '../src/observable_state';
import {projectBeliefState} from '../src/belief_state';
import {continuePipelineEpisode, summarizeEpisodeBoundary, validatePipelineEpisodeFaithfulClaim, type PipelineEpisodeResult} from '../src/pipeline_episode';
import {createPipelineEpisodeEvidence, sealPipelineEpisodeEvidence, validatePipelineEpisodeEvidence, episodeEvidenceContentDigest} from '../src/pipeline_episode_evidence';
import {PLAYERS} from '../src/types';
import {PipelineIntegrationError} from '../src/pipeline_integration';
import {fixture, publish, defaults, session, savedEpisode, witness} from './pipeline_episode_saved_helpers';

// Saved source observations/references, with a contract-only terminal suffix.
// Existing accepted source wins/ties remain the mechanic witnesses; no battle runs here.
const segmentBytes=readFileSync(path.resolve(__dirname,'../../../artifacts/validation/faithful-flag-2026-10-09/segment-start.json'));
assert.equal(createHash('sha256').update(segmentBytes).digest('hex'),'a468592b1374317504445184242a8438112d381eb18e59931816c3d25b0127c5');
const segment=JSON.parse(segmentBytes.toString('utf8'));
function terminalFixture(winner: 'p1'|'tie', kind: 'fresh_episode'|'continuation_segment' = 'fresh_episode', bound = false) {
  const original=fixture(), before=bound ? original.next : original.initial;
  const raw=bound ? segment.commit.boundary : witness.commits[0].boundary;
  const reference=bound ? segment.commit.transition : original.reference;
  if(bound) assert.deepEqual(segment.origin.perspectives,Object.fromEntries(PLAYERS.map(p=>[p,before.perspectives[p].observation])));
  const actions=Object.fromEntries(PLAYERS.map(p=>{const r=before.perspectives[p].observation.request!;
    return [p,canonicalActionFromLegalAction(r,r.legal_actions.actions.find(a=>a?.choice.startsWith('switch '))!.index)];}));
  const next={...raw, battle_id:before.battle_id, schema_version:'pipeline-integration/v1',kind:'terminal',perspectives:{}} as any;
  const bundles={} as typeof original.bundles;
  for (const p of PLAYERS) {
    const old = raw.perspectives[p], view = structuredClone(old.view);
    view.terminated = true; view.winner = winner;
    view.self_team = before.perspectives[p].observation.view.self_team.map(prior => ({...view.self_team.find((row:any) => row.ident === prior.ident)!, slot:prior.slot}));
    view.active.self = view.self_team.findIndex((row:any) => row.active);
    const observation = projectObservableBattleState({schema_version: old.schema_version, source_kind: old.source_kind,
      battle_id: old.battle_id, perspective: p, snapshot_phase: 'terminal', request: null, view: {...view,env_id:'saved-flag-control'},
      protocol_prefix: [...old.protocol_prefix, winner === 'tie' ? '|tie' : `|win|${view.names.p1}`]});
    const previous=before.perspectives[p].belief;
    const metadata = {...reference, schema_version: 'seeded-transition/v1', root_seed: [31,37,41,43],
      action_ids: Object.fromEntries(PLAYERS.map(player=>[player,actions[player].action_id])),
      emitted_log_delta: observation.protocol_prefix.slice(before.perspectives[p].observation.protocol_prefix.length)} as any;
    const belief = projectBeliefState({observation, parent: previous, transition: {metadata,
      input_observation_id: before.perspectives[p].observation.observation_id, output_observation_id: observation.observation_id,
      output_snapshot: {schema_version:'seeded-transition/v1',format:'gen9randombattle',snapshot_handle:'sim-core://saved-terminal/fixture',
        root_seed:[31,37,41,43],state_fingerprint:reference.output_state_fingerprint,parent_branch_id:reference.parent_branch_id,
        branch_id:reference.branch_id,transition_id:reference.transition_id}}});
    next.perspectives[p] = {observation, belief};
    bundles[p]={...original.bundles[p],input_observation:before.perspectives[p].observation,input_belief:previous,action:actions[p],
      transition:{...reference,action_id:actions[p].action_id},successor_observation:observation,successor_belief:belief};
  }
  const f={initial:before,next,bundles,reference};
  const initial_boundary = summarizeEpisodeBoundary(before), limits = {...defaults};
  const policy = 'saved-first-switch/v1';
  const run_id = `episode-${createHash('sha256').update(JSON.stringify({schema:'pipeline-episode/v1',battle_id:before.battle_id,
    format:'gen9randombattle',policy,limits,initial_boundary})).digest('hex')}`;
  const predecessor = bound ? structuredClone(witness) : null;
  const envelope = createPipelineEpisodeEvidence({run_id,battle_id:before.battle_id,ruleset:'gen9randombattle',kind,
    boundaries:[before,next],transitions:[{actors:[...PLAYERS],transition:reference}],predecessor});
  const result: PipelineEpisodeResult = {schema_version:'pipeline-episode/v1',run_id,battle_id:before.battle_id,ruleset:'gen9randombattle',
    policy_id:policy,limits,status:'completed',stop:{code:'episode/v1/terminal',reason:'saved contract control'},
    counts:{attempts:1,committed_transitions:1,rejected_candidates:0,rejections_at_final_boundary:0},initial_boundary,
    final_boundary:summarizeEpisodeBoundary(next),transition_ids:[reference.transition_id],
    records:{p1:[bundles.p1],p2:[bundles.p2]},evidence_envelope:envelope,faithful_complete_episode:false};
  return {f,result,predecessor};
}

function rejected(result: PipelineEpisodeResult, pattern = /faithful/) {
  const before = structuredClone(result); assert.throws(() => validatePipelineEpisodeFaithfulClaim(result));
  publish(result, pattern); assert.deepEqual(result,before);
}
function compact(result: PipelineEpisodeResult) {
  const beliefs = new Map(); const records:any={p1:[],p2:[]};
  const arrayKeys=['observation_history','simulator_snapshot_history','transition_history','candidates','evidence','unresolved','contradictions'];
  for(const p of PLAYERS) for(const row of result.records[p]) {
    for(const belief of [row.input_belief,row.successor_belief]) {
      const {belief_id,source_protocol_prefix,...fields}=structuredClone(belief) as any; const arrays:any={};
      for(const key of arrayKeys){arrays[key]={mode:'full',items:fields[key]};delete fields[key];}
      beliefs.set(belief_id,{belief_id,base_belief_id:null,fields,arrays});
    }
    records[p].push({transition_id:row.transition.transition_id,action:row.action,input_belief_id:row.input_belief.belief_id,successor_belief_id:row.successor_belief.belief_id});
  }
  const {records:_r,evidence_envelope,...metadata}=result;
  return {schema_version:'pipeline-episode-publication-sweep/v1',result:metadata,evidence_envelope,records,beliefs:[...beliefs.values()]};
}

test('faithful claim saved win tie and bound continuation publish conservatively or true', async () => {
  for(const winner of ['p1','tie'] as const) for(const bound of [false,true]) {
    console.log(`faithful eligible ${winner}/bound=${bound}`);
    const {f,result,predecessor}=terminalFixture(winner,bound?'continuation_segment':'fresh_episode',bound), frozen=structuredClone(f);
    assert.equal(validatePipelineEpisodeFaithfulClaim(result),true); publish(result,undefined,2);
    result.faithful_complete_episode=true; assert.equal(validatePipelineEpisodeFaithfulClaim(result),true);
    publish(result,undefined,2); publish(compact(result),undefined,2);
    const control=session(f,'after-commit',new Error('must not reach second candidate'));
    // Continue from original owned requests: a validated root predecessor authorizes capture.
    const root=predecessor ?? createPipelineEpisodeEvidence({run_id:result.run_id,battle_id:result.battle_id,ruleset:result.ruleset,
      kind:'fresh_episode',boundaries:[f.initial],transitions:[]});
    const produced=await savedEpisode(control.owned,{predecessor_evidence:root});
    assert.equal(produced.faithful_complete_episode,true); assert.equal(control.closed(),1); publish(produced,undefined,2);
    assert.deepEqual(f,frozen);
    const failing=session(f,'after-commit',new Error('unused'),true);
    const failed=await savedEpisode(failing.owned,{predecessor_evidence:root});
    assert.equal(failed.evidence_envelope!.closure!.complete_capture,true); assert.equal(failed.faithful_complete_episode,false);
    publish(failed,undefined,2); const forged=structuredClone(failed);forged.faithful_complete_episode=true;rejected(forged);
  }
});

test('faithful claim ineligible stops segments terminal-only and schemas reject without mutation', async () => {
  const unbound=terminalFixture('p1','continuation_segment').result;
  assert.equal(validatePipelineEpisodeFaithfulClaim(unbound),false);publish(unbound,undefined,2);
  unbound.faithful_complete_episode=true; rejected(unbound);publish(compact(unbound),/faithful/);
  for (const budget of ['max_transitions','max_attempts','max_rejections_per_boundary'] as const) {
    const f=fixture(), controller=session(f,budget==='max_rejections_per_boundary'?'candidate':'after-commit',new PipelineIntegrationError('pipeline/v1/rejected-action','saved reject'));
    const partial=await savedEpisode(controller.owned,{limits:{[budget]:1}});
    assert.equal(partial.faithful_complete_episode,false);publish(partial,undefined,budget==='max_rejections_per_boundary'?0:2);
    partial.faithful_complete_episode=true;rejected(partial);
  }
  const revival=await savedEpisode(session(fixture(),'candidate',new Error('seeded-revival/v1/unsupported-request')).owned);
  assert.equal(revival.faithful_complete_episode,false);publish(revival);revival.faithful_complete_episode=true;rejected(revival);
  const exhausted=await savedEpisode(session(fixture(),'candidate',new PipelineIntegrationError('pipeline/v1/rejected-action','saved reject')).owned,
    {limits:{max_attempts:5000,max_rejections_per_boundary:5000}});
  assert.equal(exhausted.stop.code,'episode/v1/action-exhausted');assert.equal(exhausted.faithful_complete_episode,false);publish(exhausted);
  const f=fixture(), cancel=await savedEpisode(session(f,'selection',new Error('unused')).owned,{signal:AbortSignal.abort()});
  for(const [status,code] of [['truncated','cancelled'],['truncated','transition-budget'],['truncated','attempt-budget'],['truncated','rejection-limit'],
    ['truncated','unsupported-protocol'],['truncated','unsupported-boundary'],['truncated','unsupported-format'],['truncated','action-exhausted'],
    ['failed','execution-failed'],['failed','settling-failed'],['failed','cleanup-failed']] as const) {
    const candidate=structuredClone(cancel);candidate.status=status;candidate.stop.code=`episode/v1/${code}`;candidate.faithful_complete_episode=true;
    assert.throws(()=>validatePipelineEpisodeFaithfulClaim(candidate),/ineligible/);publish(candidate,/faithful|budget stop/);
  }
  const terminal=terminalFixture('tie'); const result=terminal.result;
  result.initial_boundary=result.final_boundary;result.counts={attempts:0,committed_transitions:0,rejected_candidates:0,rejections_at_final_boundary:0};
  result.transition_ids=[];result.records={p1:[],p2:[]};
  result.run_id=`episode-${createHash('sha256').update(JSON.stringify({schema:result.schema_version,battle_id:result.battle_id,format:result.ruleset,
    policy:result.policy_id,limits:result.limits,initial_boundary:result.initial_boundary})).digest('hex')}`;
  result.evidence_envelope=createPipelineEpisodeEvidence({run_id:result.run_id,battle_id:result.battle_id,ruleset:result.ruleset,
    kind:'fresh_episode',boundaries:[terminal.f.next],transitions:[]});
  publish(result);assert.equal(validatePipelineEpisodeFaithfulClaim(result),false);result.faithful_complete_episode=true;rejected(result);
  const missing=terminalFixture('p1').result;missing.faithful_complete_episode=true;missing.evidence_envelope=null;rejected(missing,/evidence envelope/);
  for(const flag of [null,1,'true']){const r=terminalFixture('p1').result;r.faithful_complete_episode=flag as any;rejected(r,/schema|flag/);}
  const legacy=terminalFixture('p1').result;legacy.evidence_envelope!.schema_version='pipeline-episode-evidence/v1';delete legacy.evidence_envelope!.closure;
  const {evidence_id:_legacy,...legacyContent}=legacy.evidence_envelope!;legacy.evidence_envelope=sealPipelineEpisodeEvidence(legacyContent);
  publish(legacy,undefined,2);assert.equal(validatePipelineEpisodeFaithfulClaim(legacy),false);legacy.faithful_complete_episode=true;rejected(legacy);
  const wrong=terminalFixture('p1').result;wrong.schema_version='pipeline-episode/v2' as any;wrong.faithful_complete_episode=true;rejected(wrong,/pipeline bundle fields are not exact/); // Unknown top-level schema is rejected by the existing CLI dispatcher.
  const privateResult=terminalFixture('p1').result;privateResult.faithful_complete_episode=true;(privateResult as any).root_seed=[1,2,3,4];rejected(privateResult,/pipeline episode result contains private or raw simulator data/);
});

test('faithful claim coherent origin and actor tampering reaches semantic validators', () => {
  const {f,result}=terminalFixture('tie');result.faithful_complete_episode=true;const committed=structuredClone(result);
  const changed=structuredClone(result);
  changed.evidence_envelope=createPipelineEpisodeEvidence({run_id:changed.run_id,battle_id:changed.battle_id,ruleset:changed.ruleset,
    kind:'continuation_segment',boundaries:[f.initial,f.next],transitions:[{actors:[...PLAYERS],transition:f.reference}]});
  // The canonical builder updates origin, commit references, closure and envelope together.
  validatePipelineEpisodeEvidence(changed.evidence_envelope,changed.records);rejected(changed);
  const forgedCoverage=structuredClone(changed);forgedCoverage.evidence_envelope!.closure!.origin_coverage='original_initial_requests';
  forgedCoverage.evidence_envelope!.closure!.complete_capture=true;
  const {evidence_id:_coverage,...coverageContent}=forgedCoverage.evidence_envelope!;forgedCoverage.evidence_envelope=sealPipelineEpisodeEvidence(coverageContent);
  assert.equal(forgedCoverage.evidence_envelope.evidence_id,`episode-evidence-${episodeEvidenceContentDigest(coverageContent)}`);
  assert.throws(()=>validatePipelineEpisodeFaithfulClaim(forgedCoverage),/evidence-origin-coverage/);
  publish(forgedCoverage,/origin coverage/);
  const omitted=structuredClone(result);omitted.records.p2=[];rejected(omitted,/record|actor/);
  const bad=structuredClone(result);bad.counts.attempts+=2;rejected(bad,/counter/);
  assert.deepEqual(result,committed);
});
