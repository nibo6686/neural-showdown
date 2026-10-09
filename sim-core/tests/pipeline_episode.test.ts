import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { isDeepStrictEqual } from 'node:util';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction, serializeCanonicalAction } from '../src/canonical_action';
import { serializeBeliefState, validateObservableBattleState } from '../src/belief_state';
import { LocalBattleEnv } from '../src/env_manager';
import { continuePipelineEpisode, runPipelineEpisode, summarizeEpisodeBoundary, type EpisodeRecord, type PipelineEpisodeResult } from '../src/pipeline_episode';
import {
  createPipelineEpisodeEvidence, sealPipelineEpisodeEvidence, validatePipelineEpisodeEvidence,
  type EpisodeEvidenceExpectation, type EpisodeEvidenceTransition, type PipelineEpisodeEvidence,
} from '../src/pipeline_episode_evidence';
import { createPipelineIntegrationSession, PipelineIntegrationError, validatePipelineLinkedRecordBundle, type PipelineBoundary } from '../src/pipeline_integration';
import { SettlingError } from '../src/settling';
import { PUBLIC_STAGES_SCHEMA_VERSION } from '../src/observable_state';
import { PLAYERS, type PlayerID } from '../src/types';
import { projectPublicTypedState } from '../src/typed_state_lifecycle';
import { wishBattle } from './wish_fixture';
import { healingWishBattle, futureSightBattle, revivalBattle } from './slot_consequence_fixtures';
import { opponentPublicBoosts } from '../src/public_boosts';
import { fingerprintSimulatorState } from '../src/transition';
import { rehash } from './public_consequence_test_helpers';

const CONFIG = { battle_id: 'episode-regression', format: 'gen9randombattle', seed: [101, 202, 303, 404] };

for (const scenario of [
  {label: 'plain Air Lock', seed: 16, ability: 'Air Lock', current: 'airlock', base: 'airlock', choice: 'move 2', partner: 'Pikachu\nLevel: 1\nAbility: Static\n- Splash'},
  {label: 'boost Intimidate', seed: 2, ability: 'Intimidate', current: 'intimidate', base: 'intimidate', choice: 'move 1', partner: 'Pikachu\nLevel: 1\nAbility: Static\n- Splash'},
  {label: 'Imposter cleanup', seed: 9, ability: 'Imposter', current: 'imposter', base: 'imposter', choice: 'move 1', partner: 'Pikachu\nLevel: 100\nEVs: 252 HP / 252 Atk\nAbility: Static\n- Explosion'},
  {label: 'Terapagos silent replacement', seed: 135, ability: 'Tera Shift', current: null, base: null, choice: 'move 2 terastallize', partner: 'Pikachu\nLevel: 1\nAbility: Static\n- Splash'},
  {label: 'Terapagos public replacement', seed: 135, ability: 'Tera Shift', current: 'teraformzero', base: 'teraformzero', choice: 'move 2 terastallize', partner: 'Torkoal\nLevel: 1\nAbility: Drought\n- Splash'},
  {label: 'Ogerpon public replacement', seed: 109, ability: 'Defiant', current: 'embodyaspectteal', base: 'embodyaspectteal', choice: 'move 2 terastallize', partner: 'Pikachu\nLevel: 1\nAbility: Static\n- Splash'},
]) for (const actor of PLAYERS) for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`C22 bounded ability ${scenario.label} ${actor} ${version}: joined requestless authority controls`, async () => {
    console.log(`Ability authority control: ${scenario.label}/${actor}/${version}`);
    const generated = Teams.generate('gen9randombattle', {seed: [scenario.seed, 2, 3, 4]}).find((set) => set.ability === scenario.ability)!;
    assert.ok(generated); assert.equal(generated.ability, scenario.ability);
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    const partner = Teams.import(scenario.partner)!;
    direct.setPlayer('p1', {name: 'One', team: actor === 'p1' ? [generated] : partner});
    direct.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? [generated] : partner});
    const snapshot = structuredClone(direct.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
    const reset = LocalBattleEnv.prototype.resetWithOptions, serialize = LocalBattleEnv.prototype.serializeBattle;
    let terminalSnapshot: Record<string, any> | undefined;
    let result: PipelineEpisodeResult;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
      LocalBattleEnv.prototype.serializeBattle = function () {const value = serialize.call(this); if (value.ended) terminalSnapshot = structuredClone(value); return value;};
      result = await runPipelineEpisode({battle_id: `ability-${scenario.label}-${actor}-${version}`, format: 'gen9randombattle', seed: [1,2,3,4],
        observation_schema_version: version, limits: {max_transitions: 1}, policy_id: 'trace-copy-control/v1',
        action_order(observation) {
          const request = observation.request!, choice = observation.perspective === actor ? scenario.choice : 'move 1';
          const preferred = request.legal_actions.actions.find((action) => action?.choice === choice)!;
          return [preferred.index, ...request.legal_actions.available_indices.filter((index) => index !== preferred.index)];
        }});
      const choices = actor === 'p1' ? [scenario.choice, 'move 1'] : ['move 1', scenario.choice];
      direct.makeChoices(...choices); restored.makeChoices(...choices);
      assert.equal(fingerprintSimulatorState(direct.toJSON()), fingerprintSimulatorState(restored.toJSON()));
    } finally {LocalBattleEnv.prototype.resetWithOptions = reset; LocalBattleEnv.prototype.serializeBattle = serialize; direct.destroy(); restored.destroy();}
    assert.equal(result.status, 'completed', JSON.stringify(result.stop));
    assert.equal(result.counts.committed_transitions, 1);
    const envelope = result.evidence_envelope!, other = actor === 'p1' ? 'p2' : 'p1';
    const terminal = result.records[actor][0].successor_observation;
    assert.equal(terminal.request, null);
    assert.equal(terminal.view.self_team[0].ability, scenario.current);
    assert.equal(terminal.view.self_team[0].base_ability, scenario.base);
    assert.equal(terminal.view.self_team[0].ability_state, scenario.current ? 'known' : 'unknown');
    if (scenario.ability === 'Imposter') {
      assert.ok(terminal.protocol_prefix.includes(`|-transform|${actor}a: Ditto|${other}a: Pikachu|[from] ability: Imposter`));
      assert.equal(result.records[actor][0].input_observation.view.self_team[0].ability, 'static');
      assert.equal(result.records[actor][0].input_observation.view.self_team[0].base_ability, 'imposter');
      assert.ok(terminal.view.self_team[0].fainted);
    }
    if (scenario.label.includes('replacement')) assert.ok(terminal.protocol_prefix.some((line) => line.startsWith(`|detailschange|${actor}a: `)));
    const terminalEnv = new LocalBattleEnv(`ability-terminal-restore-${actor}`, 'gen9randombattle', [1,2,3,4]);
    try {
      assert.equal(terminalSnapshot?.__neural_terminal_request_history.schema_version, 'terminal-request-history/v1');
      const restoredTerminal = await terminalEnv.resetFromSerialized(structuredClone(terminalSnapshot!));
      const restoredRow = restoredTerminal.views[actor]!.self_team[0];
      for (const field of ['ability', 'base_ability', 'ability_state', 'ability_suppressed', 'active', 'fainted'] as const) {
        assert.equal(restoredRow[field], terminal.view.self_team[0][field], `terminal private restoration ${field}`);
      }
    } finally {await terminalEnv.close();}
    const observer = result.records[other][0].successor_observation.view.opponent_team[0];
    for (const field of ['ability', 'base_ability', 'ability_state', 'ability_suppressed']) assert.ok(!(field in observer));
    const original = structuredClone(result);
    if (envelope) validatePipelineEpisodeEvidence(envelope, result.records, evidenceExpectation(result));
    else assert.equal(version, 'observable-battle-state/v1', 'full evidence envelope is a v2 boundary');
    for (const bundle of [...result.records.p1, ...result.records.p2]) {
      assert.ok(bundle.schema_version === 'pipeline-linked-record/v1'); validatePipelineLinkedRecordBundle(bundle);
    }
    for (const payload of envelope ? [result, envelope, ...result.records[actor]] : result.records[actor]) {
      const valid = pythonRun(payload); assert.equal(valid.status, 0, valid.stderr);
    }
    const mutations: Array<[string, PlayerID, (observation: any) => void, RegExp]> = [];
    for (const [field, value] of [['ability', result.records[actor][0].input_observation.view.self_team[0].ability !== scenario.current ? result.records[actor][0].input_observation.view.self_team[0].ability : 'static'], ['base_ability', result.records[actor][0].input_observation.view.self_team[0].base_ability !== scenario.base ? result.records[actor][0].input_observation.view.self_team[0].base_ability : 'levitate'], ['ability_state', 'none'], ['ability_state', null], ['ability_suppressed', null],
      ['ability_state', scenario.current ? 'unknown' : 'known'], ['ability_suppressed', true]] as const) {
      mutations.push([`false-${field}-${value}`, actor, (o) => {o.view.self_team[0][field] = value;}, /Public ability evidence mismatch/]);
    }
    if (scenario.current) for (const field of ['ability', 'base_ability']) {
      mutations.push([`null-${field}`, actor, (o) => {o.view.self_team[0][field] = null;}, /Public ability evidence mismatch/]);
    }
    for (const field of ['ability', 'base_ability', 'ability_state', 'ability_suppressed']) {
      mutations.push([`missing-${field}`, actor, (o) => {delete o.view.self_team[0][field];}, /Public ability evidence mismatch|requestless owned ability requires suppression/]);
    }
    for (const shape of ['row', 'team', 'wrong-side']) {
      mutations.push([shape, actor, (o) => {
        const row = o.view.self_team[0];
        if (shape === 'team') delete o.view.self_team;
        else {o.view.self_team = []; if (shape === 'wrong-side') o.view.opponent_team.push(row);}
      }, /Public health evidence mismatch|Public ability evidence mismatch/]);
    }
    for (const field of ['ability', 'ability_state']) {
      mutations.push([`excluded-opponent-${field}`, other, (o) => {o.view.opponent_team[0][field] = field === 'ability' ? 'static' : 'changed';},
        /opponent ability fields are excluded|Opponent contains fields outside public schema|opponent roster contains private or unexpected fields/]);
    }
    for (const [label, player, mutate, semantic] of mutations) {
      if (!envelope) {
        const candidate = structuredClone(result.records[player][0]);
        mutate(candidate.successor_observation); rehash(candidate);
        pythonCheckOriginRecordIdentity(candidate);
        const before = structuredClone(candidate);
        assert.ok(candidate.schema_version === 'pipeline-linked-record/v1');
        assert.throws(() => validatePipelineLinkedRecordBundle(candidate), semantic, label);
        const rejected = pythonRun(candidate); assert.equal(rejected.status, 2, `${label}: ${rejected.stderr}`);
        assert.equal(rejected.stdout, '', label); assert.match(rejected.stderr, semantic, label);
        assert.deepEqual(candidate, before, label);
        continue;
      }
      const candidate = withRehashedEpisodeObservations(result, player, (observation) => {
        if (observation.snapshot_phase === 'terminal') mutate(observation);
      });
      const actorRecords = [...candidate.records.p1, ...candidate.records.p2];
      pythonCheckOriginRecordIdentity(actorRecords);
      for (const bundle of actorRecords) {
        const retained = candidate.evidence_envelope!.commits[0].boundary.perspectives[bundle.perspective];
        assert.equal(bundle.successor_observation.observation_id, retained.observation_id);
        assert.equal(bundle.successor_belief.observation.observation_id, retained.observation_id);
      }
      const before = structuredClone(candidate);
      assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)), semantic, label);
      const ordinary = candidate.records[player][0];
      assert.ok(ordinary.schema_version === 'pipeline-linked-record/v1');
      assert.throws(() => validatePipelineLinkedRecordBundle(ordinary), semantic, label);
      for (const payload of [candidate, candidate.evidence_envelope, candidate.records[player][0]]) {
        const rejected = pythonRun(payload); assert.equal(rejected.status, 2, `${label}: ${rejected.stderr}`);
        assert.equal(rejected.stdout, '', label); assert.match(rejected.stderr, semantic, label);
      }
      assert.deepEqual(candidate, before, label);
    }
    assert.deepEqual(result, original);
    console.log(`Ability ${scenario.label}/${actor}/${version}: ${mutations.length} joined controls; ${envelope ? 'ordinary/full/envelope' : 'ordinary'} reject atomically`);
  });
}

