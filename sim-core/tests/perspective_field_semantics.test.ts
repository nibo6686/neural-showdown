import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { validateObservableBattleState } from '../src/belief_state';
import { LocalBattleEnv } from '../src/env_manager';
import { runPipelineEpisode, validatePipelineEpisodeFaithfulClaim } from '../src/pipeline_episode';
import { validatePipelineEpisodeEvidence } from '../src/pipeline_episode_evidence';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult, validatePipelineEpisodeRecordBundle } from '../src/pipeline_integration';
import { PLAYERS, type PlayerID } from '../src/types';
import { terminalOwnedItems, terminalOwnedRequests } from '../src/public_health';

const root = path.resolve(__dirname, '../../..');
const artifact = (name: string) => path.join(root, 'docs/planning', `perspective-fidelity-prompt5-${name}`);
const originalArtifact = (name: string) => path.join(root, 'docs/planning', `perspective-fidelity-prompt4-${name}`);
type Family = 'weather' | 'terrain' | 'pseudo_weather';
type Json = Record<string, any>;
const refs = ['schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase'];
const histories = ['observation_history', 'simulator_snapshot_history', 'transition_history', 'candidates', 'evidence', 'unresolved', 'contradictions'];
function canonical(value: any): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
const hash = (value: any) => createHash('sha256').update(canonical(value), 'utf8').digest('hex');
const without = (value: Json, keys: string[]) => Object.fromEntries(Object.entries(value).filter(([key]) => !keys.includes(key)));
const reference = (o: Json) => Object.fromEntries(refs.map(k => [k, o[k]]));
function walk(value: any, visit: (o: Json) => void): void {
  if (!value || typeof value !== 'object') return;
  if (!Array.isArray(value)) visit(value);
  for (const child of Object.values(value)) walk(child, visit);
}
function python(value: unknown, identityOnly = false) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  const result = spawnSync(process.env.PYTHON || 'python3', identityOnly ? ['-c', [
    'import sys', 'from neural.pipeline_json_wire import load_json',
    'from neural.ts_identity import verify_bundle_identities',
    'for bundle in load_json(sys.stdin): verify_bundle_identities(bundle)',
  ].join('\n')] : ['-m', 'neural.pipeline_record'], {
    cwd: root, env: {...env, PYTHONPATH: path.join(root, 'trainer/src')},
    input: JSON.stringify(value), encoding: 'utf8', timeout: 30_000, maxBuffer: 8 * 1024 * 1024,
  });
  assert.equal(result.error, undefined, `unresolved subprocess: ${result.error?.message}`);
  assert.equal(result.signal, null);
  return result;
}
function pythonObservation(value: unknown) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  const result = spawnSync(process.env.PYTHON || 'python3', ['-c', [
    'import sys', 'from neural.pipeline_json_wire import load_json',
    'from neural.pipeline_record import _prefix, _validate_episode_observation',
    'from neural.ts_identity import verify_observation', 'from neural.typed_state import validate_public_typed_state',
    'o = load_json(sys.stdin)', 'verify_observation(o, "compatibility observation")',
    'try:',
    ' if o["schema_version"] == "observable-battle-state/v2": _validate_episode_observation(o, o["perspective"], o["battle_id"], "compatibility observation")',
    ' else: _prefix(o, "compatibility observation"); validate_public_typed_state(o)',
    'except ValueError as error: print(str(error), file=sys.stderr); sys.exit(2)',
  ].join('\n')], {cwd: root, env: {...env, PYTHONPATH: path.join(root, 'trainer/src')},
    input: JSON.stringify(value), encoding: 'utf8', timeout: 30_000});
  assert.equal(result.error, undefined); assert.equal(result.signal, null);
  return result;
}
function sealBundle(bundle: Json): void {
  const changed = new Map<string, Json>();
  for (const which of ['input', 'successor']) {
    const o = bundle[`${which}_observation`], old = o.observation_id;
    o.observation_id = `obs-${hash(without(o, ['observation_id', 'protocol_prefix']))}`;
    changed.set(old, reference(o));
  }
  for (const which of ['input', 'successor']) {
    const b = bundle[`${which}_belief`], o = bundle[`${which}_observation`];
    b.observation = reference(o);
    b.observation_history = b.observation_history.map((ref: Json) => changed.get(ref.observation_id) || ref);
    if (which === 'successor') {
      b.parent_belief_id = bundle.input_belief.belief_id;
      b.transition_lineage.input_observation_id = bundle.input_observation.observation_id;
      b.transition_lineage.output_observation_id = o.observation_id;
    }
    b.belief_id = `belief-${hash(without(b, ['belief_id']))}`;
  }
}
function expectation(r: Json): any {
  return {run_id: r.run_id, battle_id: r.battle_id, ruleset: r.ruleset, policy_id: r.policy_id,
    limits: r.limits, origin_kind: r.evidence_envelope.origin.kind, initial_boundary: r.initial_boundary};
}
function compact(r: Json) {
  const beliefs = new Map<string, Json>(), records: Json = {p1: [], p2: []};
  for (const player of PLAYERS) for (const b of r.records[player]) {
    for (const belief of [b.input_belief, b.successor_belief]) {
      if (beliefs.has(belief.belief_id)) assert.deepEqual(beliefs.get(belief.belief_id), belief);
      beliefs.set(belief.belief_id, belief);
    }
    records[player].push({transition_id: b.transition.transition_id, action: b.action,
      input_belief_id: b.input_belief.belief_id, successor_belief_id: b.successor_belief.belief_id});
  }
  // Full arrays are a supported compact encoding; no duplicate episode harness
  // or history-delta algorithm is needed to exercise this actual publication form.
  return {schema_version: 'pipeline-episode-publication-sweep/v1',
    result: without(r, ['records', 'evidence_envelope']), evidence_envelope: r.evidence_envelope, records,
    beliefs: [...beliefs.values()].map(b => ({belief_id: b.belief_id, base_belief_id: null,
      fields: without(b, ['belief_id', 'source_protocol_prefix', ...histories]),
      arrays: Object.fromEntries(histories.map(k => [k, {mode: 'full', items: b[k]}]))}))};
}

