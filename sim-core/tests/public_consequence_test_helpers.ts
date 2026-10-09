import { validatePipelineLinkedRecordBundle } from '../src/pipeline_integration';
import { projectPublicItems, projectPublicItemDispositions, projectPublicItemHistory } from '../src/public_item';
import { opponentPublicBoosts } from '../src/public_boosts';
import assert from 'node:assert/strict';
import {episodeEvidenceContentDigest as digest} from '../src/pipeline_episode_evidence';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { validateObservableBattleState } from '../src/belief_state';
import { projectPublicHealth } from '../src/public_health';
import { publicTeamIdent } from '../src/typed_state_lifecycle';

/** Complete synthetic grammar controls; source consequence controls never call this. */
export function completeSyntheticHealthView(view: any, prefix: readonly string[], perspective: string, request: any = null): void {
  const ensure = (target: string) => {
    const team = target.startsWith(perspective) ? 'self_team' : 'opponent_team';
    let row = view[team].find((p: any) => publicTeamIdent(p.ident) === target);
    if (!row) {
      row = {slot: view[team].length + 1, ident: target, name: target.split(': ')[1], species: 'Eevee',
        active: false, fainted: false, hp_text: '100/100', hp_ratio: 1, status: null,
        item: null, item_state: 'unknown', item_suppressed: false,
        ability: null, base_ability: null, ability_state: 'unknown', ability_suppressed: false,
        moves: [], revealed_moves: [], types: ['Normal'], boosts: {}, stats: {}, volatiles: [],
        possible_roles: [], possible_moves: [], possible_abilities: [], possible_tera_types: []};
      if (team === 'opponent_team') row.public_boosts = opponentPublicBoosts(prefix, target);
      view[team].push(row);
    }
    return row;
  };
  for (const [target, health] of Object.entries(projectPublicHealth(prefix))) Object.assign(ensure(target), health);
  for (const owner of request?.side || []) {
    const target = publicTeamIdent(owner.ident);
    const health = projectPublicHealth([`|switch|${target.replace(': ', 'a: ')}|Eevee|${owner.condition}`])[target];
    Object.assign(ensure(target), health, {active: !!owner.active && !health.fainted,
      item: owner.item || null, ...(owner.item ? {item_state: 'held'} : {}), ability: owner.ability || null});
  }
}

const referenceKeys = ['schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase'];

export function rehash(candidate: Record<string, any>): void {
  const references = new Map<string, Record<string, any>>();
  for (const which of ['input', 'successor']) {
    const observation = candidate[`${which}_observation`];
    const old = observation.observation_id;
    observation.observation_id = `obs-${digest(Object.fromEntries(Object.entries(observation).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key))))}`;
    references.set(old, Object.fromEntries(referenceKeys.map((key) => [key, observation[key]])));
  }
  for (const which of ['input', 'successor']) {
    const belief = candidate[`${which}_belief`];
    for (const reference of [belief.observation, ...belief.observation_history]) {
      const updated = references.get(reference.observation_id);
      if (updated) Object.assign(reference, updated);
    }
    for (const transition of [...belief.transition_history, ...(belief.transition_lineage ? [belief.transition_lineage] : [])]) {
      for (const key of ['input_observation_id', 'output_observation_id']) {
        const updated = references.get(transition[key]);
        if (updated) transition[key] = updated.observation_id;
      }
    }
    if (which === 'successor') belief.parent_belief_id = candidate.input_belief.belief_id;
    belief.belief_id = `belief-${digest(Object.fromEntries(Object.entries(belief).filter(([key]) => key !== 'belief_id')))}`;
  }
}