for (const actor of PLAYERS) for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`C22 generated Trace ${actor} ${version}: joined requestless copy controls`, async () => {
    console.log(`Trace copied-ability control: ${actor}/${version}`);
    const generated = Teams.generate('gen9randombattle', {seed: [2, 2, 3, 4]})[2];
    assert.equal(generated.species, 'Gardevoir'); assert.equal(generated.ability, 'Trace');
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    const partner = Teams.import('Pikachu\nLevel: 1\nAbility: Static\n- Splash')!;
    direct.setPlayer('p1', {name: 'One', team: actor === 'p1' ? [generated] : partner});
    direct.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? [generated] : partner});
    const snapshot = structuredClone(direct.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    let result: PipelineEpisodeResult;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
      result = await runPipelineEpisode({battle_id: `trace-${actor}-${version}`, format: 'gen9randombattle', seed: [1,2,3,4],
        observation_schema_version: version, limits: {max_transitions: 1}, policy_id: 'trace-copy-control/v1',
        action_order(observation) {
          const request = observation.request!, choice = 'move 1';
          const preferred = request.legal_actions.actions.find((action) => action?.choice === choice)!;
          return [preferred.index, ...request.legal_actions.available_indices.filter((index) => index !== preferred.index)];
        }});
      direct.makeChoices('move 1', 'move 1'); restored.makeChoices('move 1', 'move 1');
      assert.equal(fingerprintSimulatorState(direct.toJSON()), fingerprintSimulatorState(restored.toJSON()));
    } finally {LocalBattleEnv.prototype.resetWithOptions = reset; direct.destroy(); restored.destroy();}
    assert.equal(result.status, 'completed', result.stop.reason);
    assert.equal(result.counts.committed_transitions, 1);
    const envelope = result.evidence_envelope!, other = actor === 'p1' ? 'p2' : 'p1';
    const copy = `|-ability|${actor}a: Gardevoir|Static|[from] ability: Trace|[of] ${other}a: Pikachu`;
    const terminal = result.records[actor][0].successor_observation;
    assert.ok(terminal.protocol_prefix.includes(copy)); assert.equal(terminal.request, null);
    assert.equal(terminal.view.self_team[0].ability, 'static'); assert.equal(terminal.view.self_team[0].ability_state, 'known');
    const observer = result.records[other][0].successor_observation.view.opponent_team[0];
    for (const field of ['ability', 'base_ability', 'ability_state', 'ability_suppressed']) assert.ok(!(field in observer));
    const original = structuredClone(result);
    if (envelope) validatePipelineEpisodeEvidence(envelope, result.records, evidenceExpectation(result));
    else assert.equal(version, 'observable-battle-state/v1', 'full evidence envelope is a v2 boundary');
    for (const bundle of [...result.records.p1, ...result.records.p2]) {
      assert.ok(bundle.schema_version === 'pipeline-linked-record/v1'); validatePipelineLinkedRecordBundle(bundle);
    }
    for (const payload of envelope ? [result, envelope, ...result.records[actor]] : result.records[actor]) {
      const valid = pythonRun(payload); assert.equal(valid.status, 0, valid.stderr);
    }
    const mutations: Array<[string, PlayerID, (observation: any) => void, RegExp]> = [];
    for (const [field, value] of [['ability', 'levitate'], ['ability', null], ['ability_state', 'unknown'],
      ['ability_state', 'none'], ['ability_suppressed', true]] as const) {
      mutations.push([`false-${field}-${value}`, actor, (o) => {o.view.self_team[0][field] = value;}, /Public ability evidence mismatch/]);
    }
    for (const field of ['ability', 'ability_state', 'ability_suppressed']) {
      mutations.push([`missing-${field}`, actor, (o) => {delete o.view.self_team[0][field];}, /Public ability evidence mismatch/]);
    }
    for (const shape of ['row', 'team', 'wrong-side']) {
      mutations.push([shape, actor, (o) => {
        const row = o.view.self_team[0];
        if (shape === 'team') delete o.view.self_team;
        else {o.view.self_team = []; if (shape === 'wrong-side') o.view.opponent_team.push(row);}
      }, /Public health evidence mismatch|Public ability evidence mismatch/]);
    }
    for (const field of ['ability', 'ability_state']) {
      mutations.push([`excluded-opponent-${field}`, other, (o) => {o.view.opponent_team[0][field] = field === 'ability' ? 'static' : 'changed';},
        /opponent (Trace|ability) fields are excluded|Opponent contains fields outside public schema|opponent roster contains private or unexpected fields/]);
    }
    for (const [label, player, mutate, semantic] of mutations) {
      if (!envelope) {
        const candidate = structuredClone(result.records[player][0]);
        mutate(candidate.successor_observation); rehash(candidate);
        pythonCheckOriginRecordIdentity(candidate);
        const before = structuredClone(candidate);
        assert.ok(candidate.schema_version === 'pipeline-linked-record/v1');
        assert.throws(() => validatePipelineLinkedRecordBundle(candidate), semantic, label);
        const rejected = pythonRun(candidate); assert.equal(rejected.status, 2, `${label}: ${rejected.stderr}`);
        assert.equal(rejected.stdout, '', label); assert.match(rejected.stderr, semantic, label);
        assert.deepEqual(candidate, before, label);
        continue;
      }
      const candidate = withRehashedEpisodeObservations(result, player, (observation) => {
        if (observation.snapshot_phase === 'terminal') mutate(observation);
      });
      const actorRecords = [...candidate.records.p1, ...candidate.records.p2];
      pythonCheckOriginRecordIdentity(actorRecords);
      for (const bundle of actorRecords) {
        const retained = candidate.evidence_envelope!.commits[0].boundary.perspectives[bundle.perspective];
        assert.equal(bundle.successor_observation.observation_id, retained.observation_id);
        assert.equal(bundle.successor_belief.observation.observation_id, retained.observation_id);
      }
      const before = structuredClone(candidate);
      assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)), semantic, label);
      const ordinary = candidate.records[player][0];
      assert.ok(ordinary.schema_version === 'pipeline-linked-record/v1');
      assert.throws(() => validatePipelineLinkedRecordBundle(ordinary), semantic, label);
      for (const payload of [candidate, candidate.evidence_envelope, candidate.records[player][0]]) {
        const rejected = pythonRun(payload); assert.equal(rejected.status, 2, `${label}: ${rejected.stderr}`);
        assert.equal(rejected.stdout, '', label); assert.match(rejected.stderr, semantic, label);
      }
      assert.deepEqual(candidate, before, label);
    }
    assert.deepEqual(result, original);
    console.log(`Trace ${actor}/${version}: ${mutations.length} joined controls; ${envelope ? 'ordinary/full/envelope' : 'ordinary'} reject atomically`);
  });
}
test('C22 generated Trace terminal faint cleanup publishes restored owner base and rejects stale copied name', async () => {
  for (const actor of PLAYERS) {
    console.log(`Trace terminal cleanup publication: ${actor}`);
    const generated = Teams.generate('gen9randombattle', {seed: [2,2,3,4]})[2];
    const partner = Teams.import('Pikachu\nLevel: 100\nEVs: 252 HP / 252 Atk\nAbility: Static\n- Explosion')!;
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    direct.setPlayer('p1', {name: 'One', team: actor === 'p1' ? [generated] : partner});
    direct.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? [generated] : partner});
    const snapshot = structuredClone(direct.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    let result: PipelineEpisodeResult;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
      result = await runPipelineEpisode({battle_id: `trace-terminal-faint-${actor}`, format: 'gen9randombattle', seed: [1,2,3,4],
        observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION, limits: {max_transitions: 1}, policy_id: 'trace-terminal-cleanup/v1',
        action_order(observation) {
          const request = observation.request!, choice = observation.perspective === actor ? 'move 3' : 'move 1';
          const preferred = request.legal_actions.actions.find((action) => action?.choice === choice)!;
          return [preferred.index, ...request.legal_actions.available_indices.filter((index) => index !== preferred.index)];
        }});
      const choices = actor === 'p1' ? ['move 3', 'move 1'] : ['move 1', 'move 3'];
      direct.makeChoices(...choices); restored.makeChoices(...choices);
      assert.equal(fingerprintSimulatorState(direct.toJSON()), fingerprintSimulatorState(restored.toJSON()));
      assert.equal(direct[actor].pokemon[0].ability, 'trace');
    } finally {LocalBattleEnv.prototype.resetWithOptions = reset; direct.destroy(); restored.destroy();}
    assert.equal(result.status, 'completed', result.stop.reason); assert.equal(result.counts.committed_transitions, 1);
    const own = result.records[actor][0].successor_observation;
    assert.equal(own.request, null); assert.equal(own.view.self_team[0].ability, 'trace');
    assert.equal(own.view.self_team[0].ability_state, 'known'); assert.ok(own.view.self_team[0].fainted);
    const original = structuredClone(result);
    validatePipelineEpisodeEvidence(result.evidence_envelope!, result.records, evidenceExpectation(result));
    for (const payload of [result, result.evidence_envelope, result.records[actor][0]]) {
      const valid = pythonRun(payload); assert.equal(valid.status, 0, valid.stderr);
    }
    const candidate = withRehashedEpisodeObservations(result, actor, (observation) => {
      if (observation.snapshot_phase === 'terminal') observation.view.self_team[0].ability = 'static';
    });
    pythonCheckOriginRecordIdentity([...candidate.records.p1, ...candidate.records.p2]);
    for (const player of PLAYERS) {
      assert.equal(candidate.records[player][0].successor_observation.observation_id,
        candidate.evidence_envelope!.commits[0].boundary.perspectives[player].observation_id);
    }
    const before = structuredClone(candidate), ordinary = candidate.records[actor][0];
    assert.ok(ordinary.schema_version === 'pipeline-linked-record/v1');
    assert.throws(() => validatePipelineLinkedRecordBundle(ordinary), /Public ability evidence mismatch/);
    assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)), /Public ability evidence mismatch/);
    for (const payload of [candidate, candidate.evidence_envelope, ordinary]) {
      const rejected = pythonRun(payload); assert.equal(rejected.status, 2, rejected.stderr);
      assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public ability evidence mismatch/);
    }
    assert.deepEqual(candidate, before); assert.deepEqual(result, original);
  }
});
type EpisodeBelief = PipelineEpisodeResult['records']['p1'][number]['input_belief'];
type BeliefHistoryField = 'observation_history' | 'simulator_snapshot_history' | 'transition_history'
  | 'candidates' | 'evidence' | 'unresolved' | 'contradictions';