// Recompute every affected identity from JSON, without validator/projection
// helpers. A field does not enter the simulator transition digest: its inputs
// are snapshot fingerprints, actions, seed, revision and step (transition.ts).
function attack(source: Json, oldObservation: string, mutate: (field: Json) => void): Json {
  const r = structuredClone(source), obs = new Map<string, Json>();
  walk(r, o => {
    if (!o.schema_version?.startsWith('observable-battle-state/') || !o.view) return;
    const old = o.observation_id;
    if (!obs.has(old)) {
      const updated = structuredClone(o);
      if (old === oldObservation) mutate(updated.view.field);
      updated.observation_id = `obs-${hash(without(updated, ['observation_id', 'protocol_prefix']))}`;
      obs.set(old, updated);
    }
  });
  walk(r, o => {
    for (const key of ['observation_id', 'input_observation_id', 'output_observation_id']) {
      const updated = obs.get(o[key]);
      if (!updated) continue;
      if (key === 'observation_id' && o.view) Object.assign(o, structuredClone(updated));
      else o[key] = updated.observation_id;
    }
  });
  const beliefs = new Map<string, Json>(), updated = new Map<string, string>();
  walk(r, o => {if (o.schema_version === 'belief-state/v1') {
    assert.deepEqual(o.evidence, [], 'fixture has no nested evidence requiring resealing');
    if (beliefs.has(o.belief_id)) assert.deepEqual(beliefs.get(o.belief_id), o);
    beliefs.set(o.belief_id, o);
  }});
  const seal = (id: string): string => {
    if (updated.has(id)) return updated.get(id)!;
    const b = structuredClone(beliefs.get(id)!); assert.ok(b);
    if (b.parent_belief_id) b.parent_belief_id = seal(b.parent_belief_id);
    const next = `belief-${hash(without(b, ['belief_id']))}`;
    updated.set(id, next); return next;
  };
  for (const id of beliefs.keys()) seal(id);
  walk(r, o => {
    for (const key of ['belief_id', 'parent_belief_id']) if (updated.has(o[key])) o[key] = updated.get(o[key]);
  });
  r.run_id = `episode-${createHash('sha256').update(JSON.stringify({schema: 'pipeline-episode/v1',
    battle_id: r.battle_id, format: r.ruleset, policy: r.policy_id, limits: r.limits, initial_boundary: r.initial_boundary})).digest('hex')}`;
  const e = r.evidence_envelope;
  e.run_id = r.run_id;
  e.origin.origin_id = `episode-origin-${hash({schema_version: e.origin.schema_version, run_id: e.run_id,
    battle_id: e.battle_id, ruleset: e.ruleset, source_ref: e.source_ref, kind: e.origin.kind, boundary: e.origin.boundary})}`;
  for (const commit of e.commits) commit.origin_id = e.origin.origin_id;
  e.evidence_id = `episode-evidence-${hash(without(e, ['evidence_id']))}`;
  return r;
}
function checkJoins(r: Json, original: Json) {
  const e = r.evidence_envelope;
  assert.equal(e.evidence_id, `episode-evidence-${hash(without(e, ['evidence_id']))}`);
  assert.deepEqual(r.transition_ids, original.transition_ids, 'field is absent from transition identity inputs');
  for (const player of PLAYERS) {
    let previous = e.origin.boundary.perspectives[player];
    for (const [index, commit] of e.commits.entries()) {
      const b = r.records[player][index]; assert.ok(b);
      assert.deepEqual(b.input_observation, previous);
      assert.deepEqual(b.successor_observation, commit.boundary.perspectives[player]);
      assert.equal(commit.origin_id, e.origin.origin_id);
      for (const key of Object.keys(commit.transition)) assert.deepEqual(b.transition[key], commit.transition[key]);
      assert.deepEqual(b.transition, original.records[player][index].transition);
      for (const which of ['input', 'successor']) {
        const o = b[`${which}_observation`], belief = b[`${which}_belief`];
        assert.equal(o.observation_id, `obs-${hash(without(o, ['observation_id', 'protocol_prefix']))}`);
        assert.deepEqual(belief.observation, reference(o));
        assert.equal(belief.belief_id, `belief-${hash(without(belief, ['belief_id']))}`);
        assert.deepEqual(o.protocol_prefix, original.records[player][index][`${which}_observation`].protocol_prefix);
        assert.deepEqual(o.request, original.records[player][index][`${which}_observation`].request);
      }
      assert.equal(b.successor_belief.parent_belief_id, b.input_belief.belief_id);
      assert.deepEqual(b.successor_belief.observation_history.slice(0, b.input_belief.observation_history.length), b.input_belief.observation_history);
      const lineage = b.successor_belief.transition_lineage;
      assert.equal(lineage.input_observation_id, b.input_observation.observation_id);
      assert.equal(lineage.output_observation_id, b.successor_observation.observation_id);
      previous = b.successor_observation;
    }
    for (const [which, b] of [['initial', r.records[player][0]], ['final', r.records[player].at(-1)]] as const) {
      const at = which === 'initial' ? 'input' : 'successor';
      assert.equal(r[`${which}_boundary`].perspectives[player].observation_id, b[`${at}_observation`].observation_id);
      assert.equal(r[`${which}_boundary`].perspectives[player].belief_id, b[`${at}_belief`].belief_id);
    }
    if (e.closure.terminal) assert.equal(e.closure.terminal.final_boundary.perspectives[player].observation_id, previous.observation_id);
  }
  const verified = python([...r.records.p1, ...r.records.p2], true);
  assert.equal(verified.status, 0, verified.stderr); assert.equal(verified.stdout, '');
}