export function python(value: unknown, identityOnly = false) {
  const result = spawnSync(process.env.PYTHON || 'python3', identityOnly
    ? ['-c', 'import json,sys; from neural.ts_identity import verify_bundle_identities; verify_bundle_identities(json.load(sys.stdin))']
    : ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(value), encoding: 'utf8',
    timeout: 30_000, maxBuffer: 8 * 1024 * 1024,
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
  if (result.error || result.signal) result.stderr += `\nPython subprocess failed: ${result.error?.message || ''}; signal=${result.signal}; code=${(result.error as NodeJS.ErrnoException | undefined)?.code || ''}`;
  return result;
}

/** Fully rehashed result mutations, exercised on real source-engine actor bundles. */
export function assertPublicConsequenceTamperMatrix(bundle: unknown, targetName: string): void {
  const original = JSON.stringify(bundle);
  const valid = python(bundle);
  assert.equal(valid.status, 0, valid.stderr);
  const mutations: Record<string, (observation: any, row: any, team: string) => void> = {
    hp: (_o, row) => { row.hp_text = '25/100'; row.hp_ratio = .25; },
    status: (o, row) => { row.status = row.status === 'brn' ? 'par' : 'brn'; row.status_started_turn = o.view.turn; row.status_turns_public = 0; },
    fainted: (_o, row) => { row.fainted = !row.fainted; },
    active: (_o, row) => { row.active = !row.active; },
    'missing-hp': (_o, row) => { delete row.hp_text; },
    'missing-ratio': (_o, row) => { delete row.hp_ratio; },
    'missing-status': (_o, row) => { delete row.status; },
    'missing-faint': (_o, row) => { delete row.fainted; },
    'missing-row': (o, row, team) => { o.view[team] = o.view[team].filter((p: any) => p !== row); },
    'missing-team': (o, _row, team) => { delete o.view[team]; },
    'wrong-side': (o, row, team) => { o.view[team] = o.view[team].filter((p: any) => p !== row); if (team === 'self_team') row.public_boosts = opponentPublicBoosts(o.protocol_prefix, row.ident); o.view[team === 'self_team' ? 'opponent_team' : 'self_team'].push(row); },
    'duplicate-row': (o, row, team) => { o.view[team].push(structuredClone(row)); },
    'ability-name': (_o, row) => { row.ability = 'levitate'; },
    'missing-ability': (_o, row) => { delete row.ability; },
    'ability-suppression': (_o, row) => { row.ability_suppressed = !row.ability_suppressed; },
    'missing-suppression': (_o, row) => { delete row.ability_suppressed; },
    'owned-item': (_o, row) => { row.item = 'abilityshield'; },
    'private-slot': (o) => { o.view.pending_slots = {wish: {endingTurn: 3}}; },
  };
  for (const which of ['input', 'successor']) for (const [name, mutate] of Object.entries(mutations)) {
    const candidate = structuredClone(bundle) as Record<string, any>;
    const observation = candidate[`${which}_observation`];
    const team = observation.view.self_team.some((p: any) => p.name === targetName) ? 'self_team' : 'opponent_team';
    const row = observation.view[team].find((p: any) => p.name === targetName);
    if (!row) continue; // Incoming recipient may first become public at the successor.
    if (['ability-name', 'missing-ability', 'ability-suppression', 'missing-suppression', 'owned-item'].includes(name)
      && (team !== 'self_team' || !observation.request?.side.some((p: any) => p.ident === row.ident && p.ability))) continue;
    if (name === 'ability-name' && row.ability === 'levitate') continue;
    if (name === 'hp' && row.hp_ratio === .25) continue;
    mutate(observation, row, team);
    rehash(candidate);
    const identity = python(candidate, true);
    assert.equal(identity.status, 0, `${which}/${name} identities: ${identity.stderr}`);
    const unchanged = JSON.stringify(candidate);
    const abilityMutation = ['ability-name', 'missing-ability', 'ability-suppression', 'missing-suppression', 'owned-item'].includes(name);
    const semantic = name === 'owned-item' ? /Public item evidence mismatch/ : abilityMutation ? /Public ability evidence mismatch/ : name === 'private-slot'
      ? /fields are not exact|Private simulator slot/ : /Public health evidence mismatch/;
    assert.throws(() => validateObservableBattleState(observation), semantic, `${which}/${name}`);
    assert.equal(JSON.stringify(candidate), unchanged, 'TS rejection preserves the candidate');
    const rejected = python(candidate);
    assert.equal(rejected.status, 2, `${which}/${name}: ${rejected.stderr}`);
    assert.equal(rejected.stdout, '', `${which}/${name} must not publish`);
    assert.match(rejected.stderr, name === 'private-slot' ? /Private simulator slot/ : semantic);
  }
  assert.equal(JSON.stringify(bundle), original, 'rejections preserve the committed bundle');
  assert.equal(python(bundle).stdout, valid.stdout, 'valid source publication is unchanged');
}

export function assertRehashedUnsupportedGasRecord(bundle: unknown, record: string): void {
  for (const which of ['input', 'successor']) {
    const candidate = structuredClone(bundle) as Record<string, any>;
    if (which === 'input') {
      const at = candidate.input_observation.protocol_prefix.length;
      candidate.input_observation.protocol_prefix.push(record);
      candidate.successor_observation.protocol_prefix.splice(at, 0, record);
    } else candidate.successor_observation.protocol_prefix.push(record);
    for (const name of ['input', 'successor']) {
      const observation = candidate[`${name}_observation`];
      observation.event_cursor = observation.protocol_prefix.length;
      observation.protocol_prefix_hash = digest(observation.protocol_prefix);
      candidate[`${name}_belief`].source_protocol_prefix = [...observation.protocol_prefix];
    }
    rehash(candidate);
    assert.equal(python(candidate, true).status, 0);
    const unchanged = JSON.stringify(candidate);
    assert.throws(() => validateObservableBattleState(candidate[`${which}_observation`]), /dash_reveal source-proven domain/);
    assert.equal(JSON.stringify(candidate), unchanged);
    const rejected = python(candidate);
    assert.equal(rejected.status, 2, rejected.stderr);
    assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /dash_reveal source-proven domain/);
  }
}