type CompactBeliefDelta = {
  belief_id: string;
  base_belief_id: string | null;
  fields: Record<string, unknown>;
  arrays: Record<BeliefHistoryField, { mode: 'full' | 'append'; items: unknown[] }>;
};
const BELIEF_HISTORY_FIELDS: BeliefHistoryField[] = [
  'observation_history', 'simulator_snapshot_history', 'transition_history',
  'candidates', 'evidence', 'unresolved', 'contradictions',
];
function assertRecords(result: PipelineEpisodeResult) {
  assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
  assert.equal(result.transition_ids.length, result.counts.committed_transitions);
  assert.equal(new Set(result.transition_ids).size, result.transition_ids.length);
  const seen = new Set<string>();
  let parentBranch = result.initial_boundary?.branch_id;
  for (const id of result.transition_ids) {
    const bundles = PLAYERS.flatMap((p) => result.records[p].filter((r) => r.transition.transition_id === id));
    assert.ok(bundles.length === 1 || bundles.length === 2);
    for (const bundle of bundles) {
      assert.equal(bundle.transition.parent_branch_id, parentBranch);
      assert.equal(bundle.successor_belief.parent_belief_id, bundle.input_belief.belief_id);
      assert.equal(bundle.successor_belief.transition_lineage?.transition_id, id);
      assert.equal(bundle.successor_belief.observation.observation_id, bundle.successor_observation.observation_id);
      if (bundle.schema_version === 'pipeline-forced-switch-record/v1') {
        assert.equal(bundles.length, 1);
        assert.equal(bundle.transition.acting_player, bundle.perspective);
      }
    }
    parentBranch = bundles[0].transition.branch_id;
  }
  for (const player of PLAYERS) for (const bundle of result.records[player]) {
    assert.equal(bundle.perspective, player);
    assert.ok(result.transition_ids.includes(bundle.transition.transition_id));
    const key = `${player}:${bundle.transition.transition_id}`;
    assert.ok(!seen.has(key)); seen.add(key);
  }
  if (parentBranch) assert.equal(result.final_boundary?.branch_id, parentBranch);
}
function pythonValidate(bundle: unknown) {
  const processResult = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
  assert.equal(processResult.status, 0, processResult.stderr);
}
function pythonRun(value: unknown, timeout = 30_000) {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(value), encoding: 'utf8',
    maxBuffer: 256 * 1024 * 1024, timeout,
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
  if (result.error) result.stderr += `\n${result.error.message}; code=${(result.error as NodeJS.ErrnoException).code}; signal=${result.signal}`;
  return result;
}
function pythonPublicationSweep(result: PipelineEpisodeResult): {
  schema_version: string;
  result: Omit<PipelineEpisodeResult, 'records' | 'evidence_envelope'>;
  evidence_envelope: PipelineEpisodeEvidence;
  records: Record<PlayerID, Array<{
    transition_id: string;
    action: EpisodeRecord['action'];
    input_belief_id: string;
    successor_belief_id: string;
  }>>;
  beliefs: CompactBeliefDelta[];
} {
  assert.ok(result.evidence_envelope);
  const beliefs = new Map<string, EpisodeBelief>();
  const records: Record<PlayerID, Array<{
    transition_id: string;
    action: EpisodeRecord['action'];
    input_belief_id: string;
    successor_belief_id: string;
  }>> = { p1: [], p2: [] };
  for (const player of PLAYERS) for (const bundle of result.records[player]) {
    for (const belief of [bundle.input_belief, bundle.successor_belief]) {
      const prior = beliefs.get(belief.belief_id);
      if (prior) assert.deepEqual(prior, belief, `belief ${belief.belief_id} has one immutable content identity`);
      else beliefs.set(belief.belief_id, belief);
    }
    records[player].push({
      transition_id: bundle.transition.transition_id,
      action: structuredClone(bundle.action),
      input_belief_id: bundle.input_belief.belief_id,
      successor_belief_id: bundle.successor_belief.belief_id,
    });
  }
  const compactBeliefs: CompactBeliefDelta[] = [...beliefs.values()].map((belief) => {
    const parent = belief.parent_belief_id === null ? undefined : beliefs.get(belief.parent_belief_id);
    const arrays = {} as CompactBeliefDelta['arrays'];
    let hasBase = false;
    for (const field of BELIEF_HISTORY_FIELDS) {
      const current = belief[field] as unknown[];
      const previous = parent?.[field] as unknown[] | undefined;
      const canAppend = Boolean(previous)
        && previous!.length <= current.length
        && previous!.every((item, index) => isDeepStrictEqual(item, current[index]));
      arrays[field] = canAppend
        ? { mode: 'append', items: current.slice(previous!.length) }
        : { mode: 'full', items: current };
      hasBase ||= canAppend;
    }
    const fields = { ...belief } as unknown as Record<string, unknown>;
    delete fields.belief_id;
    delete fields.source_protocol_prefix;
    for (const field of BELIEF_HISTORY_FIELDS) delete fields[field];
    return {
      belief_id: belief.belief_id,
      base_belief_id: hasBase && parent ? parent.belief_id : null,
      fields,
      arrays,
    };
  });
  return {
    schema_version: 'pipeline-episode-publication-sweep/v1',
    result: {
      schema_version: result.schema_version,
      run_id: result.run_id,
      battle_id: result.battle_id,
      ruleset: result.ruleset,
      policy_id: result.policy_id,
      limits: structuredClone(result.limits),
      status: result.status,
      stop: structuredClone(result.stop),
      counts: structuredClone(result.counts),
      initial_boundary: structuredClone(result.initial_boundary),
      final_boundary: structuredClone(result.final_boundary),
      transition_ids: [...result.transition_ids],
      faithful_complete_episode: result.faithful_complete_episode,
    },
    evidence_envelope: structuredClone(result.evidence_envelope),
    records,
    beliefs: compactBeliefs,
  };
}
function pythonPublishBundles(bundles: EpisodeRecord[]) {
  let published = 0;
  for (let offset = 0; offset < bundles.length; offset += 8) {
    const batch = bundles.slice(offset, offset + 8);
    const response = spawnSync(process.env.PYTHON || 'python3', ['-c', `import io,json,sys
from unittest.mock import patch
from neural.pipeline_record import main
items=json.load(sys.stdin)
for bundle in items:
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(bundle))),patch('sys.stdout',out),patch('sys.stderr',err): result=main()
 assert result == 0 and out.getvalue(), (result,err.getvalue())
 row=json.loads(out.getvalue())
 assert row['transition_id'] == bundle['transition']['transition_id']
 assert row['perspective'] == bundle['perspective']
print(len(items))`], {
      input: JSON.stringify(batch), encoding: 'utf8',
      env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
    });
    assert.equal(response.status, 0, response.stderr);
    assert.equal(response.stdout.trim(), String(batch.length), response.stderr);
    published += batch.length;
  }
  return published;
}
function reseal(value: PipelineEpisodeEvidence): PipelineEpisodeEvidence {
  const { evidence_id: _evidenceId, ...partial } = structuredClone(value);
  return sealPipelineEpisodeEvidence(partial);
}
function reorigin(value: PipelineEpisodeEvidence): PipelineEpisodeEvidence {
  const identity = {
    schema_version: value.origin.schema_version,
    run_id: value.run_id,
    battle_id: value.battle_id,
    ruleset: value.ruleset,
    source_ref: value.source_ref,
    kind: value.origin.kind,
    boundary: value.origin.boundary,
  };
  value.origin.origin_id = `episode-origin-${createHash('sha256').update(evidenceCanonical(identity), 'utf8').digest('hex')}`;
  for (const commit of value.commits) commit.origin_id = value.origin.origin_id;
  return reseal(value);
}
function evidenceCanonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(evidenceCanonical).join(',')}]`;
  if (value && typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${evidenceCanonical(object[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}
function refreshObservationIdentity(observation: PipelineEpisodeEvidence['origin']['boundary']['perspectives']['p1']) {
  observation.protocol_prefix_hash = createHash('sha256').update(evidenceCanonical(observation.protocol_prefix)).digest('hex');
  const { observation_id: _observationId, protocol_prefix: _prefix, ...identity } = observation;
  observation.observation_id = `obs-${createHash('sha256').update(evidenceCanonical(identity)).digest('hex')}`;
}
function withRehashedOriginVolatileRow(result: PipelineEpisodeResult, omitRow: boolean): PipelineEpisodeResult {
  const origin = result.evidence_envelope!.origin.boundary.perspectives.p1;
  const originRoster = origin.view.self_team;
  const active = originRoster.find((pokemon) => pokemon.active);
  assert.ok(active);
  const sourceLine = `|-start|${active.ident.replace(/^(p[12]): /, '$1a: ')}|Substitute`;
  const insertionIndex = origin.protocol_prefix.length;
  return withRehashedEpisodeObservations(result, 'p1', (updated) => {
    updated.protocol_prefix.splice(Math.min(insertionIndex, updated.protocol_prefix.length), 0, sourceLine);
    updated.event_cursor = updated.protocol_prefix.length;
    updated.protocol_prefix_hash = createHash('sha256').update(evidenceCanonical(updated.protocol_prefix), 'utf8').digest('hex');
    const state = projectPublicTypedState(updated.protocol_prefix).volatiles_by_ident;
    for (const pokemon of updated.view.self_team) {
      pokemon.volatiles = pokemon.volatiles.filter((value) => value !== 'substitute');
      if (state[pokemon.ident]?.includes('substitute')) pokemon.volatiles.push('substitute');
    }
    for (const pokemon of updated.view.opponent_team) {
      pokemon.volatiles = pokemon.volatiles.filter((value) => value !== 'substitute');
      if (state[pokemon.ident]?.includes('substitute')) pokemon.volatiles.push('substitute');
    }
    if (omitRow && updated.observation_id === origin.observation_id) {
      updated.view.self_team = updated.view.self_team.filter((pokemon) => pokemon.ident !== active.ident);
    }
  });
}
function withRehashedEpisodeObservations(result: PipelineEpisodeResult, player: PlayerID,
  mutation: (observation: PipelineEpisodeEvidence['origin']['boundary']['perspectives']['p1']) => void,
  boundaryBeliefs: EpisodeBelief[] = [], validateBeliefPrefix = true): PipelineEpisodeResult {
  const tampered = structuredClone(result);
  assert.ok(tampered.evidence_envelope && tampered.initial_boundary && tampered.final_boundary);
  const envelope = tampered.evidence_envelope;
  const origin = envelope.origin.boundary.perspectives[player];
  const priorToObservation = new Map<string, PipelineEpisodeEvidence['origin']['boundary']['perspectives']['p1']>();
  const rememberObservation = (observation: PipelineEpisodeEvidence['origin']['boundary']['perspectives']['p1']) => {
    if (priorToObservation.has(observation.observation_id)) return;
    const updated = structuredClone(observation);
    mutation(updated);
    refreshObservationIdentity(updated);
    priorToObservation.set(observation.observation_id, updated);
  };
  rememberObservation(origin);
  for (const commit of envelope.commits) rememberObservation(commit.boundary.perspectives[player]);
  for (const record of tampered.records[player]) {
    rememberObservation(record.input_observation);
    rememberObservation(record.successor_observation);
  }
  const updatedOrigin = priorToObservation.get(origin.observation_id)!;
  const updatedReference = (reference: Record<string, any>) => {
    const updated = priorToObservation.get(reference.observation_id);
    if (updated) Object.assign(reference, observationReference(updated));
  };
  envelope.origin.boundary.perspectives[player] = updatedOrigin;
  for (const commit of envelope.commits) commit.boundary.perspectives[player] = priorToObservation.get(commit.boundary.perspectives[player].observation_id)!;
  for (const record of tampered.records[player]) {
    record.input_observation = priorToObservation.get(record.input_observation.observation_id)!;
    record.successor_observation = priorToObservation.get(record.successor_observation.observation_id)!;
  }
  tampered.initial_boundary.perspectives[player].observation_id = updatedOrigin.observation_id;
  tampered.initial_boundary.perspectives[player].event_cursor = updatedOrigin.event_cursor;
  const finalObservation = priorToObservation.get(tampered.final_boundary.perspectives[player].observation_id)!;
  tampered.final_boundary.perspectives[player].observation_id = finalObservation.observation_id;
  tampered.final_boundary.perspectives[player].event_cursor = finalObservation.event_cursor;

  const beliefsByPriorId = new Map<string, EpisodeBelief>();
  for (const record of tampered.records[player]) for (const belief of [record.input_belief, record.successor_belief]) {
    if (!beliefsByPriorId.has(belief.belief_id)) beliefsByPriorId.set(belief.belief_id, structuredClone(belief));
  }
  for (const belief of boundaryBeliefs.filter((entry) => entry.perspective === player)) {
    if (!beliefsByPriorId.has(belief.belief_id)) beliefsByPriorId.set(belief.belief_id, structuredClone(belief));
  }
  for (const belief of beliefsByPriorId.values()) {
    const updatedObservation = priorToObservation.get(belief.observation.observation_id);
    if (updatedObservation) belief.source_protocol_prefix = [...updatedObservation.protocol_prefix];
    updatedReference(belief.observation);
    belief.observation_history = belief.observation_history.map((reference) => {
      const copy = { ...reference };
      updatedReference(copy);
      return copy;
    });
    for (const entry of [...belief.transition_history, ...(belief.transition_lineage ? [belief.transition_lineage] : [])]) {
      const input = priorToObservation.get(entry.input_observation_id);
      const output = priorToObservation.get(entry.output_observation_id);
      if (input) entry.input_observation_id = input.observation_id;
      if (output) entry.output_observation_id = output.observation_id;
    }
  }
  const updatedBeliefs = new Map<string, EpisodeBelief>();
  const rehashBeliefByPriorId = (priorId: string, visiting = new Set<string>()): EpisodeBelief => {
    const cached = updatedBeliefs.get(priorId);
    if (cached) return cached;
    const prior = beliefsByPriorId.get(priorId);
    assert.ok(prior && !visiting.has(priorId));
    const belief = structuredClone(prior);
    if (belief.parent_belief_id) belief.parent_belief_id = rehashBeliefByPriorId(belief.parent_belief_id, visiting).belief_id;
    const updated = rehashBelief(belief, validateBeliefPrefix);
    updatedBeliefs.set(priorId, updated);
    return updated;
  };
  for (const priorId of beliefsByPriorId.keys()) rehashBeliefByPriorId(priorId);
  for (const record of tampered.records[player]) {
    record.input_belief = structuredClone(updatedBeliefs.get(record.input_belief.belief_id)!);
    record.successor_belief = structuredClone(updatedBeliefs.get(record.successor_belief.belief_id)!);
  }
  tampered.initial_boundary.perspectives[player].belief_id = updatedBeliefs.get(tampered.initial_boundary.perspectives[player].belief_id)!.belief_id;
  tampered.final_boundary.perspectives[player].belief_id = updatedBeliefs.get(tampered.final_boundary.perspectives[player].belief_id)!.belief_id;
  const runIdentity = {
    schema: 'pipeline-episode/v1', battle_id: tampered.battle_id, format: tampered.ruleset,
    policy: tampered.policy_id, limits: tampered.limits, initial_boundary: tampered.initial_boundary,
  };
  tampered.run_id = `episode-${createHash('sha256').update(JSON.stringify(runIdentity)).digest('hex')}`;
  envelope.run_id = tampered.run_id;
  if (envelope.closure?.terminal) {
    envelope.closure.terminal.final_boundary.perspectives[player] = {
      observation_id: finalObservation.observation_id, event_cursor: finalObservation.event_cursor,
      protocol_prefix_hash: finalObservation.protocol_prefix_hash,
    };
  }
  const originIdentity = {
    schema_version: envelope.origin.schema_version, run_id: envelope.run_id,
    battle_id: envelope.battle_id, ruleset: envelope.ruleset, source_ref: envelope.source_ref,
    kind: envelope.origin.kind, boundary: envelope.origin.boundary,
  };
  envelope.origin.origin_id = `episode-origin-${createHash('sha256').update(evidenceCanonical(originIdentity), 'utf8').digest('hex')}`;
  for (const commit of envelope.commits) commit.origin_id = envelope.origin.origin_id;
  tampered.evidence_envelope = reseal(envelope);
  return tampered;
}
function observationReference(observation: PipelineEpisodeEvidence['origin']['boundary']['perspectives']['p1']) {
  const { schema_version, observation_id, source_kind, event_cursor, protocol_prefix_hash, snapshot_phase } = observation;
  return { schema_version, observation_id, source_kind, event_cursor, protocol_prefix_hash, snapshot_phase };
}
function rehashBelief(belief: EpisodeBelief, validatePrefix = true) {
  const { belief_id: _priorBeliefId, ...beliefPayload } = belief;
  belief.belief_id = `belief-${createHash('sha256').update(evidenceCanonical(beliefPayload), 'utf8').digest('hex')}`;
  if (validatePrefix) serializeBeliefState(belief);
  return belief;
}
function assertRehashedForeignOriginJoins(result: PipelineEpisodeResult) {
  const envelope = result.evidence_envelope!;
  const originObservation = envelope.origin.boundary.perspectives.p1;
  assert.equal(originObservation.perspective, 'p1');
  assert.equal(originObservation.request?.player, 'p2', 'the sole intended inconsistency is request ownership');
  assert.equal(result.initial_boundary!.perspectives.p1.observation_id, originObservation.observation_id);

  const expectedRecordIds = envelope.commits.flatMap((commit) => commit.actors.includes('p1')
    ? [commit.transition.transition_id] : []);
  assert.deepEqual(result.records.p1.map((record) => record.transition.transition_id), expectedRecordIds);
  let previous = envelope.origin.boundary;
  let p1RecordIndex = 0;
  for (const commit of envelope.commits) {
    if (commit.actors.includes('p1')) {
      const record = result.records.p1[p1RecordIndex++];
      assert.ok(record);
      assert.deepEqual(record.input_observation, previous.perspectives.p1, 'p1 record input must join its origin/preceding boundary');
      assert.deepEqual(record.successor_observation, commit.boundary.perspectives.p1, 'p1 record successor must join its committed boundary');
      assert.deepEqual(record.input_belief.observation, observationReference(record.input_observation));
      assert.deepEqual(record.successor_belief.observation, observationReference(record.successor_observation));
      assert.equal(record.successor_belief.parent_belief_id, record.input_belief.belief_id);
      serializeBeliefState(record.input_belief);
      serializeBeliefState(record.successor_belief);
      assert.deepEqual({
        schema_version: record.transition.schema_version,
        transition_id: record.transition.transition_id,
        parent_branch_id: record.transition.parent_branch_id,
        branch_id: record.transition.branch_id,
        input_state_fingerprint: record.transition.input_state_fingerprint,
        output_state_fingerprint: record.transition.output_state_fingerprint,
        simulator_revision: record.transition.simulator_revision,
        step_index: record.transition.step_index,
      }, commit.transition, 'record transition identity remains joined to its evidence commit');
      assert.deepEqual(record.successor_belief.transition_lineage, {
        transition_id: record.transition.transition_id,
        parent_branch_id: record.transition.parent_branch_id,
        branch_id: record.transition.branch_id,
        input_state_fingerprint: record.transition.input_state_fingerprint,
        output_state_fingerprint: record.transition.output_state_fingerprint,
        simulator_revision: record.transition.simulator_revision,
        step_index: record.transition.step_index,
        input_observation_id: record.input_observation.observation_id,
        output_observation_id: record.successor_observation.observation_id,
      });
    }
    previous = commit.boundary;
  }
  assert.equal(p1RecordIndex, result.records.p1.length);
  assert.equal(result.initial_boundary!.perspectives.p1.belief_id, result.records.p1[0].input_belief.belief_id);
  const finalP1Belief = result.records.p1.flatMap((record) => [record.input_belief, record.successor_belief])
    .find((belief) => belief.observation.observation_id === result.final_boundary!.perspectives.p1.observation_id);
  assert.ok(finalP1Belief, 'final p1 boundary belief must be represented in actor evidence');
  assert.equal(result.final_boundary!.perspectives.p1.belief_id, finalP1Belief.belief_id);
}
function pythonCheckOriginRecordIdentity(record: PipelineEpisodeResult['records']['p1'][number] | PipelineEpisodeResult['records']['p1'], prefixContradiction = false) {
  const code = [
    'import json, sys',
    'from neural.ts_identity import verify_bundle_identities, verify_observation, belief_digest',
    'for bundle in json.load(sys.stdin):',
    ...(prefixContradiction ? [
      '    for which in ("input", "successor"):',
      '        observation, belief = bundle[which + "_observation"], bundle[which + "_belief"]',
      '        verify_observation(observation, which)',
      '        assert belief["belief_id"] == belief_digest(belief)',
    ] : ['    verify_bundle_identities(bundle)']),
  ].join('\n');
  const processResult = spawnSync(process.env.PYTHON || 'python3', ['-c', code], {
    input: JSON.stringify(Array.isArray(record) ? record : [record]), encoding: 'utf8', timeout: 30_000,
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
  assert.equal(processResult.status, 0, processResult.stderr);
  assert.equal(processResult.stdout, '');
}
function recordsForEvidence(result: PipelineEpisodeResult, envelope: PipelineEpisodeEvidence) {
  const ids = new Set(envelope.commits.map((commit) => commit.transition.transition_id));
  return {
    p1: result.records.p1.filter((record) => ids.has(record.transition.transition_id)),
    p2: result.records.p2.filter((record) => ids.has(record.transition.transition_id)),
  };
}
function evidenceActorsAt(boundary: PipelineEpisodeEvidence['origin']['boundary']): PlayerID[] {
  const state = (player: PlayerID) => {
    const observation = boundary.perspectives[player];
    if (observation.view.terminated) return 'terminal';
    if (!observation.request) return 'requestless';
    if (observation.request.wait) return 'waiting';
    if (observation.request.side.some((pokemon) => pokemon.reviving)) return 'revival_selection';
    if (!observation.decision_availability.available || !observation.request.legal_actions.available_indices.length) return 'no_legal_actions';
    return observation.request.force_switch ? 'forced_switch' : 'actionable';
  };
  const states = { p1: state('p1'), p2: state('p2') };
  if (['actionable', 'forced_switch'].includes(states.p1) && ['actionable', 'forced_switch'].includes(states.p2)) return ['p1', 'p2'];
  if (states.p1 === 'revival_selection' && states.p2 === 'waiting') return ['p1'];
  if (states.p2 === 'revival_selection' && states.p1 === 'waiting') return ['p2'];
  if (states.p1 === 'forced_switch' && states.p2 === 'waiting') return ['p1'];
  if (states.p2 === 'forced_switch' && states.p1 === 'waiting') return ['p2'];
  return [];
}
function evidenceExpectation(result: PipelineEpisodeResult): EpisodeEvidenceExpectation {
  assert.ok(result.evidence_envelope);
  return {
    run_id: result.run_id, battle_id: result.battle_id, ruleset: result.ruleset,
    policy_id: result.policy_id, limits: result.limits,
    origin_kind: result.evidence_envelope.origin.kind, initial_boundary: result.initial_boundary,
  } as EpisodeEvidenceExpectation;
}
function withRehashedForeignOriginRequest(result: PipelineEpisodeResult): PipelineEpisodeResult {
  const tampered = structuredClone(result);
  assert.ok(tampered.evidence_envelope && tampered.initial_boundary);
  const envelope = tampered.evidence_envelope;
  const p1 = envelope.origin.boundary.perspectives.p1;
  const priorObservationId = p1.observation_id;
  const p2Request = envelope.origin.boundary.perspectives.p2.request;
  assert.ok(p1.request && p2Request);
  p1.request = structuredClone(p2Request);
  refreshObservationIdentity(p1);
  tampered.initial_boundary.perspectives.p1.observation_id = p1.observation_id;

  const updatedObservationReference = {
    schema_version: p1.schema_version,
    observation_id: p1.observation_id,
    source_kind: p1.source_kind,
    event_cursor: p1.event_cursor,
    protocol_prefix_hash: p1.protocol_prefix_hash,
    snapshot_phase: p1.snapshot_phase,
  };

  const beliefsByPriorId = new Map<string, EpisodeBelief>();
  for (const record of tampered.records.p1) {
    for (const belief of [record.input_belief, record.successor_belief]) {
      const prior = beliefsByPriorId.get(belief.belief_id);
      if (prior) assert.equal(evidenceCanonical(prior), evidenceCanonical(belief), 'repeated p1 belief identity must have identical content');
      else beliefsByPriorId.set(belief.belief_id, structuredClone(belief));
    }
  }
  assert.ok(beliefsByPriorId.has(tampered.initial_boundary.perspectives.p1.belief_id));
  for (const belief of beliefsByPriorId.values()) {
    assert.equal(belief.evidence.length, 0, 'this accepted fixture has no evidence payloads to rebind');
    if (belief.observation.observation_id === priorObservationId) belief.observation = updatedObservationReference;
    belief.observation_history = belief.observation_history.map((reference) =>
      reference.observation_id === priorObservationId ? updatedObservationReference : reference);
    for (const entry of [...belief.transition_history, ...(belief.transition_lineage ? [belief.transition_lineage] : [])]) {
      if (entry.input_observation_id === priorObservationId) entry.input_observation_id = p1.observation_id;
      if (entry.output_observation_id === priorObservationId) entry.output_observation_id = p1.observation_id;
    }
  }

  const priorToUpdatedBeliefId = new Map<string, string>();
  const updatedBeliefsByPriorId = new Map<string, EpisodeBelief>();
  const rehashPriorBelief = (priorId: string, visiting = new Set<string>()) => {
    const cached = updatedBeliefsByPriorId.get(priorId);
    if (cached) return cached;
    assert.ok(!visiting.has(priorId), `p1 belief parent cycle at ${priorId}`);
    const prior = beliefsByPriorId.get(priorId);
    assert.ok(prior, `p1 belief parent ${priorId} must be represented in actor evidence`);
    visiting.add(priorId);
    const updated = structuredClone(prior);
    if (updated.parent_belief_id !== null) {
      updated.parent_belief_id = rehashPriorBelief(updated.parent_belief_id, visiting).belief_id;
    }
    visiting.delete(priorId);
    const rehashed = rehashBelief(updated);
    priorToUpdatedBeliefId.set(priorId, rehashed.belief_id);
    updatedBeliefsByPriorId.set(priorId, rehashed);
    return rehashed;
  };
  for (const priorId of beliefsByPriorId.keys()) rehashPriorBelief(priorId);

  for (const record of tampered.records.p1) {
    if (record.input_observation.observation_id === priorObservationId) record.input_observation = structuredClone(p1);
    if (record.successor_observation.observation_id === priorObservationId) record.successor_observation = structuredClone(p1);
    record.input_belief = structuredClone(updatedBeliefsByPriorId.get(record.input_belief.belief_id)!);
    record.successor_belief = structuredClone(updatedBeliefsByPriorId.get(record.successor_belief.belief_id)!);
  }
  tampered.initial_boundary.perspectives.p1.belief_id = priorToUpdatedBeliefId.get(tampered.initial_boundary.perspectives.p1.belief_id)!;
  tampered.final_boundary!.perspectives.p1.belief_id = priorToUpdatedBeliefId.get(tampered.final_boundary!.perspectives.p1.belief_id)!;

  const runIdentity = {
    schema: 'pipeline-episode/v1', battle_id: tampered.battle_id, format: tampered.ruleset,
    policy: tampered.policy_id, limits: tampered.limits, initial_boundary: tampered.initial_boundary,
  };
  tampered.run_id = `episode-${createHash('sha256').update(JSON.stringify(runIdentity)).digest('hex')}`;
  envelope.run_id = tampered.run_id;
  const originIdentity = {
    schema_version: envelope.origin.schema_version,
    run_id: envelope.run_id,
    battle_id: envelope.battle_id,
    ruleset: envelope.ruleset,
    source_ref: envelope.source_ref,
    kind: envelope.origin.kind,
    boundary: envelope.origin.boundary,
  };
  envelope.origin.origin_id = `episode-origin-${createHash('sha256').update(evidenceCanonical(originIdentity)).digest('hex')}`;
  for (const commit of envelope.commits) commit.origin_id = envelope.origin.origin_id;
  tampered.evidence_envelope = reseal(envelope);
  assertRehashedForeignOriginJoins(tampered);
  pythonCheckOriginRecordIdentity(tampered.records.p1[0]);
  return tampered;
}
function assertTamperRejected(result: PipelineEpisodeResult, candidate: PipelineEpisodeEvidence, label: string, errorPattern?: RegExp, pythonErrorPattern = errorPattern) {
  const candidateBefore = structuredClone(candidate);
  const recordsBefore = structuredClone(result.records);
  const envelopeBefore = JSON.stringify(result.evidence_envelope);
  if (errorPattern) {
    assert.throws(() => validatePipelineEpisodeEvidence(candidate, recordsForEvidence(result, candidate), evidenceExpectation(result)), errorPattern, label);
  } else {
    assert.throws(() => validatePipelineEpisodeEvidence(candidate, recordsForEvidence(result, candidate), evidenceExpectation(result)),
      (error: unknown) => error instanceof Error, label);
  }
  assert.deepEqual(result.records, recordsBefore, `${label}: rejected validation must preserve committed actor rows`);
  assert.equal(JSON.stringify(result.evidence_envelope), envelopeBefore, `${label}: rejected validation must preserve committed evidence`);
  assert.deepEqual(candidate, candidateBefore, `${label}: rejected validation must preserve the candidate`);
  const invalid = structuredClone(result);
  invalid.evidence_envelope = candidate;
  const response = pythonRun(invalid);
  assert.equal(response.status, 2, `${label}: ${response.stderr}`);
  assert.equal(response.stdout, '', `${label}: invalid full result must not emit DATA-001 rows`);
  if (pythonErrorPattern) assert.match(response.stderr, pythonErrorPattern);
  assert.deepEqual(candidate, candidateBefore, `${label}: Python publication must preserve the candidate`);
}
function assertFullResultTamperRejected(result: PipelineEpisodeResult, candidate: PipelineEpisodeEvidence, label: string, errorPattern?: RegExp, pythonErrorPattern = errorPattern) {
  const resultBefore = structuredClone(result);
  const candidateBefore = structuredClone(candidate);
  if (errorPattern) assert.throws(() => validatePipelineEpisodeEvidence(candidate, result.records, evidenceExpectation(result)), errorPattern);
  else assert.throws(() => validatePipelineEpisodeEvidence(candidate, result.records, evidenceExpectation(result)));
  assert.deepEqual(candidate, candidateBefore, `${label}: validator must not mutate the candidate`);
  assert.deepEqual(result, resultBefore, `${label}: rejected candidate must preserve the committed result`);
  const invalid = structuredClone(result);
  invalid.evidence_envelope = candidate;
  const response = pythonRun(invalid);
  assert.equal(response.status, 2, `${label}: ${response.stderr}`);
  assert.equal(response.stdout, '', `${label}: invalid full result must not publish DATA-001 rows`);
  if (pythonErrorPattern) assert.match(response.stderr, pythonErrorPattern);
}

async function advanceSessionFromEpisode(session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>, result: PipelineEpisodeResult, count: number) {
  assert.ok(result.evidence_envelope);
  const boundaries: PipelineBoundary[] = [session.boundary];
  const transitions: Array<{ transition: EpisodeEvidenceTransition; actors: PlayerID[] }> = [];
  for (const commit of result.evidence_envelope.commits.slice(0, count)) {
    const bundles = Object.fromEntries(commit.actors.map((player) => {
      const record = result.records[player].find((item) => item.transition.transition_id === commit.transition.transition_id)!;
      return [player, record];
    })) as Partial<Record<PlayerID, EpisodeRecord>>;
    let committed: { boundary: PipelineBoundary; record_bundles: Partial<Record<PlayerID, EpisodeRecord>> };
    if (commit.actors.length === 2) {
      committed = await session.step({
        p1: bundles.p1!.action,
        p2: bundles.p2!.action,
      });
    } else {
      const actor = commit.actors[0];
      const record = bundles[actor]!;
      committed = commit.transition.schema_version === 'pipeline-revival-reference/v1'
        ? await session.stepRevival(record.action)
        : await session.stepForcedSwitch(record.action);
    }
    const sourceTransition = commit.actors.length === 2
      ? committed.record_bundles.p1!.transition
      : committed.record_bundles[commit.actors[0]]!.transition;
    const transition: EpisodeEvidenceTransition = {
      schema_version: sourceTransition.schema_version,
      transition_id: sourceTransition.transition_id,
      parent_branch_id: sourceTransition.parent_branch_id,
      branch_id: sourceTransition.branch_id,
      input_state_fingerprint: sourceTransition.input_state_fingerprint,
      output_state_fingerprint: sourceTransition.output_state_fingerprint,
      simulator_revision: sourceTransition.simulator_revision,
      step_index: sourceTransition.step_index,
    };
    assert.deepEqual(transition, commit.transition);
    assert.equal(committed.boundary.state_fingerprint, commit.boundary.state_fingerprint);
    boundaries.push(committed.boundary);
    transitions.push({ transition, actors: [...commit.actors] });
  }
  return createPipelineEpisodeEvidence({
    run_id: result.run_id,
    battle_id: result.battle_id,
    ruleset: result.ruleset,
    kind: 'fresh_episode',
    boundaries,
    transitions,
  })!;
}
function choose(boundary: PipelineBoundary, p: PlayerID, choice: string) {
  const r = boundary.perspectives[p].observation.request!;
  const a = r.legal_actions.actions.find((a) => a?.choice === choice)!;
  assert.ok(a); return canonicalActionFromLegalAction(r, a.index);
}
function chooseFirstSwitch(boundary: PipelineBoundary, player: PlayerID) {
  const request = boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((candidate) => candidate?.choice.startsWith('switch '));
  assert.ok(action, `${player} needs a legal switch for the source turn-limit route`);
  return canonicalActionFromLegalAction(request, action.index);
}

test('v2 episode origin boundary requires exactly one visible Substitute roster row', async () => {
  const result = await runPipelineEpisode({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  const valid = withRehashedOriginVolatileRow(result, false);
  assert.doesNotThrow(() => validateObservableBattleState(valid.evidence_envelope!.origin.boundary.perspectives.p1));

  const omitted = withRehashedOriginVolatileRow(result, true);
  assert.throws(() => validatePipelineEpisodeEvidence(omitted.evidence_envelope!, omitted.records, evidenceExpectation(omitted)),
    /exactly one canonical self_team roster row/);
  const rejected = pythonRun(omitted);
  assert.equal(rejected.status, 2, rejected.stderr);
  assert.equal(rejected.stdout, '', 'missing-row episode evidence must not publish');
  assert.match(rejected.stderr, /exactly one canonical self_team roster row/);
});

test('C23 fully rehashed Wish episode health matrix rejects atomically in both runtimes', async () => {
  const direct = wishBattle('p1', 'heal');
  const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  let result: PipelineEpisodeResult;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(snapshot), options);
    };
    result = await runPipelineEpisode({
      battle_id: 'c23-wish-episode-health', format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION,
      policy_id: 'c23-wish-health-control/v1', limits: { max_transitions: 2 },
      action_order(observation) {
        const request = observation.request!;
        const choice = observation.perspective === 'p1'
          ? observation.view.turn === 1 ? 'move 1' : 'switch 2'
          : observation.view.turn === 1 ? 'move 1' : 'move 2';
        const preferred = request.legal_actions.actions.find((action) => action?.choice === choice);
        assert.ok(preferred, choice);
        return [preferred.index, ...request.legal_actions.available_indices.filter((index) => index !== preferred.index)];
      },
    });
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
    direct.destroy();
  }
  assert.equal(result.counts.committed_transitions, 2);
  assert.ok(result.evidence_envelope);
  assert.equal(result.evidence_envelope.origin.kind, 'fresh_episode');
  const before = structuredClone(result);
  validatePipelineEpisodeEvidence(result.evidence_envelope, result.records, evidenceExpectation(result));
  for (const player of PLAYERS) {
    const final = result.evidence_envelope.commits.at(-1)!.boundary.perspectives[player];
    assert.ok(final.protocol_prefix.includes('|-heal|p1a: Recipient|100/100|[from] move: Wish|[wisher] Wisher'));
  }
  for (const value of [result]) {
    const valid = pythonRun(value);
    assert.equal(valid.status, 0, valid.stderr);
    assert.equal(JSON.parse(valid.stdout).length, 4);
  }
  const changes: Array<[string, (row: Record<string, unknown>, view: Record<string, any>, team: string) => void]> = [
    ['false HP', (row) => { row.hp_text = '25/100'; row.hp_ratio = 0.25; }],
    ['false status', (row) => { row.status = 'brn'; row.status_started_turn = 2; row.status_turns_public = 0; }],
    ['false faint', (row) => { row.fainted = true; row.hp_text = '0'; row.hp_ratio = 0; row.active = false; }],
    ['missing HP', (row) => { delete row.hp_text; delete row.hp_ratio; }],
    ['missing status', (row) => { delete row.status; }],
    ['missing faint', (row) => { delete row.fainted; }],
    ['missing roster row', (row, view, team) => { view[team] = view[team].filter((entry: unknown) => entry !== row); }],
    ['partial roster container', (_row, view, team) => { delete view[team]; }],
    ['wrong side', (row, view, team) => {
      view[team] = view[team].filter((entry: unknown) => entry !== row);
      view[team === 'self_team' ? 'opponent_team' : 'self_team'].push(row);
    }],
    ['ambiguous roster row', (row, view, team) => { view[team].push(structuredClone(row)); }],
  ];
  for (const player of PLAYERS) for (const [label, mutate] of changes) {
    const finalId = result.final_boundary!.perspectives[player].observation_id;
    const candidate = withRehashedEpisodeObservations(result, player, (observation) => {
      if (observation.observation_id !== finalId) return;
      const team = player === 'p1' ? 'self_team' : 'opponent_team';
      const row = observation.view[team].find((pokemon) => pokemon.ident.replace(/^(p[12])a: /, '$1: ') === 'p1: Recipient');
      assert.ok(row);
      // Repair the v2 opposite-compartment stage shape so this reaches the health join.
      if (label === 'wrong side' && team === 'self_team') row.public_boosts = opponentPublicBoosts(observation.protocol_prefix, row.ident);
      mutate(row as unknown as Record<string, unknown>, observation.view, team);
    });
    const candidateBefore = structuredClone(candidate);
    // Check every canonical bundle identity before invoking semantic validation.
    for (const record of PLAYERS.flatMap((p) => candidate.records[p])) pythonCheckOriginRecordIdentity(record);
    let boundary = candidate.evidence_envelope!.origin.boundary;
    for (const commit of candidate.evidence_envelope!.commits) {
      for (const actor of commit.actors) {
        const record = candidate.records[actor].find((entry) => entry.transition.transition_id === commit.transition.transition_id)!;
        assert.deepEqual(record.input_observation, boundary.perspectives[actor]);
        assert.deepEqual(record.successor_observation, commit.boundary.perspectives[actor]);
      }
      boundary = commit.boundary;
    }
    assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)),
      /Public health evidence mismatch/, `${player} ${label}`);
    assert.deepEqual(candidate, candidateBefore, `${player} ${label}: no candidate mutation`);
    assert.deepEqual(result, before, `${player} ${label}: no committed evidence mutation`);
    for (const value of [candidate]) {
      const rejected = pythonRun(value);
      assert.equal(rejected.status, 2, `${player} ${label}: ${rejected.stderr}`);
      assert.equal(rejected.stdout, '', `${player} ${label}: no partial DATA-001 output`);
      assert.match(rejected.stderr, /Public health evidence mismatch/);
    }
  }
});

for (const family of ['Healing Wish', 'Future Sight', 'Revival Blessing'] as const) for (const actor of PLAYERS) {
  test(`C23 ${family} ${actor} full-result health rejection covers acting and waiting perspectives`, async () => {
    const direct = family === 'Healing Wish' ? healingWishBattle(actor, true)
      : family === 'Future Sight' ? futureSightBattle(actor, 'drag') : revivalBattle(actor);
    const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
    const startingTurn = direct.turn;
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) {
        return this.resetFromSerialized(structuredClone(snapshot), options);
      };
      session = await createPipelineIntegrationSession({
        battle_id: `c23-${family}-${actor}-envelope`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
        observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION,
      });
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; direct.destroy(); }
    const originBeliefs = PLAYERS.map((player) => structuredClone(session.boundary.perspectives[player].belief));
    let finalBeliefs: EpisodeBelief[] = [];
    const close = session.close.bind(session);
    session.close = async () => {
      finalBeliefs = PLAYERS.map((player) => structuredClone(session.boundary.perspectives[player].belief));
      await close();
    };
    const result = await continuePipelineEpisode(session, {
      policy_id: 'c23-slot-result-health/v1',
      limits: { max_transitions: family === 'Healing Wish' ? 2 : family === 'Future Sight' ? 3 : 1 },
      action_order(observation) {
        const request = observation.request!;
        const own = observation.perspective === actor;
        const offset = observation.view.turn - startingTurn;
        const choice = own && (request.force_switch || request.side.some((row) => row.reviving)) ? 'switch 2'
          : own && family === 'Future Sight' ? `move ${Math.min(offset + 1, 3)}` : 'move 1';
        const preferred = request.legal_actions.actions.find((action) => action?.choice === choice);
        assert.ok(preferred, `${family} ${actor} ${choice}`);
        return [preferred.index, ...request.legal_actions.available_indices.filter((index) => index !== preferred.index)];
      },
    });
    const boundaryBeliefs = [...originBeliefs, ...finalBeliefs];
    assert.ok(result.evidence_envelope);
    assert.equal(result.evidence_envelope.origin.kind, 'continuation_segment');
    assert.equal(result.evidence_envelope.closure!.complete_capture, false);
    const targetName = family === 'Healing Wish' ? 'Recipient' : family === 'Future Sight' ? 'Reserve' : 'First';
    const prefix = result.evidence_envelope.commits.at(-1)!.boundary.perspectives.p1.protocol_prefix;
    assert.ok(prefix.some((line) => line.includes(family === 'Future Sight' ? '|move: Future Sight' : `[from] move: ${family}`)), family);
    const valid = pythonRun(result);
    assert.equal(valid.status, 0, valid.stderr);
    assert.equal(JSON.parse(valid.stdout).length, result.records.p1.length + result.records.p2.length);
    validatePipelineEpisodeEvidence(result.evidence_envelope, result.records, evidenceExpectation(result));
    const committed = structuredClone(result);
    for (const player of PLAYERS) for (const defect of ['HP', 'status', 'faint']) {
      const finalId = result.final_boundary!.perspectives[player].observation_id;
      const candidate = withRehashedEpisodeObservations(result, player, (observation) => {
        if (observation.observation_id !== finalId) return;
        const row = [...observation.view.self_team, ...observation.view.opponent_team].find((pokemon) => pokemon.name === targetName)!;
        assert.ok(row, targetName);
        if (defect === 'HP') { const ratio = (row.hp_ratio ?? 0) > .5 ? .25 : .75; row.hp_text = `${ratio * 100}/100`; row.hp_ratio = ratio; }
        else if (defect === 'status') { row.status = row.status === 'brn' ? 'par' : 'brn'; row.status_started_turn = observation.view.turn; row.status_turns_public = 0; }
        else row.fainted = !row.fainted;
      }, boundaryBeliefs);
      for (const record of PLAYERS.flatMap((p) => candidate.records[p])) pythonCheckOriginRecordIdentity(record);
      const previous = candidate.evidence_envelope!.commits.length === 1 ? candidate.evidence_envelope!.origin.boundary
        : candidate.evidence_envelope!.commits.at(-2)!.boundary;
      const final = candidate.evidence_envelope!.commits.at(-1)!;
      for (const acting of final.actors) {
        const record = candidate.records[acting].find((entry) => entry.transition.transition_id === final.transition.transition_id)!;
        assert.deepEqual(record.input_observation, previous.perspectives[acting]);
        assert.deepEqual(record.successor_observation, final.boundary.perspectives[acting]);
      }
      const before = structuredClone(candidate);
      assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)), /Public health evidence mismatch/, `${family} ${actor}/${player}/${defect}`);
      assert.deepEqual(candidate, before);
      assert.deepEqual(result, committed);
      const invalid = pythonRun(candidate);
      assert.equal(invalid.status, 2, invalid.stderr);
      assert.equal(invalid.stdout, '', `${family} ${actor}/${player}/${defect}: atomic DATA-001 rejection`);
      assert.match(invalid.stderr, /Public health evidence mismatch/);
    }
    if (family === 'Revival Blessing') {
      const waiting = actor === 'p1' ? 'p2' : 'p1';
      assert.equal(result.records[waiting].length, 0, 'no fabricated waiting-side decision row');
    }
  });
}

test('C23 original-to-terminal publication sweep rejects rehashed origin health omissions', async () => {
  const result = await runPipelineEpisode({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  assert.equal(result.status, 'completed');
  assert.equal(result.evidence_envelope!.closure!.complete_capture, true);
  const original = structuredClone(result);
  const valid = pythonRun(pythonPublicationSweep(result));
  assert.equal(valid.status, 0, valid.stderr);
  assert.equal(JSON.parse(valid.stdout).length, PLAYERS.reduce((count, player) => count + result.records[player].length, 0));
  for (const player of PLAYERS) for (const defect of ['false HP', 'missing row', 'missing status']) {
    const originId = result.evidence_envelope!.origin.boundary.perspectives[player].observation_id;
    const candidate = withRehashedEpisodeObservations(result, player, (observation) => {
      if (observation.observation_id !== originId) return;
      const row = observation.view.self_team.find((pokemon) => pokemon.active)!;
      assert.ok(row);
      if (defect === 'false HP') { row.hp_text = '25/100'; row.hp_ratio = 0.25; }
      else if (defect === 'missing status') delete (row as unknown as Record<string, unknown>).status;
      else observation.view.self_team = observation.view.self_team.filter((pokemon) => pokemon !== row);
    });
    // These are origin joins, not stale IDs or broken first-record lineage.
    const first = candidate.records[player][0];
    assert.deepEqual(first.input_observation, candidate.evidence_envelope!.origin.boundary.perspectives[player]);
    pythonCheckOriginRecordIdentity(first);
    const before = structuredClone(candidate);
    assert.throws(() => validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate)),
      /Public health evidence mismatch/);
    assert.deepEqual(candidate, before);
    assert.deepEqual(result, original);
    const rejected = pythonRun(pythonPublicationSweep(candidate));
    assert.equal(rejected.status, 2, `${player} ${defect}: ${rejected.stderr}`);
    assert.equal(rejected.stdout, '', 'invalid origin health cannot leak any earlier actor row');
    assert.match(rejected.stderr, /Public health evidence mismatch/);
  }
  const finalId = result.final_boundary!.perspectives.p1.observation_id;
  const redirect = withRehashedEpisodeObservations(result, 'p1', (observation) => {
    if (observation.observation_id !== finalId) return;
    const active = observation.view.self_team.find((row) => row.active)!;
    const other = observation.view.self_team.find((row) => row !== active)!;
    assert.ok(active && other);
    observation.view.self_team = observation.view.self_team.filter((row) => row !== active);
    other.active = true;
  });
  for (const record of redirect.records.p1) pythonCheckOriginRecordIdentity(record);
  const redirectBefore = structuredClone(redirect);
  assert.throws(() => validatePipelineEpisodeEvidence(redirect.evidence_envelope!, redirect.records, evidenceExpectation(redirect)),
    /Public health evidence mismatch/, 'a forged active row cannot bind a requestless public carrier');
  assert.deepEqual(redirect, redirectBefore);
  assert.deepEqual(result, original);
  for (const value of [redirect, pythonPublicationSweep(redirect)]) {
    const rejected = pythonRun(value);
    assert.equal(rejected.status, 2, rejected.stderr);
    assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /Public health evidence mismatch/);
  }

});

test('real episode completes repeatably through joint and both one-sided actor paths, with valid partial lineage', async () => {
  const first = await runPipelineEpisode(CONFIG);
  const repeated = await runPipelineEpisode(CONFIG);
  assert.equal(first.status, 'completed');
  assert.equal(first.stop.code, 'episode/v1/terminal');
  assert.equal(first.counts.committed_transitions, 55);
  assert.equal(first.evidence_envelope, null);
  assert.deepEqual(first, repeated);
  assertRecords(first);
  assert.equal(first.final_boundary?.kind, 'terminal');
  for (const p of PLAYERS) {
    assert.equal(first.final_boundary?.perspectives[p].request_state, 'terminal');
    assert.ok(first.records[p].some((r) => r.schema_version === 'pipeline-forced-switch-record/v1'));
    pythonValidate(first.records[p].at(-1));
  }
});

test('v2 evidence retains both owners at every commit and rejects rehashed chain tampering in TypeScript and Python', async () => {
  const result = await runPipelineEpisode({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  const envelope = result.evidence_envelope;
  assert.equal(result.status, 'completed');
  assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
  assert.ok(envelope);
  validatePipelineEpisodeEvidence(envelope, result.records, evidenceExpectation(result));
  assert.equal(envelope.schema_version, 'pipeline-episode-evidence/v2');
  assert.equal(envelope.closure?.origin_coverage, 'original_initial_requests');
  assert.equal(envelope.closure?.complete_capture, true);
  assert.equal(envelope.closure?.terminal?.outcome, 'win');
  assert.equal(envelope.closure?.terminal?.winner, 'p1');
  assert.equal(envelope.closure?.terminal?.final_boundary.step_index, envelope.commits.at(-1)?.boundary.step_index);
  assert.equal(envelope.origin.kind, 'fresh_episode');
  assert.equal(envelope.origin.boundary.perspectives.p1.request?.player, 'p1');
  assert.equal(envelope.origin.boundary.perspectives.p2.request?.player, 'p2');
  assert.equal(envelope.commits.length, result.counts.committed_transitions);
  assert.ok(envelope.commits.some((commit) => commit.actors.length === 1));
  for (const [index, commit] of envelope.commits.entries()) if (commit.actors.length === 1) {
    const waiting = commit.actors[0] === 'p1' ? 'p2' : 'p1';
    const input: PipelineEpisodeEvidence['origin']['boundary'] = index === 0
      ? envelope.origin.boundary : envelope.commits[index - 1].boundary;
    assert.equal(input.perspectives[waiting].request?.wait, true);
    assert.equal(result.records[waiting].some((record) => record.transition.transition_id === commit.transition.transition_id), false);
  }
  const published = pythonRun(result);
  assert.equal(published.status, 0, published.stderr);
  const rows = JSON.parse(published.stdout) as Array<Record<string, unknown>>;
  assert.equal(rows.length, result.records.p1.length + result.records.p2.length);
  assert.equal(rows.length, envelope.commits.reduce((count, commit) => count + commit.actors.length, 0));
  const sweepPublished = pythonRun(pythonPublicationSweep(result));
  assert.equal(sweepPublished.status, 0, sweepPublished.stderr);
  assert.deepEqual(
    (JSON.parse(sweepPublished.stdout) as Array<{ transition_id: string; perspective: PlayerID }>).map(({ transition_id, perspective }) => [perspective, transition_id]),
    PLAYERS.flatMap((player) => result.records[player].map((record) => [player, record.transition.transition_id])),
    'bulk publication preserves one-sided actor-only DATA-001 row ordering',
  );
  const evidenceOnly = pythonRun(envelope);
  assert.equal(evidenceOnly.status, 0, evidenceOnly.stderr);
  assert.equal(JSON.parse(evidenceOnly.stdout).committed_transitions, envelope.commits.length);
  const legacyControl = structuredClone(envelope);
  legacyControl.schema_version = 'pipeline-episode-evidence/v1';
  delete legacyControl.closure;
  const legacyEvidence = reseal(legacyControl);
  validatePipelineEpisodeEvidence(legacyEvidence, result.records, evidenceExpectation(result));
  assert.equal(pythonRun(legacyEvidence).status, 0, 'historical v1 evidence remains readable');

  const encodedEnvelope = JSON.stringify(envelope);
  for (const privateKey of ['"simulator_snapshot"', '"simulator_state"', '"seed"', '"hidden_roster"', '"hidden_set"', '"opponent_request"']) {
    assert.equal(encodedEnvelope.includes(privateKey), false, `${privateKey} must not enter episode evidence`);
  }

  const wrongWinner = structuredClone(envelope);
  wrongWinner.closure!.terminal!.winner = 'p2';
  assertFullResultTamperRejected(result, reseal(wrongWinner), 'rehashed terminal winner');
  const wrongOutcome = structuredClone(envelope);
  wrongOutcome.closure!.terminal!.outcome = 'tie';
  assertFullResultTamperRejected(result, reseal(wrongOutcome), 'rehashed terminal win/tie outcome');
  const wrongFinalCursor = structuredClone(envelope);
  wrongFinalCursor.closure!.terminal!.final_boundary.perspectives.p1.event_cursor++;
  assertFullResultTamperRejected(result, reseal(wrongFinalCursor), 'rehashed terminal cursor');
  const wrongFinalBoundary = structuredClone(envelope);
  wrongFinalBoundary.closure!.terminal!.final_boundary.state_fingerprint = '0'.repeat(64);
  assertFullResultTamperRejected(result, reseal(wrongFinalBoundary), 'rehashed terminal final-boundary reference');
  const wrongCoverage = structuredClone(envelope);
  wrongCoverage.closure!.origin_coverage = 'segment_only';
  wrongCoverage.closure!.complete_capture = false;
  assertFullResultTamperRejected(result, reseal(wrongCoverage), 'rehashed origin coverage downgrade');

  const committedBefore = structuredClone(result);
  const foreignRequestResult = withRehashedForeignOriginRequest(result);
  const tamperedBeforeValidation = structuredClone(foreignRequestResult);
  assert.throws(() => validatePipelineEpisodeEvidence(
    foreignRequestResult.evidence_envelope!, foreignRequestResult.records, evidenceExpectation(foreignRequestResult),
  ), /Observation request perspective or rqid is invalid/);
  assert.deepEqual(foreignRequestResult, tamperedBeforeValidation, 'rejected full-result validation must preserve its evidence and lineage');
  assert.deepEqual(result, committedBefore, 'foreign-request rejection must preserve the committed result');
  const invalidPrivacyPublication = pythonRun(foreignRequestResult);
  assert.equal(invalidPrivacyPublication.status, 2, invalidPrivacyPublication.stderr);
  assert.equal(invalidPrivacyPublication.stdout, '', 'invalid privacy evidence must not publish DATA-001 rows');
  assert.match(invalidPrivacyPublication.stderr, /request is not owned by its perspective/);

  const gap = structuredClone(envelope);
  gap.commits.splice(1, 1);
  assertTamperRejected(result, reseal(gap), 'gap', /lineage|gap, reorder, or transition mismatch|terminal transition continuity is invalid/);

  const reordered = structuredClone(envelope);
  [reordered.commits[0], reordered.commits[1]] = [reordered.commits[1], reordered.commits[0]];
  assertTamperRejected(result, reseal(reordered), 'reorder', /lineage|gap, reorder, or transition mismatch|terminal transition continuity is invalid/);

  const duplicate = structuredClone(envelope);
  const duplicateId = duplicate.commits[0].transition.transition_id;
  const duplicatePrevious = duplicate.commits[0].boundary;
  const duplicateActors = evidenceActorsAt(duplicatePrevious);
  assert.ok(duplicateActors.length);
  const repeated = structuredClone(duplicate.commits[0]);
  repeated.actors = duplicateActors;
  repeated.transition.transition_id = duplicateId;
  repeated.transition.schema_version = duplicateActors.length === 2 ? 'pipeline-transition-reference/v1'
    : duplicatePrevious.kind === 'one_sided_revival' ? 'pipeline-revival-reference/v1' : 'pipeline-forced-switch-reference/v1';
  repeated.transition.step_index = duplicatePrevious.step_index;
  repeated.transition.parent_branch_id = duplicatePrevious.branch_id;
  repeated.transition.branch_id = `${duplicatePrevious.branch_id}-duplicate`;
  repeated.transition.input_state_fingerprint = duplicatePrevious.state_fingerprint;
  repeated.transition.output_state_fingerprint = duplicatePrevious.state_fingerprint;
  repeated.boundary.step_index = duplicatePrevious.step_index + 1;
  repeated.boundary.branch_id = repeated.transition.branch_id;
  repeated.boundary.state_fingerprint = duplicatePrevious.state_fingerprint;
  duplicate.commits.splice(1, 0, repeated);
  assertTamperRejected(result, reseal(duplicate), 'duplicate', /duplicate.*transition|episode actor action does not join the retained transition boundaries/);

  let prefixResult = result;
  for (const player of PLAYERS) {
    const originId = result.evidence_envelope!.origin.boundary.perspectives[player].observation_id;
    prefixResult = withRehashedEpisodeObservations(prefixResult, player, (observation) => {
      if (observation.observation_id !== originId) observation.protocol_prefix[0] = '|t:|1';
    }, [], false); // The deliberate prefix contradiction is validated below, after canonical sealing.
  }
  const prefixRecords: PipelineEpisodeResult['records']['p1'] = [];
  let prefixPrevious = prefixResult.evidence_envelope!.origin.boundary;
  for (const commit of prefixResult.evidence_envelope!.commits) {
    for (const player of commit.actors) {
      const record = prefixResult.records[player].find((entry) => entry.transition.transition_id === commit.transition.transition_id)!;
      assert.deepEqual(record.input_observation, prefixPrevious.perspectives[player], 'prefix tamper input joins retained boundary');
      assert.deepEqual(record.successor_observation, commit.boundary.perspectives[player], 'prefix tamper successor joins retained boundary');
      assert.deepEqual(record.input_belief.observation, observationReference(record.input_observation));
      assert.deepEqual(record.successor_belief.observation, observationReference(record.successor_observation));
      assert.equal(record.successor_belief.parent_belief_id, record.input_belief.belief_id);
      const references = [prefixResult.evidence_envelope!.origin.boundary, ...prefixResult.evidence_envelope!.commits.map((entry) => entry.boundary)]
        .map((boundary) => boundary.perspectives[player]);
      for (const belief of [record.input_belief, record.successor_belief]) for (const reference of belief.observation_history) {
        const observation = references.find((entry) => entry.observation_id === reference.observation_id);
        assert.ok(observation, 'historical reference must join an actual retained observation');
        assert.deepEqual(reference, observationReference(observation));
      }
      // Full bundle identity verification also enforces the deliberately broken prefix extension.
      prefixRecords.push(record);
    }
    prefixPrevious = commit.boundary;
  }
  pythonCheckOriginRecordIdentity(prefixRecords.slice(0, 2), true); // Independent canonical proof at the deliberately changed edge.
  assertFullResultTamperRejected(prefixResult, prefixResult.evidence_envelope!, 'joined prefix mutation', /evidence-commit-0-p1-prefix-lineage/, /episode commit 0 p1 public prefix was mutated/);
  assert.deepEqual(result, committedBefore, 'joined prefix rejection preserves original committed evidence');

  const forgedOrigin = structuredClone(envelope);
  forgedOrigin.origin.origin_id = `episode-origin-${'0'.repeat(64)}`;
  for (const commit of forgedOrigin.commits) commit.origin_id = forgedOrigin.origin.origin_id;
  assertTamperRejected(result, reseal(forgedOrigin), 'forged origin', /origin/);
});

test('continuation v2 evidence binds its segment origin to both current owned observations', async () => {
  const session = await createPipelineIntegrationSession({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  const origin = structuredClone({ p1: session.boundary.perspectives.p1.observation, p2: session.boundary.perspectives.p2.observation });
  const result = await continuePipelineEpisode(session, { limits: { max_transitions: 1 } });
  assert.equal(result.evidence_envelope?.origin.kind, 'continuation_segment');
  assert.deepEqual(result.evidence_envelope?.origin.boundary.perspectives, origin);
  assert.equal(result.evidence_envelope?.commits.length, 1);
  assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
  const publication = pythonRun(result);
  assert.equal(publication.status, 0, publication.stderr);
  assert.equal(JSON.parse(publication.stdout).length, 2);

  const forgedOrigin = structuredClone(result.evidence_envelope!);
  forgedOrigin.origin.kind = 'fresh_episode';
  const rehashedOrigin = reorigin(forgedOrigin);
  const candidateBefore = structuredClone(rehashedOrigin);
  const committedEvidenceBefore = structuredClone(result.evidence_envelope);
  const committedRecordsBefore = structuredClone(result.records);
  assert.throws(() => validatePipelineEpisodeEvidence(
    rehashedOrigin, result.records, evidenceExpectation(result),
  ), /origin/);
  assert.deepEqual(rehashedOrigin, candidateBefore, 'fully rehashed origin mismatch must not mutate its candidate');
  assert.deepEqual(result.evidence_envelope, committedEvidenceBefore, 'rejected origin must preserve committed evidence');
  assert.deepEqual(result.records, committedRecordsBefore, 'rejected origin must preserve committed records');
  const invalidOriginPublication = pythonRun(rehashedOrigin);
  assert.equal(invalidOriginPublication.status, 2, invalidOriginPublication.stderr);
  assert.equal(invalidOriginPublication.stdout, '', 'invalid origin cannot publish DATA-001 rows');
});

for (const actor of PLAYERS) {
  test(`source Destiny Bond simultaneous terminal ${actor} closes from original requests and publishes both actors`, async () => {
    const own = Teams.generate('gen9randombattle', { seed: [147, 2, 3, 4] })[0];
    assert.equal(own.species, 'Froslass');
    assert.ok(own.moves.includes('destinybond') && own.moves.includes('poltergeist'));
    const other = Teams.import('Snorlax\nAbility: Immunity\n- Splash\n- Crunch\n')![0];
    const sourceBattle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
    sourceBattle.setPlayer('p1', { name: 'Agent-1', team: actor === 'p1' ? [own] : [other] });
    sourceBattle.setPlayer('p2', { name: 'Agent-2', team: actor === 'p2' ? [own] : [other] });
    const sourceSnapshot = structuredClone(sourceBattle.toJSON()) as unknown as Record<string, unknown>;
    sourceBattle.destroy();

    const originalReset = LocalBattleEnv.prototype.resetWithOptions;
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(sourceSnapshot), options);
    };
    const create = () => {
      let phase = 0;
      const sourceChoices = [
        `move ${own.moves.indexOf('destinybond') + 1}`,
        `move ${own.moves.indexOf('poltergeist') + 1}`,
        `move ${own.moves.indexOf('destinybond') + 1}`,
      ];
      const opponentChoices = ['move 1', 'move 2', 'move 2'];
      return runPipelineEpisode({
        battle_id: `episode-simultaneous-destinybond-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
        observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION,
        limits: { max_transitions: 6, max_attempts: 12 },
        policy_id: `source-destinybond-simultaneous-${actor}/v1`,
        action_order: (observation) => {
          const player = observation.perspective;
          const desired = player === actor ? sourceChoices[phase] : opponentChoices[phase];
          const request = observation.request!;
          const selected = request.legal_actions.actions.find((action) => action?.choice === desired);
          assert.ok(selected, `${player} source request must expose ${desired}`);
          if (player === 'p2') phase++;
          return [selected.index, ...request.legal_actions.available_indices.filter((index) => index !== selected.index)];
        },
      });
    };
    try {
      const result = await create();
      const repeated = await create();
      assert.equal(result.status, 'completed', result.stop.reason);
      assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
      assert.equal(result.evidence_envelope?.origin.kind, 'fresh_episode');
      assert.equal(result.evidence_envelope?.origin.boundary.step_index, 0);
      assert.equal(result.evidence_envelope?.origin.boundary.perspectives.p1.request?.player, 'p1');
      assert.equal(result.evidence_envelope?.origin.boundary.perspectives.p2.request?.player, 'p2');
      assert.equal(result.evidence_envelope?.closure?.origin_coverage, 'original_initial_requests');
      assert.equal(result.evidence_envelope?.closure?.complete_capture, true);
      assert.equal(result.evidence_envelope?.closure?.terminal?.outcome, 'win');
      assert.ok(result.evidence_envelope?.commits.length === 3);
      const terminal = result.evidence_envelope!.commits.at(-1)!.boundary;
      assert.equal(terminal.perspectives.p1.view.winner, terminal.perspectives.p2.view.winner);
      assert.equal(terminal.perspectives.p1.view.winner, result.evidence_envelope?.closure?.terminal?.winner);
      assert.equal(terminal.perspectives.p1.request, null);
      assert.equal(terminal.perspectives.p2.request, null);
      assert.ok(terminal.perspectives.p1.protocol_prefix.some((line) => line.startsWith('|faint|')));
      assert.equal(terminal.perspectives.p1.protocol_prefix.filter((line) => line.startsWith('|faint|')).length, 2);
      const winIndex = terminal.perspectives.p1.protocol_prefix.findIndex((line) => line.startsWith('|win|'));
      assert.ok(winIndex >= 0);
      assert.equal(terminal.perspectives.p1.protocol_prefix.slice(winIndex + 1).some((line) => line.startsWith('|move|')), false);
      assert.deepEqual(repeated.evidence_envelope, result.evidence_envelope, 'restoration/replay must reproduce simultaneous terminal evidence');
      assert.deepEqual(repeated.transition_ids, result.transition_ids);
      const terminalTamper = structuredClone(result.evidence_envelope!);
      terminalTamper.closure!.terminal!.outcome = 'tie';
      terminalTamper.closure!.terminal!.winner = 'tie';
      const rehashedTerminalTamper = reseal(terminalTamper);
      const candidateBeforeValidation = structuredClone(rehashedTerminalTamper);
      const committedEvidenceBeforeValidation = structuredClone(result.evidence_envelope);
      const committedRecordsBeforeValidation = structuredClone(result.records);
      assert.throws(() => validatePipelineEpisodeEvidence(
        rehashedTerminalTamper, result.records, evidenceExpectation(result),
      ));
      assert.deepEqual(rehashedTerminalTamper, candidateBeforeValidation,
        'rejected rehashed terminal tamper cannot mutate its candidate');
      assert.deepEqual(result.evidence_envelope, committedEvidenceBeforeValidation,
        'rejected terminal tamper must preserve committed evidence');
      assert.deepEqual(result.records, committedRecordsBeforeValidation,
        'rejected terminal tamper must preserve committed actor records');
      const invalidTerminalPublication = pythonRun(rehashedTerminalTamper);
      assert.equal(invalidTerminalPublication.status, 2, invalidTerminalPublication.stderr);
      assert.equal(invalidTerminalPublication.stdout, '', 'invalid terminal evidence cannot publish DATA-001 rows');
      const publication = pythonRun(result);
      assert.equal(publication.status, 0, publication.stderr);
      assert.equal(JSON.parse(publication.stdout).length,
        result.records.p1.length + result.records.p2.length);
      for (const player of PLAYERS) {
        assert.equal(result.records[player].length,
          result.evidence_envelope!.commits.filter((commit) => commit.actors.includes(player)).length);
      }
    } finally {
      LocalBattleEnv.prototype.resetWithOptions = originalReset;
    }
  });
}