type Truth = {value: string | null | string[]; writers: string[]};
function fixture(family: Family, terminal: boolean): {battle: Battle; ledger: Truth[]; choices: string[][]} {
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  const team = (s: string) => Teams.import(s)!;
  const bomb = 'Bomb (Snorlax)\nLevel: 100\nAbility: Thick Fat\n- Splash\n- Explosion';
  if (family === 'weather') {
    battle.setPlayer('p1', {name: 'One', team: team(`Sun (Ninetales)\n${terminal ? 'Level: 1\n' : ''}Ability: Drought\n- Rain Dance\n- Splash`)});
    battle.setPlayer('p2', {name: 'Two', team: team(terminal ? bomb : 'Foe (Eevee)\nAbility: Run Away\n- Splash')});
    const sun = '|-weather|SunnyDay|[from] ability: Drought|[of] p1a: Sun';
    if (terminal) return {battle, choices: [['move 2', 'move 2']], ledger: [{value: 'sunnyday', writers: [sun]}, {value: 'sunnyday', writers: [sun]}]};
    return {battle, choices: [['move 1', 'move 1'], ...Array.from({length: 4}, () => ['move 2', 'move 1']), ['move 1', 'move 1']],
      ledger: [{value: 'sunnyday', writers: [sun]}, ...Array.from({length: 4}, () => ({value: 'raindance', writers: [sun, '|-weather|RainDance']})),
        {value: 'none', writers: [sun, '|-weather|RainDance', '|-weather|none']}, {value: 'raindance', writers: [sun, '|-weather|RainDance', '|-weather|none', '|-weather|RainDance']}]};
  }
  if (family === 'terrain') {
    battle.setPlayer('p1', {name: 'One', team: team(`Pin (Pincurchin)\n${terminal ? 'Level: 1\n' : ''}Ability: Electric Surge\n- Splash${terminal ? '' : '\n\nGrass (Rillaboom)\nAbility: Grassy Surge\n- Splash'}`)});
    battle.setPlayer('p2', {name: 'Two', team: team(terminal ? bomb : 'Clearer (Azumarill)\nAbility: Huge Power\n- Ice Spinner\n- Splash')});
    const electric = '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin';
    const grass = '|-fieldstart|move: Grassy Terrain|[from] ability: Grassy Surge|[of] p1a: Grass';
    if (terminal) return {battle, choices: [['move 1', 'move 2']], ledger: [{value: 'electricterrain', writers: [electric]}, {value: 'electricterrain', writers: [electric]}]};
    return {battle, choices: [['switch 2', 'move 2'], ['move 1', 'move 1'], ['switch 2', 'move 2']],
      ledger: [{value: 'electricterrain', writers: [electric]}, {value: 'grassyterrain', writers: [electric, grass]},
        {value: null, writers: [electric, grass, '|-fieldend|move: Grassy Terrain']},
        {value: 'electricterrain', writers: [electric, grass, '|-fieldend|move: Grassy Terrain', electric]}]};
  }
  battle.setPlayer('p1', {name: 'One', team: team(`Room (Slowbro-Galar)\n${terminal ? 'Level: 1\n' : ''}Ability: Regenerator\n- Trick Room\n- Splash`)});
  battle.setPlayer('p2', {name: 'Two', team: team(terminal ? bomb : 'Foe (Eevee)\nAbility: Run Away\n- Splash')});
  const start = '|-fieldstart|move: Trick Room|[of] p1a: Room', end = '|-fieldend|move: Trick Room';
  if (terminal) {
    return {battle, choices: [['move 1', 'move 1'], ['move 2', 'move 2']],
      ledger: [{value: [], writers: []}, {value: ['trickroom'], writers: [start]}, {value: ['trickroom'], writers: [start]}]};
  }
  return {battle, choices: Array.from({length: 3}, () => ['move 1', 'move 1']),
    ledger: [{value: [], writers: []}, {value: ['trickroom'], writers: [start]}, {value: [], writers: [start, end]}, {value: ['trickroom'], writers: [start, end, start]}]};
}
async function capture(family: Family, terminal: boolean) {
  const {battle, ledger, choices} = fixture(family, terminal), snapshot = structuredClone(battle.toJSON());
  const reset = LocalBattleEnv.prototype.resetWithOptions, serialize = LocalBattleEnv.prototype.serializeBattle;
  let terminalSnapshot: any, r: any;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function(options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    LocalBattleEnv.prototype.serializeBattle = function() {const s = serialize.call(this); if (s.ended) terminalSnapshot = structuredClone(s); return s;};
    r = await runPipelineEpisode({battle_id: `field-proof-${family}-${terminal ? 'terminal' : 'lifecycle'}`, format: 'gen9randombattle', seed: [1,2,3,4],
      observation_schema_version: 'observable-battle-state/v2', limits: {max_transitions: choices.length}, policy_id: 'field-proof/v1',
      action_order(o) {
        const boundary = Math.max(0, o.view.turn - (snapshot as any).turn);
        const choice = choices[boundary]?.[o.perspective === 'p1' ? 0 : 1];
        const action = o.request!.legal_actions.actions.find(a => a?.choice === choice);
        assert.ok(action, `choice ${choice} at turn ${o.view.turn}`);
        return [action.index, ...o.request!.legal_actions.available_indices.filter(i => i !== action.index)];
      }});
  } finally {LocalBattleEnv.prototype.resetWithOptions = reset; LocalBattleEnv.prototype.serializeBattle = serialize; battle.destroy();}
  assert.equal(r.status, terminal ? 'completed' : 'truncated', JSON.stringify(r.stop));
  assert.equal(r.counts.committed_transitions, choices.length);
  const boundaries = [r.evidence_envelope.origin.boundary, ...r.evidence_envelope.commits.map((c: Json) => c.boundary)];
  assert.equal(boundaries.length, ledger.length);
  for (const [index, boundary] of boundaries.entries()) for (const player of PLAYERS) {
    const o = boundary.perspectives[player], truth = ledger[index];
    assert.deepEqual(o.view.field[family], truth.value, `${family}/${index}/${player} independent truth`);
    let after = -1;
    for (const writer of truth.writers) {after = o.protocol_prefix.indexOf(writer, after + 1); assert.ok(after >= 0, `ordered public writer ${writer}`);}
  }
  if (terminal) {
    const env = new LocalBattleEnv(`field-terminal-restore-${family}`, 'gen9randombattle', [1,2,3,4]);
    try {
      assert.equal(terminalSnapshot.__neural_terminal_request_history.schema_version, 'terminal-request-history/v1');
      const restored = await env.resetFromSerialized(structuredClone(terminalSnapshot), {include_log_delta: true, include_wait_requests: true});
      const prefix = projectPipelineProtocolPrefix(restored.log_delta);
      const observations = projectPipelineStepResult(restored, `field-terminal-restore-${family}`, prefix, 'observable-battle-state/v2');
      for (const player of PLAYERS) {
        const o = boundaries.at(-1).perspectives[player]; assert.equal(o.request, null);
        assert.deepEqual(restored.views[player]!.field[family], ledger.at(-1)!.value);
        assert.equal(observations[player].request, null, 'restoration invents no requests');
        validateObservableBattleState(observations[player]);
        const forged = structuredClone(restored);
        if (family === 'pseudo_weather') forged.views[player]!.field.pseudo_weather = [];
        else forged.views[player]!.field[family] = family === 'weather' ? 'raindance' : 'grassyterrain';
        const unchanged = JSON.stringify(forged);
        assert.throws(() => projectPipelineStepResult(forged, `field-terminal-restore-${family}`, prefix, 'observable-battle-state/v2'), /Public field evidence mismatch/);
        assert.equal(JSON.stringify(forged), unchanged, 'failed restored projection never normalizes a forged value');
        assert.deepEqual(restored.views[player]!.field[family], ledger.at(-1)!.value, 'failed restored projection is immutable');
      }
    } finally {await env.close();}
  }
  return {r, ledger};
}
const results: Json[] = [];
function save() {fs.writeFileSync(artifact('results.json'), JSON.stringify(results, null, 2) + '\n');}
function tsOutcome(run: () => void) {try {run(); return 'accepted';} catch (error) {return String(error);}}
function probe(r: Json, player: PlayerID, recordIndex: number, label: string, kind: string) {
  const unchanged = JSON.stringify(r);
  const record = r.records[player][recordIndex];
  // Clone before bound validators: terminal authority is validation-local and
  // must not accidentally make a previously bound object a standalone proof.
  const tsObservations = ['input', 'successor'].map(which => tsOutcome(() => validateObservableBattleState(structuredClone(record[`${which}_observation`]))));
  const tsRecord = tsOutcome(() => validatePipelineEpisodeRecordBundle(record));
  const tsEpisode = tsOutcome(() => validatePipelineEpisodeEvidence(r.evidence_envelope, r.records, expectation(r)));
  const tsClaim = tsOutcome(() => {validatePipelineEpisodeFaithfulClaim(r as any);});
  for (const [form, payload] of [['ordinary', record], ['full', r], ['envelope', r.evidence_envelope], ['compact', compact(r)]] as const) {
    const out = python(payload), published = out.stdout.trim() ? JSON.parse(out.stdout) : null;
    const rows = published === null || form === 'envelope' ? [] : Array.isArray(published) ? published : [published];
    if (out.status === 0) {
      if (form === 'envelope') assert.equal(published.evidence_id, r.evidence_envelope.evidence_id, 'validation receipt joins resealed envelope');
      else assert.ok(rows.some(row => row.perspective === player && row.transition_id === record.transition.transition_id
        && row.observation_id === record.input_observation.observation_id && row.belief_id === record.input_belief.belief_id), 'published row joins resealed input');
    } else assert.equal(out.stdout, '', 'rejection must publish atomically');
    results.push({label, kind, form, tsRecord, tsEpisode, tsClaim, tsObservations,
      status: out.status, stdoutBytes: Buffer.byteLength(out.stdout), rows: rows.length, stderr: out.stderr});
    save();
  }
  assert.equal(JSON.stringify(r), unchanged, 'validation never mutates or repairs supplied fields');
}
test('V01 repaired: source controls and fully resealed false field values through actual publication', async () => {
  for (const family of ['weather', 'terrain', 'pseudo_weather'] as const) for (const terminal of [false, true]) {
    const {r, ledger} = await capture(family, terminal), original = structuredClone(r), label = `${family}/${terminal ? 'terminal' : 'lifecycle'}`;
    checkJoins(r, original);
    const controlsAt = results.length;
    for (const player of PLAYERS) probe(r, player, 0, `${label}/${player}/control`, 'control');
    if (r.records.p1.length > 1) for (const player of PLAYERS) probe(r, player, r.records[player].length - 1, `${label}/${player}/last-control`, 'control');
    const compactApplicable = terminal;
    assert.ok(results.slice(controlsAt).every(row => row.tsRecord === 'accepted' && row.tsEpisode === 'accepted'
      && (row.form === 'compact' && !compactApplicable
        ? row.status === 2 && row.stdoutBytes === 0 && /requires a validated original-to-terminal chain/.test(row.stderr)
        : row.status === 0)), JSON.stringify(results.slice(controlsAt)));
    assert.deepEqual(ledger, JSON.parse(fs.readFileSync(originalArtifact(`${family}-${terminal ? 'terminal' : 'lifecycle'}-ledger.json`), 'utf8')), 'preserved independent source ledger');
    fs.writeFileSync(artifact(`${family}-${terminal ? 'terminal' : 'lifecycle'}-ledger.json`), JSON.stringify(ledger, null, 2) + '\n');
    for (const player of PLAYERS) for (const which of ['input', 'successor']) {
      const index = which === 'input' ? 0 : r.records[player].length - 1;
      const o = r.records[player][index][`${which}_observation`];
      const value = family === 'weather' ? (o.view.field.weather === 'raindance' ? 'sunnyday' : 'raindance')
        : family === 'terrain' ? (o.view.field.terrain === 'electricterrain' ? 'grassyterrain' : 'electricterrain')
        : o.view.field.pseudo_weather.includes('trickroom') ? [] : ['trickroom'];
      const candidate = attack(r, o.observation_id, field => {field[family] = value;});
      checkJoins(candidate, r);
      assert.notDeepEqual(candidate.records[player][index][`${which}_observation`].view.field[family], o.view.field[family]);
      const before = results.length;
      probe(candidate, player, index, `${label}/${player}/${which}/false-value`, 'false-value');
      const observed = results.slice(before);
      assert.ok(observed.every(row => /Public field evidence mismatch/.test(row.tsRecord) && /Public field evidence mismatch/.test(row.tsEpisode)
        && row.tsObservations.some((outcome: string) => /Public field evidence mismatch/.test(outcome))
        && row.status === 2 && row.stdoutBytes === 0 && /Public field evidence mismatch/.test(row.stderr)), JSON.stringify(observed));
      // A failed validation must not leave authority usable by a later call.
      assert.match(tsOutcome(() => validatePipelineEpisodeRecordBundle(candidate.records[player][index])), /Public field evidence mismatch/);
      assert.equal(terminalOwnedItems(candidate.records[player][index].successor_observation.view), undefined, 'failure leaves no terminal item authority');
      assert.equal(terminalOwnedRequests(candidate.records[player][index].successor_observation.view), undefined, 'failure leaves no terminal request authority');
      assert.equal(tsOutcome(() => validatePipelineEpisodeRecordBundle(r.records[player][index])), 'accepted');
      if (!terminal && player === 'p1' && which === 'input') {
        fs.writeFileSync(artifact(`${family}-reproduction.json`), JSON.stringify(candidate.records[player][index], null, 2) + '\n');
      }
      if (terminal && player === 'p1' && which === 'successor') {
        fs.writeFileSync(artifact(`${family}-terminal-full-reproduction.json`), JSON.stringify(candidate, null, 2) + '\n');
        fs.writeFileSync(artifact(`${family}-terminal-compact-reproduction.json`), JSON.stringify(compact(candidate), null, 2) + '\n');
      }
    }
    if (!terminal) for (const mode of ['missing-field', 'extra-field']) {
      const o = r.records.p1[0].input_observation;
      const candidate = attack(r, o.observation_id, field => {if (mode === 'missing-field') delete field[family]; else field.unreviewed_field = 'trickroom';});
      checkJoins(candidate, r);
      const before = results.length; probe(candidate, 'p1', 0, `${label}/${mode}`, 'schema');
      assert.ok(results.slice(before).every(row => /fields are not exact/.test(row.tsRecord) && /fields are not exact/.test(row.tsEpisode)
        && row.status === 2 && row.stdoutBytes === 0 && /fields are not exact/.test(row.stderr)), JSON.stringify(results.slice(before)));
    }
    assert.deepEqual(r, original, 'controls remain immutable');
    console.log(`${label}: controls, 4 false-value attacks, terminal restoration=${terminal}; results persisted`);
  }
  assert.ok(results.filter(row => row.kind === 'control').every(row => row.tsRecord === 'accepted' && row.tsEpisode === 'accepted'));
  console.log(`V01 repaired regression: ${results.length} real publication invocations; false fields reject atomically.`);
});
for (const family of ['weather', 'terrain', 'pseudo_weather'] as const) {
  test(`V01 SAVED WITNESS: ${family} contradiction must reject before publication`, () => {
    const candidate = JSON.parse(fs.readFileSync(originalArtifact(`${family}-reproduction.json`), 'utf8'));
    const identities = python([candidate], true); assert.equal(identities.status, 0, identities.stderr);
    const out = python(candidate);
    assert.equal(out.status, 2, out.stderr);
    assert.equal(out.stdout, '');
    assert.match(out.stderr, /Public field evidence mismatch/);
  });
}