function continuity(candidate: any) {
  return {
    predecessor: candidate.input_observation,
    before: {step_index: candidate.transition.step_index, branch_id: candidate.input_belief.simulator_snapshot.branch_id,
      state_fingerprint: candidate.input_belief.simulator_snapshot.state_fingerprint},
    transition: candidate.transition,
    after: {step_index: candidate.transition.step_index + 1, branch_id: candidate.successor_belief.simulator_snapshot.branch_id,
      state_fingerprint: candidate.successor_belief.simulator_snapshot.state_fingerprint},
  };
}

export const itemIdentityMatrixCounts = {ordinary: 0, fullResult: 0, envelope: 0, sweep: 0};

export function assertTerminalIdentityTamperMatrix(bundle: unknown): void {
  const original = JSON.stringify(bundle);
  const valid = python(bundle);
  assert.equal(valid.status, 0, valid.stderr);
  const standalone = structuredClone((bundle as any).successor_observation);
  assert.throws(() => validateObservableBattleState(standalone), /Public health/);
  const roundtrip = JSON.parse(original);
  assert.doesNotThrow(() => validatePipelineLinkedRecordBundle(roundtrip));
  for (const mutate of [
    (c: any) => {c.schema_version = 'foreign-bundle/v1';},
    (c: any) => {c.source_ref = 'sim-core://foreign';},
    (c: any) => {c.ruleset = 'gen8randombattle';},
    (c: any) => {c.transition.simulator_revision = 'foreign';},
    (c: any) => {c.transition.transition_id = 'transition-foreign';},
    (c: any) => {c.transition.acting_player = c.perspective;},
  ]) {
    const candidate = JSON.parse(original); mutate(candidate);
    const before = JSON.stringify(candidate);
    assert.throws(() => validatePipelineLinkedRecordBundle(candidate), /Linked record source\/schema\/action transition metadata/);
    assert.throws(() => validateObservableBattleState(candidate.successor_observation), /Public health/);
    assert.equal(JSON.stringify(candidate), before);
  }
  const mutations: Record<string, (candidate: any) => void> = {
    'alias-active': (c) => { for (const row of c.successor_observation.view.self_team) row.active = !row.active; },
    'missing-owner': (c) => { c.successor_observation.view.self_team.shift(); },
    'foreign-owner': (c) => { c.successor_observation.view.self_team[0].ident = 'p2: Foreign'; },
    'renamed-owner': (c) => { c.successor_observation.view.self_team[0].ident = `${c.perspective}: Disguise`; },
    'reordered-roster': (c) => { c.successor_observation.view.self_team.reverse(); },
    'changed-roster': (c) => { c.successor_observation.view.self_team[0].base_species = 'Pikachu'; },
    'terminal-owned-item': (c) => { c.successor_observation.view.self_team[0].item = c.successor_observation.view.self_team[0].item ? null : 'leftovers'; },
  };
  for (const [name, mutate] of Object.entries(mutations)) {
    const candidate = structuredClone(bundle) as any;
    mutate(candidate); rehash(candidate);
    itemIdentityMatrixCounts.ordinary++;
    assert.equal(python(candidate, true).status, 0, `${name} canonical identities`);
    const before = JSON.stringify(candidate);
    assert.throws(() => validatePipelineLinkedRecordBundle(candidate), /Public (health|item)/, name);
    assert.equal(JSON.stringify(candidate), before);
    const rejected = python(candidate);
    assert.equal(rejected.status, 2, `${name}: ${rejected.stderr}`);
    assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /Public (health|item)/);
  }
  for (const field of ['parent_branch_id', 'input_state_fingerprint', 'step_index']) {
    const candidate = JSON.parse(original), context = continuity(candidate);
    context.transition = {...context.transition, [field]: field === 'step_index' ? -1 : 'foreign'};
    assert.throws(() => (validateObservableBattleState as any)(candidate.successor_observation, context), /Public health/);
  }
  assert.equal(JSON.stringify(bundle), original);
}