test('source turn-limit tie retains a complete two-perspective chain and bulk-publishes every actor row', async (t) => {
  const integrationOptions = {
    battle_id: 'episode-source-turn-limit-tie', format: 'gen9randombattle', seed: [31, 37, 41, 43],
    observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION,
  } as const;
  const episodeOptions = {
    limits: { max_transitions: 1_050, max_attempts: 1_050 },
    policy_id: 'source-legal-switch-stall/v1',
    action_order: (observation: PipelineBoundary['perspectives']['p1']['observation']) => {
      const actions = observation.request!.legal_actions;
      const switches = actions.actions.filter((action) => action?.choice.startsWith('switch ')).map((action) => action!.index);
      return [...switches, ...actions.available_indices.filter((index) => !switches.includes(index))];
    },
  } as const;
  const session = await createPipelineIntegrationSession(integrationOptions);
  const initialBoundary = session.boundary;
  const firstCommit = await session.step({
    p1: chooseFirstSwitch(initialBoundary, 'p1'), p2: chooseFirstSwitch(initialBoundary, 'p2'),
  });
  const replaySession = await createPipelineIntegrationSession(integrationOptions);
  const replayFirstCommit = await replaySession.step({
    p1: chooseFirstSwitch(replaySession.boundary, 'p1'), p2: chooseFirstSwitch(replaySession.boundary, 'p2'),
  });
  assert.equal(replayFirstCommit.transition_id, firstCommit.transition_id);
  assert.equal(replayFirstCommit.boundary.state_fingerprint, firstCommit.boundary.state_fingerprint);
  for (const player of PLAYERS) {
    assert.equal(replayFirstCommit.boundary.perspectives[player].observation.observation_id,
      firstCommit.boundary.perspectives[player].observation.observation_id);
    assert.deepEqual(replayFirstCommit.boundary.perspectives[player].observation.protocol_prefix,
      firstCommit.boundary.perspectives[player].observation.protocol_prefix);
  }
  await replaySession.close();
  const firstRecords = firstCommit.record_bundles;
  assert.ok(firstRecords.p1 && firstRecords.p2);
  const transition = firstRecords.p1.transition;
  const predecessor = createPipelineEpisodeEvidence({
    run_id: `episode-${'0'.repeat(64)}`,
    battle_id: integrationOptions.battle_id, ruleset: integrationOptions.format,
    kind: 'fresh_episode', boundaries: [initialBoundary, firstCommit.boundary],
    transitions: [{
      transition: {
        schema_version: transition.schema_version, transition_id: transition.transition_id,
        parent_branch_id: transition.parent_branch_id, branch_id: transition.branch_id,
        input_state_fingerprint: transition.input_state_fingerprint,
        output_state_fingerprint: transition.output_state_fingerprint,
        simulator_revision: transition.simulator_revision, step_index: transition.step_index,
      },
      actors: ['p1', 'p2'],
    }],
  })!;
  validatePipelineEpisodeEvidence(predecessor, { p1: [firstRecords.p1], p2: [firstRecords.p2] });

  console.log('CE-08A isolated turn-limit: native commits started');
  const commitStarted = Date.now(), originalStep = session.step.bind(session);
  session.step = async (actions) => {
    const commit = await originalStep(actions);
    if (commit.boundary.step_index % 100 === 0) console.log(`CE-08A isolated turn-limit: ${commit.boundary.step_index} commits, ${Date.now() - commitStarted}ms`);
    return commit;
  };
  let result: PipelineEpisodeResult;
  try {result = await continuePipelineEpisode(session, { ...episodeOptions, predecessor_evidence: predecessor });}
  finally {session.step = originalStep;}
  console.log(`CE-08A isolated turn-limit: native chain completed, ${Date.now() - commitStarted}ms`);
  assert.equal(result.status, 'completed', result.stop.reason);
  assert.equal(result.stop.code, 'episode/v1/terminal');
  const envelope = result.evidence_envelope!;
  const completeCommits = [...predecessor.commits, ...envelope.commits];
  assert.ok(completeCommits.length >= 990 && completeCommits.length <= 1_000);
  assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
  assertRecords(result);
  assert.equal(envelope.closure?.terminal?.outcome, 'tie');
  assert.equal(envelope.closure?.terminal?.winner, 'tie');
  assert.equal(envelope.closure?.origin_coverage, 'original_initial_requests');
  assert.equal(envelope.closure?.complete_capture, true);
  assert.equal(envelope.origin.kind, 'continuation_segment');
  assert.deepEqual(envelope.closure?.predecessor, predecessor);
  const originalBoundary = predecessor.origin.boundary;
  const finalBoundary = envelope.commits.at(-1)!.boundary;
  for (const player of PLAYERS) {
    const origin = originalBoundary.perspectives[player];
    const finalObservation = finalBoundary.perspectives[player];
    assert.equal(origin.view.terminated, false);
    assert.equal(origin.request?.player, player);
    assert.equal(finalObservation.view.terminated, true);
    assert.equal(finalObservation.view.winner, 'tie');
    assert.equal(finalObservation.request, null);
    assert.equal(finalObservation.protocol_prefix.at(-1), '|tie');
    assert.ok(finalObservation.protocol_prefix.some((line: string) => line === '|bigerror|You will auto-tie if the battle doesn\'t end in 1 turn (on turn 1000).'));
  }
  for (const [index, commit] of completeCommits.entries()) {
    assert.equal(commit.boundary.step_index, index + 1);
    for (const player of PLAYERS) {
      const prior = index === 0 ? originalBoundary.perspectives[player] : completeCommits[index - 1].boundary.perspectives[player];
      const next = commit.boundary.perspectives[player];
      assert.ok(next.event_cursor > prior.event_cursor);
      assert.equal(next.event_cursor, next.protocol_prefix.length);
      assert.deepEqual(next.protocol_prefix.slice(0, prior.event_cursor), prior.protocol_prefix);
    }
  }
  for (const player of PLAYERS) {
    assert.equal(result.records[player].length, envelope.commits.filter((commit) => commit.actors.includes(player)).length);
    assert.equal(result.records[player].at(-1)?.successor_observation.request, null);
  }
  const sweepStarted = Date.now();
  const sweep = pythonPublicationSweep(result);
  console.log('CE-08A isolated turn-limit: Python bulk publication started (360s timeout)');
  const publication = pythonRun(sweep, 360_000);
  console.log(`CE-08A isolated turn-limit: Python bulk completed, ${Date.now() - sweepStarted}ms`);
  const sweepElapsedMs = Date.now() - sweepStarted;
  assert.equal(publication.status, 0, publication.stderr);
  const publishedRows = JSON.parse(publication.stdout) as Array<{ transition_id: string; perspective: PlayerID }>;
  const expectedRows = PLAYERS.flatMap((player) => result.records[player].map((record) => ({
    transition_id: record.transition.transition_id, perspective: player,
  })));
  const eligibleActorBundles = envelope.commits.reduce((count, commit) => count + commit.actors.length, 0);
  assert.equal(expectedRows.length, eligibleActorBundles);
  assert.deepEqual(publishedRows.map(({ transition_id, perspective }) => ({ transition_id, perspective })), expectedRows,
    'the sweep emits one DATA-001 row for each current-segment actor bundle and none for waiting sides');
  assert.ok(sweepElapsedMs < 300_000, `bulk publication must remain bounded; took ${sweepElapsedMs}ms`);
  t.diagnostic(`CE-08A turn-limit bulk publication: ${publishedRows.length} actor rows in ${sweepElapsedMs}ms`);

  const middleJointCommit = envelope.commits.slice(Math.floor(envelope.commits.length / 3), Math.ceil(envelope.commits.length * 2 / 3))
    .find((commit) => commit.actors.length === 2);
  assert.ok(middleJointCommit, 'source turn-limit chain has a middle joint actor row for the rehashed control');
  const p1Bundle = result.records.p1.find((record) => record.transition.transition_id === middleJointCommit.transition.transition_id)!;
  const p2Bundle = result.records.p2.find((record) => record.transition.transition_id === middleJointCommit.transition.transition_id)!;
  assert.doesNotThrow(() => serializeCanonicalAction(p2Bundle.action, p2Bundle.input_observation.request!, 'p2'));
  const invalidMiddleSweep = structuredClone(sweep);
  const invalidMiddleRow = invalidMiddleSweep.records.p1.find((row) => row.transition_id === middleJointCommit.transition.transition_id)!;
  invalidMiddleRow.action = structuredClone(p2Bundle.action);
  assert.equal(invalidMiddleRow.action.action_id, p2Bundle.action.action_id,
    'transplanted p2 action retains its canonical identity; the sweep derives the matching transition action ID');
  assert.throws(
    () => serializeCanonicalAction(invalidMiddleRow.action, p1Bundle.input_observation.request!, 'p1'),
    /player/i,
    'TypeScript rejects the fully identity-consistent foreign-owner action',
  );
  const committedEvidenceId = envelope.evidence_id;
  const committedActionId = p1Bundle.action.action_id;
  console.log('CE-08A isolated turn-limit: atomic invalid-middle sweep started (360s timeout)');
  const invalidMiddlePublication = pythonRun(invalidMiddleSweep, 360_000);
  console.log('CE-08A isolated turn-limit: atomic invalid-middle sweep completed');
  assert.equal(invalidMiddlePublication.status, 2, invalidMiddlePublication.stderr);
  assert.equal(invalidMiddlePublication.stdout, '', 'invalid middle-row sweep must publish no earlier DATA-001 rows');
  assert.match(invalidMiddlePublication.stderr, /canonical action validation failed.*player/i);
  assert.equal(envelope.evidence_id, committedEvidenceId);
  assert.equal(p1Bundle.action.action_id, committedActionId);

  assert.equal(pythonPublishBundles([firstRecords.p1, firstRecords.p2]), 2,
    'the continuation predecessor transition remains separately published through ordinary one-bundle validation');

  const wrongOutcome = structuredClone(envelope);
  wrongOutcome.closure!.terminal!.winner = 'p1';
  const wrongOutcomeRehashed = reseal(wrongOutcome);
  const resultEvidenceId = envelope.evidence_id;
  const resultTransitionIds = [...result.transition_ids];
  const resultRecordRefs = Object.fromEntries(PLAYERS.map((player) => [player, result.records[player].map((record) => [
    record.transition.transition_id, record.input_observation.observation_id,
    record.successor_observation.observation_id, record.successor_belief.belief_id,
  ])]));
  const wrongOutcomeBefore = structuredClone(wrongOutcomeRehashed);
  assert.throws(() => validatePipelineEpisodeEvidence(wrongOutcomeRehashed, result.records, evidenceExpectation(result)));
  assert.deepEqual(wrongOutcomeRehashed, wrongOutcomeBefore, 'rejected outcome tamper cannot mutate its candidate');
  assert.equal(envelope.evidence_id, resultEvidenceId);
  assert.deepEqual(result.transition_ids, resultTransitionIds);
  assert.deepEqual(Object.fromEntries(PLAYERS.map((player) => [player, result.records[player].map((record) => [
    record.transition.transition_id, record.input_observation.observation_id,
    record.successor_observation.observation_id, record.successor_belief.belief_id,
  ])])), resultRecordRefs);
  const invalidOutcomePublication = pythonRun(wrongOutcomeRehashed);
  assert.equal(invalidOutcomePublication.status, 2, invalidOutcomePublication.stderr);
  assert.equal(invalidOutcomePublication.stdout, '');
  const forgedOrigin = structuredClone(envelope);
  forgedOrigin.origin.kind = 'fresh_episode';
  const forgedOriginRehashed = reorigin(forgedOrigin);
  const forgedOriginBefore = structuredClone(forgedOriginRehashed);
  assert.throws(() => validatePipelineEpisodeEvidence(forgedOriginRehashed, result.records, evidenceExpectation(result)), /origin/);
  assert.deepEqual(forgedOriginRehashed, forgedOriginBefore, 'rejected origin tamper cannot mutate its candidate');
  assert.equal(envelope.evidence_id, resultEvidenceId);
  assert.deepEqual(result.transition_ids, resultTransitionIds);
  assert.deepEqual(Object.fromEntries(PLAYERS.map((player) => [player, result.records[player].map((record) => [
    record.transition.transition_id, record.input_observation.observation_id,
    record.successor_observation.observation_id, record.successor_belief.belief_id,
  ])])), resultRecordRefs);
  const invalidOriginPublication = pythonRun(forgedOriginRehashed);
  assert.equal(invalidOriginPublication.status, 2, invalidOriginPublication.stderr);
  assert.equal(invalidOriginPublication.stdout, '');
});