test('field evidence applies to real waiting/requestless reports and v1/v2 ordinary callers', async () => {
  const compatibility: Json[] = [];
  for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
    const {battle} = fixture('weather', false), snapshot = structuredClone(battle.toJSON()); battle.destroy();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function(options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
      session = await createPipelineIntegrationSession({battle_id: `field-compat-${version}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: version});
    } finally {LocalBattleEnv.prototype.resetWithOptions = reset;}
    try {
      const actions = Object.fromEntries(PLAYERS.map(player => {
        const request = session.boundary.perspectives[player].observation.request!;
        return [player, canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0])];
      })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
      const stepped = await session.step(actions);
      const committed = JSON.stringify(session.boundary);
      for (const player of PLAYERS) {
        const control = stepped.record_bundles[player];
        const valid = python(control); assert.equal(valid.status, 0, valid.stderr);
        assert.equal(control.input_observation.view.field.weather, 'sunnyday');
        assert.equal(control.successor_observation.view.field.weather, 'raindance');
        for (const which of ['input', 'successor']) {
          const forged: Json = structuredClone(control);
          forged[`${which}_observation`].view.field.weather = which === 'input' ? 'raindance' : 'sunnyday';
          sealBundle(forged);
          const identities = python([forged], true); assert.equal(identities.status, 0, identities.stderr);
          const unchanged = JSON.stringify(forged);
          assert.throws(() => validatePipelineEpisodeRecordBundle(forged as any), /Public field evidence mismatch/);
          const rejected = python(forged);
          assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, '');
          assert.match(rejected.stderr, /Public field evidence mismatch/);
          assert.equal(JSON.stringify(forged), unchanged);
          compatibility.push({version, player, which, status: rejected.status, stdoutBytes: Buffer.byteLength(rejected.stdout), stderr: rejected.stderr});
        }
      }
      assert.equal(JSON.stringify(session.boundary), committed);
    } finally {await session.close();}

    for (const submitted of PLAYERS) {
      const env = new LocalBattleEnv(`field-partial-${submitted}-${version}`, 'gen9randombattle', [1,2,3,4]);
      const restored = new LocalBattleEnv(`field-partial-restore-${submitted}-${version}`, 'gen9randombattle', [1,2,3,4]);
      const options = {include_wait_requests: true, include_possible_roles: false, include_log_delta: true};
      try {
        const initial = await env.resetFromSerialized(structuredClone(snapshot), options);
        const request = initial.requests[submitted]!;
        const action = canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
        const partial = await env.stepWithCanonicalOptions({[submitted]: action}, options);
        assert.equal(partial.requests[submitted], null);
        const replay = await restored.resetFromSerialized(env.serializeBattle(), options);
        assert.equal(replay.requests[submitted], null, 'restore retains consumed request absence');
        const prefix = projectPipelineProtocolPrefix(replay.log_delta);
        const states = projectPipelineStepResult(replay, `field-partial-${submitted}`, prefix, version);
        assert.equal(states[submitted].decision_availability.reason, 'requestless');
        for (const player of PLAYERS) {
          assert.equal(states[player].view.field.weather, 'sunnyday');
          validateObservableBattleState(states[player]);
          const valid = pythonObservation(states[player]); assert.equal(valid.status, 0, valid.stderr);
          const forged = structuredClone(states[player]); forged.view.field.weather = 'raindance';
          forged.observation_id = `obs-${hash(without(forged, ['observation_id', 'protocol_prefix']))}`;
          assert.throws(() => validateObservableBattleState(forged), /Public field evidence mismatch/);
          const rejected = pythonObservation(forged);
          assert.equal(rejected.status, 2); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public field evidence mismatch/);
          compatibility.push({version, player, state: states[player].decision_availability.reason, status: rejected.status, stdoutBytes: 0});
        }
        const unchanged = JSON.stringify(replay);
        const forged = structuredClone(replay); forged.views[submitted]!.field.weather = 'raindance';
        const forgedUnchanged = JSON.stringify(forged);
        assert.throws(() => projectPipelineStepResult(forged, `field-partial-${submitted}`, prefix, version), /Public field evidence mismatch/);
        assert.equal(JSON.stringify(forged), forgedUnchanged);
        assert.equal(JSON.stringify(replay), unchanged);
        for (const mutate of [(field: Json) => {delete field.weather;}, (field: Json) => {field.extra = true;},
          (field: Json) => {field.pseudo_weather = [1];}, (field: Json) => {field.side_conditions.self.extra = true;},
          (field: Json) => {field.side_conditions = {'opponent|self': {}};}]) {
          const malformed = structuredClone(replay); mutate(malformed.views[submitted]!.field);
          const before = JSON.stringify(malformed);
          assert.throws(() => projectPipelineStepResult(malformed, `field-partial-${submitted}`, prefix, version), /field fields are not exact|field values are malformed|side conditions are malformed/);
          assert.equal(JSON.stringify(malformed), before);
        }
      } finally {await env.close(); await restored.close();}
    }

    const waitingBattle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    waitingBattle.setPlayer('p1', {name: 'One', team: Teams.import('Sun (Ninetales)\nLevel: 1\nAbility: Drought\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash')!});
    waitingBattle.setPlayer('p2', {name: 'Two', team: Teams.import('Foe (Eevee)\nLevel: 100\nAbility: Run Away\n- Tackle')!});
    const waitingSnapshot = structuredClone(waitingBattle.toJSON()); waitingBattle.destroy();
    const env = new LocalBattleEnv(`field-wait-${version}`, 'gen9randombattle', [1,2,3,4]);
    try {
      const options = {include_wait_requests: true, include_possible_roles: false, include_log_delta: true};
      const initial = await env.resetFromSerialized(waitingSnapshot, options);
      const result = await env.stepWithOptions({p1: 'move 1', p2: 'move 1'}, options);
      assert.equal(result.requests.p2?.wait, true, 'real faint yields the opponent waiting request');
      const prefix = projectPipelineProtocolPrefix([...initial.log_delta, ...result.log_delta]);
      const states = projectPipelineStepResult(result, 'field-wait', prefix, version);
      assert.equal(states.p2.decision_availability.reason, 'waiting');
      const before = JSON.stringify(states);
      for (const player of PLAYERS) {
        validateObservableBattleState(states[player]);
        assert.equal(states[player].view.field.weather, 'sunnyday');
        const valid = pythonObservation(states[player]); assert.equal(valid.status, 0, valid.stderr);
        const forged = structuredClone(states[player]); forged.view.field.weather = 'raindance';
        forged.observation_id = `obs-${hash(without(forged, ['observation_id', 'protocol_prefix']))}`;
        assert.throws(() => validateObservableBattleState(forged), /Public field evidence mismatch/);
        const rejected = pythonObservation(forged);
        assert.equal(rejected.status, 2); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public field evidence mismatch/);
        compatibility.push({version, player, state: states[player].decision_availability.reason, status: rejected.status, stdoutBytes: 0});
      }
      assert.equal(JSON.stringify(states), before);
    } finally {await env.close();}
  }
  fs.writeFileSync(artifact('compatibility-results.json'), JSON.stringify(compatibility, null, 2) + '\n');
});