/** Test-only startup batching: every CLI invocation parses a fresh JSON value and captures its own streams. */
export function assertFreshPythonRejections(candidates: Array<{candidate: unknown; label: string; semantic: RegExp}>): void {
  if (!candidates.length) return;
  const response = spawnSync(process.env.PYTHON || 'python3', ['-c', `import io,json,sys
from unittest.mock import patch
from neural.pipeline_record import main
from neural.ts_identity import verify_bundle_identities
results=[]
for encoded in json.load(sys.stdin):
 identity_error=''
 try: verify_bundle_identities(json.loads(encoded))
 except Exception as error: identity_error=str(error)
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(encoded)),patch('sys.stdout',out),patch('sys.stderr',err): status=main()
 results.append({'identity_error':identity_error,'status':status,'stdout':out.getvalue(),'stderr':err.getvalue()})
print(json.dumps(results))`], {input: JSON.stringify(candidates.map(({candidate}) => JSON.stringify(candidate))), encoding: 'utf8',
    timeout: 30_000, maxBuffer: 8 * 1024 * 1024, env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')}});
  assert.equal(response.status, 0, `fresh Python batch failed: ${response.stderr}; ${response.error?.message || ''}; code=${(response.error as NodeJS.ErrnoException | undefined)?.code}; signal=${response.signal}`);
  const results = JSON.parse(response.stdout) as Array<{identity_error: string; status: number; stdout: string; stderr: string}>;
  assert.equal(results.length, candidates.length);
  for (const [index, result] of results.entries()) {
    const {label, semantic} = candidates[index];
    assert.equal(result.identity_error, '', `${label} canonical identities`);
    assert.equal(result.status, 2, `${label}: ${result.stderr}`); assert.equal(result.stdout, '', `${label} atomic publication`);
    assert.match(result.stderr, semantic, label);
  }
}

export function assertPublicItemTamperMatrix(bundle: unknown): void {
  const original = JSON.stringify(bundle);
  const cases: Array<{candidate: unknown; label: string; semantic: RegExp}> = [];
  const valid = python(bundle);
  assert.equal(valid.status, 0, valid.stderr);
  for (const which of ['input', 'successor']) {
    const control = (bundle as any)[`${which}_observation`];
    for (const unknown of control.view.opponent_team) {
      const target = unknown.ident.replace(/^(p[12])a: /, '$1: ');
      if (projectPublicItems(control.protocol_prefix)[target] !== undefined) continue;
      const candidate = structuredClone(bundle) as any;
      candidate[`${which}_observation`].view.opponent_team.find((row: any) => row.ident === unknown.ident).item = 'has-item';
      rehash(candidate);
      itemIdentityMatrixCounts.ordinary++;
      const unchanged = JSON.stringify(candidate);
      assert.throws(() => validateObservableBattleState(candidate[`${which}_observation`]), /Public item/);
      assert.equal(JSON.stringify(candidate), unchanged);
      cases.push({candidate, label: `${which}/unknown-presence`, semantic: /Public item/});
    }
    for (const row of control.view.self_team) {
      if (projectPublicItemHistory(control.protocol_prefix)[row.ident.replace(/^(p[12])a: /, '$1: ')]) continue;
      for (const field of ['last_item', 'item_state']) {
        const candidate = structuredClone(bundle) as any, observation = candidate[`${which}_observation`];
        const own = observation.view.self_team.find((entry: any) => entry.ident === row.ident);
        own[field] = field === 'last_item' ? 'sitrusberry' : 'consumed'; rehash(candidate);
        itemIdentityMatrixCounts.ordinary++;
        const unchanged = JSON.stringify(candidate);
        assert.throws(() => validateObservableBattleState(observation), /Public item/);
        assert.equal(JSON.stringify(candidate), unchanged);
        cases.push({candidate, label: `${which}/${field}`, semantic: /Public item/});
      }
    }
    const facts = projectPublicItems(control.protocol_prefix);
    for (const [target, item] of Object.entries(facts)) {
      const team = target.slice(0, 2) === control.perspective ? 'self_team' : 'opponent_team';
      const mutations: Record<string, (o: any, row: any) => void> = {
        ...(team === 'self_team' ? {
          'false-disposition': (_o: any, row: any) => {row.item_state = row.item_state === 'held' ? 'consumed' : 'held';},
          'missing-disposition': (_o: any, row: any) => {delete row.item_state;},
          'joint-field-suppression': (o: any, row: any) => {row.item_suppressed = true; o.view.field.pseudo_weather = ['magicroom'];},
          'false-suppression': (_o: any, row: any) => {row.item_suppressed = !row.item_suppressed;},
          'missing-suppression': (_o: any, row: any) => {delete row.item_suppressed;},
          ...(projectPublicItemDispositions(control.protocol_prefix)[target]?.last_item ? {
            'false-last-item': (_o: any, row: any) => {row.last_item = row.last_item === 'leftovers' ? 'choicescarf' : 'leftovers';},
            'missing-last-item': (_o: any, row: any) => {delete row.last_item;},
          } : {}),
        } : {}),
        'false-presence': (_o, row) => { if (team === 'opponent_team') { if (item === null) row.item = 'has-item'; else delete row.item; }
          else row.item = item === null ? 'leftovers' : null; },
        'missing-row': (o, row) => { o.view[team] = o.view[team].filter((p: any) => p !== row); },
        'missing-team': (o) => { delete o.view[team]; },
        'false-container': (o) => { o.view[team] = {}; },
        'partial-team': (o, row) => { o.view[team] = o.view[team].filter((p: any) => p !== row).concat({ident: row.ident}); },
        'wrong-side': (o, row) => { o.view[team] = o.view[team].filter((p: any) => p !== row); o.view[team === 'self_team' ? 'opponent_team' : 'self_team'].push(row); },
      };
      for (const [name, mutate] of Object.entries(mutations)) {
        const candidate = structuredClone(bundle) as any, observation = candidate[`${which}_observation`];
        const row = observation.view[team].find((p: any) => p.ident.replace(/^(p[12])a: /, '$1: ') === target);
        if (!row) continue;
        mutate(observation, row); rehash(candidate);
        itemIdentityMatrixCounts.ordinary++;
        const before = JSON.stringify(candidate);
        assert.throws(() => validateObservableBattleState(observation), /Public (health|item) evidence mismatch|Typed lifecycle evidence mismatch/);
        assert.equal(JSON.stringify(candidate), before);
        cases.push({candidate, label: `${which}/${name}`, semantic: /Public (health|item) evidence mismatch|Typed lifecycle evidence mismatch/});
      }
    }
  }
  assertFreshPythonRejections(cases);
  assert.equal(JSON.stringify(bundle), original);
}