test('resumed terminal closure needs a validated predecessor chain to claim original initial coverage', async () => {
  const complete = await runPipelineEpisode({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  assert.equal(complete.status, 'completed');
  assert.ok(complete.evidence_envelope);
  const predecessorCommitCount = complete.evidence_envelope.commits.length - 1;
  assert.ok(predecessorCommitCount > 0);

  const linkedSession = await createPipelineIntegrationSession({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  const predecessor = await advanceSessionFromEpisode(linkedSession, complete, predecessorCommitCount);
  const linked = await continuePipelineEpisode(linkedSession, { predecessor_evidence: predecessor });
  assert.equal(linked.status, 'completed');
  assert.equal(linked.evidence_envelope?.commits.length, 1);
  assert.deepEqual(linked.evidence_envelope?.closure?.predecessor, predecessor);
  assert.equal(linked.evidence_envelope?.closure?.origin_coverage, 'original_initial_requests');
  assert.equal(linked.evidence_envelope?.closure?.complete_capture, true);
  assert.equal(linked.faithful_complete_episode, true);
  const linkedPublication = pythonRun(linked);
  assert.equal(linkedPublication.status, 0, linkedPublication.stderr);
  assert.equal(JSON.parse(linkedPublication.stdout).length, 2);

  const segmentSession = await createPipelineIntegrationSession({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  await advanceSessionFromEpisode(segmentSession, complete, predecessorCommitCount);
  const unlinked = await continuePipelineEpisode(segmentSession);
  assert.equal(unlinked.status, 'completed');
  assert.equal(unlinked.evidence_envelope?.closure?.origin_coverage, 'segment_only');
  assert.equal(unlinked.evidence_envelope?.closure?.predecessor, null);
  assert.equal(unlinked.evidence_envelope?.closure?.complete_capture, false);
  const unlinkedPublication = pythonRun(unlinked);
  assert.equal(unlinkedPublication.status, 0, unlinkedPublication.stderr);
  assert.equal(JSON.parse(unlinkedPublication.stdout).length, 2);

  const brokenOrigin = structuredClone(predecessor);
  brokenOrigin.commits.at(-1)!.boundary.perspectives.p1.event_cursor++;
  const { evidence_id: _id, ...partial } = brokenOrigin;
  const forgedPredecessor = sealPipelineEpisodeEvidence(partial);
  const unchangedSession = await createPipelineIntegrationSession({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  await advanceSessionFromEpisode(unchangedSession, complete, predecessorCommitCount);
  const before = summarizeEpisodeBoundary(unchangedSession.boundary);
  await assert.rejects(
    continuePipelineEpisode(unchangedSession, { predecessor_evidence: forgedPredecessor }),
    /cursor must equal its normalized protocol prefix length/,
  );
  assert.deepEqual(summarizeEpisodeBoundary(unchangedSession.boundary), before, 'invalid predecessor must not advance the committed session');
  await unchangedSession.close();
});

for (const [limit, code] of [['max_transitions', 'transition-budget'], ['max_attempts', 'attempt-budget']] as const) {
  test(`${limit} stops after one committed transition without duplicate records`, async () => {
    const result = await runPipelineEpisode({ ...CONFIG, limits: { [limit]: 1 } });
    assert.equal(result.status, 'truncated');
    assert.equal(result.stop.code, `episode/v1/${code}`);
    assert.equal(result.counts.attempts, 1); assert.equal(result.counts.committed_transitions, 1);
    assertRecords(result);
  });
}

test('natural Arena Trap rejection retries a different current-request tuple and preserves control identity', async () => {
  const config = { ...CONFIG, seed: [46, 101, 202, 303] };
  const session = await createPipelineIntegrationSession(config);
  const control = await createPipelineIntegrationSession(config);
  for (const s of [session, control]) {
    await s.step({ p1: choose(s.boundary, 'p1', 'switch 3'), p2: choose(s.boundary, 'p2', 'switch 6') });
  }
  const before = summarizeEpisodeBoundary(session.boundary);
  const result = await continuePipelineEpisode(session, {
    limits: { max_transitions: 1 }, policy_id: 'arena-trap-regression/v1',
    action_order: (o) => {
      const legal = o.request!.legal_actions;
      const first = o.perspective === 'p2' ? legal.actions.find((a) => a?.choice === 'switch 2')?.index : undefined;
      return first === undefined ? legal.available_indices : [first, ...legal.available_indices.filter((i) => i !== first)];
    },
  });
  const expected = await control.step(); await control.close();
  assert.equal(result.status, 'truncated'); assert.equal(result.stop.code, 'episode/v1/transition-budget');
  assert.equal(result.counts.rejected_candidates, 1); assert.equal(result.counts.attempts, 2);
  assert.equal(result.counts.rejections_at_final_boundary, 0);
  assert.deepEqual(result.initial_boundary, before);
  assert.equal(result.transition_ids[0], expected.transition_id);
  assertRecords(result);
  assert.throws(() => session.boundary, /closed/);
});

for (const max_attempts of [10, 2]) {
  test(`controlled rejections stop at ${max_attempts === 10 ? 'default three per boundary' : 'episode attempt cap'}`, async () => {
    const session = await createPipelineIntegrationSession(CONFIG);
    const before = session.boundary;
    const tried: string[] = [];
    session.step = async (actions) => {
      assert.equal(session.boundary, before);
      tried.push(JSON.stringify(actions));
      throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled rejection');
    };
    const r = await continuePipelineEpisode(session, { limits: { max_attempts } });
    assert.equal(r.stop.code, max_attempts === 10 ? 'episode/v1/rejection-limit' : 'episode/v1/attempt-budget');
    assert.equal(r.status, 'truncated'); assert.equal(r.counts.attempts, Math.min(3, max_attempts));
    assert.equal(new Set(tried).size, tried.length);
    assert.equal(r.counts.rejected_candidates, tried.length);
    assert.deepEqual(r.initial_boundary, r.final_boundary); assertRecords(r);
  });
}

test('episode attempt budget counts rejections and successes without resetting after commit', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const original = session.step.bind(session);
  let attempts = 0;
  session.step = async (actions) => {
    if (++attempts === 1) throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled once');
    return original(actions);
  };
  const r = await continuePipelineEpisode(session, { limits: { max_attempts: 3 } });
  assert.equal(r.stop.code, 'episode/v1/attempt-budget');
  assert.equal(r.counts.attempts, 3); assert.equal(r.counts.committed_transitions, 2);
  assert.equal(r.counts.rejected_candidates, 1); assert.equal(r.counts.rejections_at_final_boundary, 0);
  assertRecords(r);
});

test('cancellation is observed at committed boundaries including after an in-flight commit', async () => {
  const pre = new AbortController(); pre.abort();
  const cancelled = await runPipelineEpisode({ ...CONFIG, signal: pre.signal });
  assert.equal(cancelled.stop.code, 'episode/v1/cancelled'); assert.equal(cancelled.counts.attempts, 0);
  const session = await createPipelineIntegrationSession(CONFIG);
  const signal = new AbortController();
  const original = session.step.bind(session);
  session.step = async (a) => { const result = await original(a); signal.abort(); return result; };
  const r = await continuePipelineEpisode(session, { signal: signal.signal });
  assert.equal(r.stop.code, 'episode/v1/cancelled'); assert.equal(r.counts.committed_transitions, 1);
  assertRecords(r);
});

test('controlled requestless boundary explicitly truncates without submitting or fabricating an action', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const synthetic = structuredClone(session.boundary);
  synthetic.kind = 'requestless';
  for (const p of PLAYERS) synthetic.perspectives[p].observation.request = null;
  Object.defineProperty(session, 'boundary', { get: () => synthetic });
  session.step = async () => { throw new Error('must not submit'); };
  const r = await continuePipelineEpisode(session);
  assert.equal(r.status, 'truncated'); assert.equal(r.stop.code, 'episode/v1/unsupported-boundary');
  assert.equal(r.counts.attempts, 0); assertRecords(r);
});

test('source-shaped Revival Blessing flag at a real force/wait boundary truncates before any attempt', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  while (session.boundary.kind === 'joint_actionable') await session.step();
  assert.equal(session.boundary.kind, 'one_sided_forced_switch');
  const getRequest = LocalBattleEnv.prototype.getRequest;
  try {
    LocalBattleEnv.prototype.getRequest = function (p) {
      const request = getRequest.call(this, p);
      if (request?.force_switch) request.raw = { side: { pokemon: [{ reviving: true }] } };
      return request;
    };
    const r = await continuePipelineEpisode(session);
    assert.equal(r.status, 'truncated'); assert.equal(r.stop.code, 'episode/v1/unsupported-revival-blessing');
    assert.equal(r.counts.attempts, 0); assertRecords(r);
  } finally { LocalBattleEnv.prototype.getRequest = getRequest; await session.close(); }
});

for (const testCase of [
  { record: '|nothing|', status: 'truncated', stop: 'episode/v1/unsupported-protocol' },
  { record: '|-singlemove|p1a: Pikachu|Glaive Rush', status: 'failed', stop: 'episode/v1/execution-failed' },
  { record: '|futuremechanic|opaque', status: 'truncated', stop: 'episode/v1/unsupported-protocol' },
  { record: '|turn|broken', status: 'failed', stop: 'episode/v1/execution-failed' },
  { record: '|-boost|bad ident|atk|1', status: 'failed', stop: 'episode/v1/execution-failed' },
] as const) {
  test(`controlled ${testCase.record} candidate output stops with no uncommitted records`, async () => {
    const session = await createPipelineIntegrationSession(CONFIG);
    const original = LocalBattleEnv.prototype.stepSeededTransition;
    try {
      LocalBattleEnv.prototype.stepSeededTransition = async function (r, o) {
        const result = await original.call(this, r, o); result.metadata.emitted_log_delta.push(testCase.record); return result;
      };
      const r = await continuePipelineEpisode(session);
      assert.equal(r.status, testCase.status);
      assert.equal(r.stop.code, testCase.stop);
      assert.equal(r.counts.attempts, 1); assert.equal(r.counts.rejected_candidates, 0);
      assert.deepEqual(r.initial_boundary, r.final_boundary); assertRecords(r);
    } finally { LocalBattleEnv.prototype.stepSeededTransition = original; await session.close(); }
  });
}

test('simulator failure after a valid commit retains only committed records and final lineage', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const original = LocalBattleEnv.prototype.stepSeededTransition;
  let calls = 0;
  try {
    LocalBattleEnv.prototype.stepSeededTransition = async function (r, o) {
      if (++calls === 2) this.markError(new Error('controlled simulator error'));
      return original.call(this, r, o);
    };
    const r = await continuePipelineEpisode(session);
    assert.equal(r.status, 'failed'); assert.equal(r.stop.cause_code, 'settling/v1/simulator-error');
    assert.equal(r.counts.attempts, 2); assert.equal(r.counts.committed_transitions, 1);
    assert.equal(r.final_boundary?.step_index, 1); assertRecords(r);
    assert.throws(() => session.boundary, /closed/);
  } finally { LocalBattleEnv.prototype.stepSeededTransition = original; await session.close(); }
});

test('initialization failure returns a versioned failed outcome with no committed boundary', async () => {
  const original = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = async () => { throw new SettlingError('stream-closed', 5000, 100000); };
    const r = await runPipelineEpisode(CONFIG);
    assert.equal(r.status, 'failed'); assert.equal(r.stop.cause_code, 'settling/v1/stream-closed');
    assert.equal(r.initial_boundary, null); assert.equal(r.final_boundary, null); assertRecords(r);
  } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
});

test('invalid budgets/policy fail explicitly; cleanup failure retains committed records', async () => {
  for (const max_attempts of [0, -1, Infinity, 0.5]) {
    const r = await runPipelineEpisode({ ...CONFIG, limits: { max_attempts } });
    assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/invalid-options');
    assert.equal(r.counts.attempts, 0); assert.equal(r.limits, null);
  }
  const badPolicy = await runPipelineEpisode({ ...CONFIG, action_order: () => [] });
  assert.equal(badPolicy.stop.code, 'episode/v1/invalid-options');
  const invalidOrder = await runPipelineEpisode({ ...CONFIG, policy_id: 'invalid/v1', action_order: () => [99] });
  assert.equal(invalidOrder.status, 'failed'); assert.equal(invalidOrder.counts.attempts, 0);
  const session = await createPipelineIntegrationSession(CONFIG);
  const close = session.close.bind(session);
  session.close = async () => { await close(); throw new Error('controlled cleanup error'); };
  const r = await continuePipelineEpisode(session, { limits: { max_transitions: 1 } });
  assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/cleanup-failed');
  assert.equal(r.counts.committed_transitions, 1); assertRecords(r);
});


test('invalid continuation options retain the existing committed origin and close its session', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  await session.step();
  const before = summarizeEpisodeBoundary(session.boundary);
  const r = await continuePipelineEpisode(session, { limits: { max_attempts: 0 } });
  assert.equal(r.status, 'failed'); assert.equal(r.stop.code, 'episode/v1/invalid-options');
  assert.deepEqual(r.initial_boundary, before); assert.deepEqual(r.final_boundary, before);
  assert.equal(r.counts.attempts, 0); assertRecords(r);
  assert.throws(() => session.boundary, /closed/);
});

test('rejection cap resets only on commit, while total rejection and attempt counts accumulate', async () => {
  const session = await createPipelineIntegrationSession(CONFIG);
  const step = session.step.bind(session);
  let attempts = 0;
  session.step = async (actions) => {
    if (++attempts === 1 || attempts === 3) throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled rejection at each origin');
    return step(actions);
  };
  const r = await continuePipelineEpisode(session, { limits: { max_transitions: 2, max_rejections_per_boundary: 2 } });
  assert.equal(r.stop.code, 'episode/v1/transition-budget');
  assert.equal(r.counts.attempts, 4); assert.equal(r.counts.rejected_candidates, 2);
  assert.equal(r.counts.rejections_at_final_boundary, 0); assertRecords(r);
});

// CE-08B controls exercise stop metadata around short, real v2 boundaries.
test('CE-08B v2 classified failures preserve cause and committed evidence', async () => {
  const cases = [
    ...(['timeout', 'message-limit', 'simulator-error', 'stream-closed', 'cancelled'] as const).map((code) => ({
      error: new SettlingError(code, 25, 100), status: 'failed', stop: 'settling-failed', cause: `settling/v1/${code}`,
    })),
    ...(['unresolved-protocol-alias', 'unsupported-protocol-record', 'unsupported-observable-protocol'] as const).map((code) => ({
      error: new PipelineIntegrationError(`pipeline/v1/${code}`, 'Unsupported raw protocol event: controlled', {record_index: 7}),
      status: 'truncated', stop: 'unsupported-protocol', cause: `pipeline/v1/${code}`,
    })),
    {error: new PipelineIntegrationError('pipeline/v1/unsupported-observable-protocol', 'Malformed controlled record', {record_index: 7}),
      status: 'failed', stop: 'execution-failed', cause: 'pipeline/v1/unsupported-observable-protocol'},
  ];
  for (const control of cases) {
    console.log(`CE-08B classified ${control.cause}/${control.status}`);
    const session = await createPipelineIntegrationSession({...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION});
    const before = session.boundary, frozen = structuredClone(before);
    session.step = async () => {throw control.error;};
    const result = await continuePipelineEpisode(session);
    assert.equal(result.status, control.status); assert.equal(result.stop.code, `episode/v1/${control.stop}`);
    assert.equal(result.stop.cause_code, control.cause);
    if (control.error instanceof PipelineIntegrationError) assert.equal((result.stop as any).cause_record_index, 7);
    assert.deepEqual(before, frozen); assert.deepEqual(result.initial_boundary, result.final_boundary);
    assert.equal(result.evidence_envelope!.closure!.complete_capture, false);
    validatePipelineEpisodeEvidence(result.evidence_envelope!, result.records, evidenceExpectation(result));
    assertRecords(result);
    const accepted = pythonRun(result); assert.equal(accepted.status, 0, accepted.stderr); assert.deepEqual(JSON.parse(accepted.stdout), []);
  }
});

test('CE-08B Python rejects contradictory stop classification atomically', async () => {
  const result = await runPipelineEpisode({...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION, limits: {max_transitions: 1}});
  const original = structuredClone(result);
  assert.equal(result.stop.code, 'episode/v1/transition-budget');
  const valid = pythonRun(result); assert.equal(valid.status, 0, valid.stderr); assert.equal(JSON.parse(valid.stdout).length, 2);
  for (const stop of ['episode/v1/transition-budget', 'episode/v1/invented-stop']) {
    const candidate = structuredClone(result); candidate.status = 'failed'; candidate.stop.code = stop;
    // Execution metadata is outside canonical envelope identities; all actor joins remain exactly valid.
    assert.deepEqual(candidate.evidence_envelope, original.evidence_envelope);
    validatePipelineEpisodeEvidence(candidate.evidence_envelope!, candidate.records, evidenceExpectation(candidate));
    const frozen = structuredClone(candidate), rejected = pythonRun(candidate);
    assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /episode stop classification/);
    assert.deepEqual(candidate, frozen); assert.deepEqual(result, original);
    const compact = pythonPublicationSweep(candidate), compactFrozen = structuredClone(compact);
    const bulkRejected = pythonRun(compact);
    assert.equal(bulkRejected.status, 2, bulkRejected.stderr); assert.equal(bulkRejected.stdout, '');
    assert.match(bulkRejected.stderr, /episode stop classification/); assert.deepEqual(compact, compactFrozen);
  }
  for (const counts of [
    {...original.counts, attempts: -1},
    {...original.counts, rejections_at_final_boundary: 1},
    {...original.counts, attempts: original.counts.attempts + 2},
    {...original.counts, committed_transitions: 0},
  ]) {
    const candidate = {...structuredClone(original), counts}, frozen = structuredClone(candidate);
    const rejected = pythonRun(candidate);
    assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /episode (counter|committed transition count)/);
    assert.deepEqual(candidate, frozen); assert.deepEqual(result, original);
  }

});

test('CE-08B v2 cancellation and exhaustive rejections retain incomplete actor-free evidence', async () => {
  const unsupported = await runPipelineEpisode({...CONFIG, format: 'gen8randombattle'});
  assert.equal(unsupported.stop.code, 'episode/v1/unsupported-format'); assert.equal(unsupported.initial_boundary, null);
  const unpublished = pythonRun(unsupported); assert.equal(unpublished.status, 2); assert.equal(unpublished.stdout, '');
  for (const mode of ['cancelled', 'action-exhausted', 'after-commit'] as const) {
    console.log(`CE-08B bounded ${mode}`);
    const session = await createPipelineIntegrationSession({...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION});
    const before = session.boundary, frozen = structuredClone(before), signal = new AbortController();
    const step = session.step.bind(session), tried = new Set<string>();
    const tuples = PLAYERS.reduce((n, p) => n * before.perspectives[p].observation.request!.legal_actions.available_indices.length, 1);
    if (mode === 'cancelled') signal.abort();
    if (mode === 'after-commit') session.step = async (actions) => {const commit = await step(actions); signal.abort(); return commit;};
    if (mode === 'action-exhausted') session.step = async (actions) => {
      const key = JSON.stringify(actions); assert.ok(!tried.has(key)); tried.add(key);
      throw new PipelineIntegrationError('pipeline/v1/rejected-action', 'controlled rejection');
    };
    const result = await continuePipelineEpisode(session, {signal: signal.signal,
      limits: {max_attempts: tuples + 1, max_rejections_per_boundary: tuples + 1}});
    assert.equal(result.stop.code, `episode/v1/${mode === 'after-commit' ? 'cancelled' : mode}`);
    assert.equal(result.counts.committed_transitions, mode === 'after-commit' ? 1 : 0);
    if (mode === 'action-exhausted') assert.equal(tried.size, tuples);
    assert.deepEqual(before, frozen); assert.equal(result.evidence_envelope!.closure!.complete_capture, false); assertRecords(result);
    const accepted = pythonRun(result); assert.equal(accepted.status, 0, accepted.stderr);
    assert.equal(JSON.parse(accepted.stdout).length, mode === 'after-commit' ? 2 : 0);
  }
});

test('CE-08B cleanup preserves preceding diagnostics and terminal precedence', async () => {
  for (const mode of ['cancelled', 'cancelled-after-commit', 'error', 'terminal', 'completed'] as const) {
    console.log(`CE-08B cleanup ${mode}`);
    const signal = new AbortController();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    let battle: Battle | undefined;
    if (mode === 'terminal' || mode === 'completed') {
      battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
      battle.setPlayer('p1', {name: 'One', team: Teams.import('Snorlax\nLevel: 100\nAbility: Immunity\n- Body Slam')!});
      battle.setPlayer('p2', {name: 'Two', team: Teams.import('Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash')!});
      const snapshot = structuredClone(battle.toJSON());
      LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    }
    let session;
    try {session = await createPipelineIntegrationSession({...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION});}
    finally {LocalBattleEnv.prototype.resetWithOptions = reset; battle?.destroy();}
    const before = session.boundary, frozen = structuredClone(before), step = session.step.bind(session), close = session.close.bind(session);
    if (mode !== 'completed') session.close = async () => {await close(); throw new Error('private cleanup detail must not escape');};
    if (mode === 'cancelled') signal.abort();
    if (mode === 'error') {
      let calls = 0;
      session.step = async (actions) => {
        if (++calls === 1) return step(actions);
        throw new PipelineIntegrationError('pipeline/v1/unsupported-observable-protocol', 'Malformed private detail', {record_index: 9});
      };
    }
    if (mode === 'terminal' || mode === 'completed' || mode === 'cancelled-after-commit') session.step = async (actions) => {const commit = await step(actions); signal.abort(); return commit;};
    const result = await continuePipelineEpisode(session, {signal: signal.signal, limits: {max_transitions: mode === 'error' ? 2 : 1, max_attempts: mode === 'error' ? 2 : 1}});
    assert.equal(result.status, mode === 'completed' ? 'completed' : 'failed');
    assert.equal(result.stop.code, mode === 'completed' ? 'episode/v1/terminal' : 'episode/v1/cleanup-failed');
    if (mode !== 'completed') assert.equal(result.stop.cause_code, mode === 'error' ? 'pipeline/v1/unsupported-observable-protocol'
      : `episode/v1/${mode === 'cancelled-after-commit' ? 'cancelled' : mode}`);
    if (mode === 'error') assert.equal((result.stop as any).cause_record_index, 9);
    assert.ok(!JSON.stringify(result.stop).includes('private'));
    assert.deepEqual(before, frozen); assertRecords(result); assert.equal(result.faithful_complete_episode, result.status === 'completed' && result.evidence_envelope?.closure?.complete_capture === true);
    assert.equal(result.evidence_envelope!.closure!.complete_capture, false, 'unbound continuation cannot claim original coverage');
    if (mode === 'terminal' || mode === 'completed') {assert.equal(result.final_boundary!.kind, 'terminal'); assert.equal(result.counts.committed_transitions, 1);}
    const accepted = pythonRun(result); assert.equal(accepted.status, 0, accepted.stderr);
    assert.equal(JSON.parse(accepted.stdout).length, mode === 'cancelled' ? 0 : 2);
  }
});
