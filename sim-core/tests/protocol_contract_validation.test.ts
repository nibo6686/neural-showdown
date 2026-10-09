import { completeSyntheticHealthView } from './public_consequence_test_helpers';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { extractChannelMessages } from 'pokemon-showdown/dist/sim/battle';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import {
  PROTOCOL_CONTRACT,
  ProtocolContractError,
  RECOGNIZED_UNSUPPORTED_RAW_COMMANDS,
  SUPPORTED_RAW_COMMANDS,
  loadProtocolContract,
  validateProtocolContract,
} from '../src/protocol_contract';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';
import { publicBoostEvidence } from '../src/public_boosts';
import { validateObservableBattleState } from '../src/belief_state';
import { appendPublicSpectatorChunk, validatePublicSpectatorRecord } from '../src/env_manager';

const contractPath = path.resolve(__dirname, '../../../trainer/src/neural/protocol_contract.json');
const contract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));
const canonical = (value: any): string => Array.isArray(value)
  ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const hash = (value: any): string => createHash('sha256').update(canonical(value), 'utf8').digest('hex');
const observationId = (observation: any): string => `obs-${hash(Object.fromEntries(
  Object.entries(observation).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key)),
))}`;
const beliefId = (belief: any): string => `belief-${hash(Object.fromEntries(
  Object.entries(belief).filter(([key]) => key !== 'belief_id'),
))}`;

function injectProtocolRecord(original: any, where: 'input' | 'successor', record: string): any {
  const bundle = structuredClone(original);
  const oldObservationIds = {
    input: bundle.input_observation.observation_id,
    successor: bundle.successor_observation.observation_id,
  };
  const inputCursor = bundle.input_observation.event_cursor;
  if (where === 'input') bundle.input_observation.protocol_prefix.push(record);
  bundle.successor_observation.protocol_prefix.splice(where === 'input' ? inputCursor : bundle.successor_observation.event_cursor, 0, record);
  const references: Record<string, any> = {};
  for (const position of ['input', 'successor'] as const) {
    const observation = bundle[`${position}_observation`];
    let validGrammar = true;
    try { validateObservableProtocolPrefix(observation.protocol_prefix, observation.perspective, observation.view, observation.request); }
    catch { validGrammar = false; }
    if (validGrammar) completeSyntheticHealthView(observation.view, observation.protocol_prefix, observation.perspective, observation.request);
    const opponentKeys = new Set('slot ident name species base_species current_species displayed_species species_source transformed displayed_species_uncertain illusion_revealed details active fainted hp_text hp_ratio status status_source status_started_turn status_turns_public gender level types terastallized volatiles item public_boosts'.split(' '));
    if (validGrammar) for (const row of observation.view.opponent_team) {
      for (const key of Object.keys(row)) if (!opponentKeys.has(key) || key === 'public_boosts' && observation.schema_version === 'observable-battle-state/v1') delete row[key];
    }
    observation.event_cursor = observation.protocol_prefix.length;
    observation.protocol_prefix_hash = hash(observation.protocol_prefix);
    observation.observation_id = observationId(observation);
    references[oldObservationIds[position]] = Object.fromEntries(
      ['schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase']
        .map((key) => [key, observation[key]]),
    );
  }
  const replaceReferences = (value: any): any => Array.isArray(value)
    ? value.map(replaceReferences)
    : value && typeof value === 'object'
      ? references[value.observation_id]
        ? { ...value, ...references[value.observation_id] }
        : Object.fromEntries(Object.entries(value).map(([key, child]) => [key, replaceReferences(child)]))
      : value === oldObservationIds.input
        ? bundle.input_observation.observation_id
        : value === oldObservationIds.successor
          ? bundle.successor_observation.observation_id
          : value;
  for (const position of ['input', 'successor'] as const) {
    bundle[`${position}_belief`] = replaceReferences(bundle[`${position}_belief`]);
    bundle[`${position}_belief`].source_protocol_prefix = [...bundle[`${position}_observation`].protocol_prefix];
  }
  bundle.input_belief.belief_id = beliefId(bundle.input_belief);
  bundle.successor_belief.parent_belief_id = bundle.input_belief.belief_id;
  bundle.successor_belief.belief_id = beliefId(bundle.successor_belief);
  return bundle;
}

function assertRehashedProtocolBundle(bundle: any): void {
  for (const position of ['input', 'successor'] as const) {
    const observation = bundle[`${position}_observation`];
    const belief = bundle[`${position}_belief`];
    assert.equal(observation.event_cursor, observation.protocol_prefix.length);
    assert.equal(observation.protocol_prefix_hash, hash(observation.protocol_prefix));
    assert.equal(observation.observation_id, observationId(observation));
    assert.deepEqual(belief.source_protocol_prefix, observation.protocol_prefix);
    assert.equal(belief.belief_id, beliefId(belief));
    assert.deepEqual(belief.observation, Object.fromEntries(
      ['schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase']
        .map((key) => [key, observation[key]]),
    ));
  }
  assert.equal(bundle.successor_belief.parent_belief_id, bundle.input_belief.belief_id);
  assert.equal(bundle.successor_belief.transition_lineage.input_observation_id, bundle.input_observation.observation_id);
  assert.equal(bundle.successor_belief.transition_lineage.output_observation_id, bundle.successor_observation.observation_id);
}

const autoTieWarning = "|bigerror|You will auto-tie if the battle doesn't end in 10 turns (on turn 1000).";
const malformedAutoTieControls = [
  { kind: 'EV warning', record: "|bigerror|Warning: One player isn't adhering to a 510 EV limit, and the other player is." },
  { kind: 'wrong turn', record: "|bigerror|You will auto-tie if the battle doesn't end in 10 turns (on turn 1001)." },
  { kind: 'field count', record: `${autoTieWarning}|unexpected` },
  { kind: 'whitespace', record: autoTieWarning.replace('10 turns', ' 10 turns') },
  { kind: 'tag suffix', record: `${autoTieWarning}|[from] move: Tackle` },
] as const;

const pythonPath = path.resolve(__dirname, '../../../trainer/src');
const runPython = (input: unknown, script: string) => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-c', script], {
    input: JSON.stringify(input), encoding: 'utf8', env: { ...process.env, PYTHONPATH: pythonPath },
    timeout: 30_000, maxBuffer: 8 * 1024 * 1024,
  });
  if (result.error || result.signal) result.stderr += `\nPython subprocess failed: ${result.error?.message || ''}; signal=${result.signal}; code=${(result.error as NodeJS.ErrnoException | undefined)?.code || ''}`;
  return result;
};

const repeatedSingletonTagFixtures = [
  { family: 'damage', kind: '[from]', record: '|-damage|p1a: Pikachu|50/100|[from] move: Tackle|[from] ability: Static' },
  { family: 'damage', kind: '[of]', record: '|-damage|p1a: Pikachu|50/100|[of] p2: Eevee|[of] p1a: Pikachu' },
  { family: 'damage', kind: '[silent]', record: '|-damage|p1a: Pikachu|50/100|[silent]|[silent]' },
  { family: 'damage', kind: '[partiallytrapped]', record: '|-damage|p1a: Pikachu|50/100|[partiallytrapped]|[partiallytrapped]' },
  { family: 'heal', kind: '[from]', record: '|-heal|p1a: Pikachu|50/100|[from] move: Recover|[from] ability: Regenerator' },
  { family: 'heal', kind: '[of]', record: '|-heal|p1a: Pikachu|50/100|[of] p2: Eevee|[of] p1a: Pikachu' },
  { family: 'heal', kind: '[silent]', record: '|-heal|p1a: Pikachu|50/100|[silent]|[silent]' },
  { family: 'heal', kind: '[zeffect]', record: '|-heal|p1a: Pikachu|50/100|[zeffect]|[zeffect]' },
  { family: 'heal', kind: '[wisher]', record: '|-heal|p1a: Pikachu|50/100|[wisher] Eevee|[wisher] Blissey' },
  { family: 'boost', kind: '[from]', record: '|-boost|p1a: Pikachu|atk|1|[from] move: Swords Dance|[from] ability: Intimidate' },
  { family: 'boost', kind: '[silent]', record: '|-boost|p1a: Pikachu|atk|1|[silent]|[silent]' },
  { family: 'boost', kind: '[zeffect]', record: '|-boost|p1a: Pikachu|atk|1|[zeffect]|[zeffect]' },
] as const;

test('shared contract fixtures cover every supported and recognized-unsupported token in both runtimes', () => {
  const fixtureTokens = contract.record_fixtures.map((fixture: any) => fixture.token);
  assert.equal(new Set(fixtureTokens).size, fixtureTokens.length);
  assert.deepEqual(new Set(fixtureTokens), SUPPORTED_RAW_COMMANDS);
  for (const fixture of contract.record_fixtures) assert.equal(fixture.record.split('|')[1], fixture.token);
  assert.deepEqual(new Set(contract.recognized_unsupported_commands.map((item: any) => item.token)),
    new Set(RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.keys()));
  for (const fixture of contract.record_fixtures) {
    assert.doesNotThrow(() => validateRawProtocolRecord(fixture.record), fixture.token);
  }
  for (const control of contract.valid_record_controls) {
    assert.equal(control.record.split('|')[1], control.token);
    assert.doesNotThrow(() => validateRawProtocolRecord(control.record), control.record);
  }
  assert.doesNotThrow(() => validateRawProtocolRecord('|'));
  assert.deepEqual(validateProtocolContract(contract), PROTOCOL_CONTRACT);
  for (const fixture of contract.rejection_fixtures) {
    assert.throws(() => validateRawProtocolRecord(fixture.record), (error: Error) => {
      if (fixture.kind === 'malformed') return error.message.startsWith('Malformed raw');
      if (fixture.kind === 'unknown') return error.message.startsWith('Unsupported raw protocol event:');
      return error.message.includes(fixture.record.split('|')[1]);
    });
  }

  const result = runPython(contract, `import json,sys
from neural.protocol_contract import RECORD_FIXTURES, REJECTION_FIXTURES, validate_protocol_record, ProtocolRecordError
x=json.load(sys.stdin)
assert {r['token'] for r in RECORD_FIXTURES} == {r['token'] for r in x['record_fixtures']}
assert len(RECORD_FIXTURES) == len(x['record_fixtures'])
for row in x['record_fixtures']: validate_protocol_record(row['record'])
for row in x['rejection_fixtures']:
 try: validate_protocol_record(row['record'])
 except ProtocolRecordError as e: assert e.kind == row['kind'], (row,e.kind,str(e))
 else: raise AssertionError(row)
print(len(RECORD_FIXTURES), len(REJECTION_FIXTURES))`);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), `${contract.record_fixtures.length} ${contract.rejection_fixtures.length}`);
});

test('CE-02 closes ordered typed tags and retains only the pinned public auto-tie warning', () => {
  const warning = autoTieWarning;
  assert.doesNotThrow(() => validateRawProtocolRecord(warning));
  assert.deepEqual(projectPipelineProtocolPrefix([warning]), [warning]);
  assert.doesNotThrow(() => validatePublicSpectatorRecord(warning));
  for (const turnsLeft of contract.validation_rules.bigerror.turns_left_values) {
    const unit = turnsLeft === 1 ? 'turn' : 'turns';
    assert.doesNotThrow(() => validateRawProtocolRecord(
      `|bigerror|You will auto-tie if the battle doesn't end in ${turnsLeft} ${unit} (on turn 1000).`,
    ));
  }

  for (const record of [
    '|-damage|p1a: Pikachu|50/100|[of] p2: Eevee|[from] drain',
    '|-heal|p1a: Pikachu|50/100|[wisher] Eevee|[from] move: Wish',
    '|-sethp|p1a: Pikachu|50/100|[silent]|[from] move: Pain Split',
    '|-boost|p1a: Pikachu|atk|1|[silent]|[from] move: Swords Dance',
    '|-clearpositiveboost|p1a: Pikachu|p2a: Eevee|Mirror Armor|[silent]',
    "|bigerror|You will auto-tie if the battle doesn't end in 1 turns (on turn 1000).",
    ...[11, 99, 150, 499].map((turnsLeft) =>
      `|bigerror|You will auto-tie if the battle doesn't end in ${turnsLeft} turns (on turn 1000).`),
  ]) {
    assert.throws(() => validateRawProtocolRecord(record), record);
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
});

test('CE-02D reaches the pinned warning through restored Showdown turns and retains it raw for both views', async () => {
  const format = 'gen9randombattle';
  const p1Team = Teams.generate(format, { seed: '1,2,3,4' });
  const p2Team = Teams.generate(format, { seed: '9,10,11,12' });
  const sourceBattle = new Battle({ formatid: format, seed: '5,6,7,8' });
  sourceBattle.setPlayer('p1', { name: 'P1', team: p1Team });
  sourceBattle.setPlayer('p2', { name: 'P2', team: p2Team });
  assert.equal(sourceBattle.debugMode, false);
  for (const team of [p1Team, p2Team]) {
    for (const set of team) {
      const evs = Object.values(set.evs ?? {}) as number[];
      assert.ok(evs.reduce((total, ev) => total + ev, 0) <= 510);
    }
  }

  sourceBattle.turn = 989;
  const restored = Battle.fromJSON(JSON.parse(JSON.stringify(sourceBattle.toJSON())));
  const sourceStart = restored.log.length;
  for (let index = 0; index < 11 && !restored.ended; index++) restored.endTurn();
  assert.equal(restored.turn, 1000);
  assert.equal(restored.ended, true);
  assert.equal(restored.winner, '');
  const sourceDelta = restored.log.slice(sourceStart);
  const warningRecords = sourceDelta.filter((line) => line.startsWith('|bigerror|'));
  assert.deepEqual(warningRecords, Array.from({ length: 10 }, (_, index) => {
    const turnsLeft = 10 - index;
    return `|bigerror|You will auto-tie if the battle doesn't end in ${turnsLeft} ${turnsLeft === 1 ? 'turn' : 'turns'} (on turn 1000).`;
  }));
  const messageIndex = sourceDelta.indexOf('|message|It is turn 1000. You have hit the turn limit!');
  const tieIndex = sourceDelta.indexOf('|tie');
  assert.ok(messageIndex > sourceDelta.lastIndexOf(warningRecords.at(-1)!));
  assert.ok(tieIndex > messageIndex);

  const sourceChannels = extractChannelMessages(sourceDelta.join('\n'), [0, 1, 2]);
  for (const channel of [0, 1, 2] as const) {
    assert.deepEqual(sourceChannels[channel].filter((line) => line.startsWith('|bigerror|')), warningRecords);
  }

  const session = await createPipelineIntegrationSession({
    battle_id: 'ce02d-source-warning-prefix', format, seed: [17, 19, 23, 29],
    observation_schema_version: 'observable-battle-state/v2',
  });
  try {
    for (const player of ['p1', 'p2'] as const) {
      const original = session.boundary.perspectives[player].observation;
      const candidate = structuredClone(original);
      const prefix = candidate.protocol_prefix;
      appendPublicSpectatorChunk(sourceChannels[player === 'p1' ? 1 : 2]
        .filter((line) => line.startsWith('|bigerror|')).join('\n'), prefix);
      assert.deepEqual(prefix.slice(-warningRecords.length), warningRecords);
      assert.deepEqual(projectPipelineProtocolPrefix(prefix).slice(-warningRecords.length), warningRecords);
      assert.equal(prefix.some((line) => /^\|(request|error|split|debug|showteam)\|/.test(line)), false);
      candidate.event_cursor = prefix.length;
      candidate.protocol_prefix_hash = hash(prefix);
      candidate.observation_id = observationId(candidate);
      const typedFields = (state: typeof candidate) => {
        const { event_cursor: _cursor, observation_id: _id, protocol_prefix_hash: _hash, protocol_prefix: _prefix, ...typed } = state;
        return typed;
      };
      assert.deepEqual(typedFields(candidate), typedFields(original));
    }
  } finally {
    await session.close();
  }
});

test('CE-04-SLOTS admits only the pinned Healing Wish full-heal provenance shape', () => {
  const exact = '|-heal|p1a: Recipient|100/100|[from] move: Healing Wish';
  assert.deepEqual(contract.validation_rules.healing_wish_heal, {
    required_from: '[from] move: Healing Wish', required_tag_order: ['[from]'], target_role: 'active', health: '100/100',
  });
  assert.doesNotThrow(() => validateRawProtocolRecord(exact));
  assert.deepEqual(projectPipelineProtocolPrefix([exact]), [exact]);
  // Existing ordinary heals remain generic and do not acquire a delayed-effect model.
  assert.doesNotThrow(() => validateRawProtocolRecord('|-heal|p1a: Recipient|50/100|[from] move: Recover'));

  for (const record of [
    '|-heal|p1a: Recipient|100/100|[from] move: Healing Wisp',
    '|-heal|p1a: Recipient|100/100|[from] move: Healing Wishful',
    '|-heal|p1: Recipient|100/100|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|99/100|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|1/1|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|100/100 brn|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[silent]',
    '|-heal|p1a: Recipient|100/100|[silent]|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[from] move: Healing Wish',
    '|-heal|p1a: Recipient|100/100|[from] move: Healing Wish|[wisher] Wisher',
  ]) {
    assert.throws(() => validateRawProtocolRecord(record));
    assert.throws(() => validateObservableProtocolPrefix([record], 'p1'));
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
});

test('CE-02 rejects every repeated singleton HP/heal/stage tag kind before projection', () => {
  for (const fixture of repeatedSingletonTagFixtures) {
    assert.ok(contract.validation_rules.event_tag_cardinality[fixture.family].includes(fixture.kind), fixture.kind);
    assert.throws(() => validateRawProtocolRecord(fixture.record), /duplicate singleton tag kind/);
    assert.throws(() => validateObservableProtocolPrefix([fixture.record], 'p1'), /duplicate singleton tag kind/);
    assert.throws(() => projectPipelineProtocolPrefix([fixture.record]), /unsupported-observable-protocol/);
  }
});

test('CE-02 rejects every private spectator channel before candidate-log accumulation', () => {
  const privateRecords = [
    '|request|{"rqid":7,"side":{"pokemon":[{"item":"secret"}]}}',
    '|error|[Invalid choice] secret',
    '|split|p1',
    '|debug|secret diagnostic',
    '|showteam|p1|packed-private-team',
  ];
  for (const record of privateRecords) {
    assert.throws(() => validatePublicSpectatorRecord(record), /Private/);
    const candidateLog = ['|turn|1'];
    assert.throws(() => appendPublicSpectatorChunk(record, candidateLog), /Private/);
    assert.deepEqual(candidateLog, ['|turn|1']);
  }

  const publicCandidateLog: string[] = [];
  const warning = autoTieWarning;
  assert.doesNotThrow(() => appendPublicSpectatorChunk(`|turn|1\r\n${warning}`, publicCandidateLog));
  assert.deepEqual(publicCandidateLog, ['|turn|1', warning]);

  for (const fixture of malformedAutoTieControls) {
    assert.throws(() => validateRawProtocolRecord(fixture.record), fixture.record);
    assert.throws(() => validatePublicSpectatorRecord(fixture.record), fixture.record);
    assert.throws(() => projectPipelineProtocolPrefix([fixture.record]), /unsupported-observable-protocol/);
    const candidateLog = ['|turn|1'];
    const before = [...candidateLog];
    assert.throws(() => appendPublicSpectatorChunk(`|turn|2\r\n${fixture.record}`, candidateLog), fixture.record);
    assert.deepEqual(candidateLog, before, `${fixture.kind} must not partially append preceding valid lines`);
  }

  assert.throws(
    () => projectPipelineProtocolPrefix(['|error|[Invalid choice]']),
    (error: Error) => error instanceof Error && error.message.includes('pipeline/v1/private-protocol-record'),
  );
});

test('singleturn source controls cover every configured literal and tagged template exactly once', () => {
  const rules = contract.validation_rules.singleturn;
  const controls = contract.valid_record_controls
    .filter((control: any) => control.token === '-singleturn')
    .map((control: any) => control.record.split('|'));
  const untagged = controls.filter((parts: string[]) => parts.length === 4).map((parts: string[]) => parts[3]).sort();
  assert.deepEqual(untagged, [...rules.untagged_effects].sort());

  const tagged = controls.filter((parts: string[]) => parts.length === 5).map((parts: string[]) => {
    const noPayloadTag = parts[4] === '[zeffect]';
    const form: any = {
      effect: parts[3],
      tag: noPayloadTag ? parts[4] : '[of]',
      tag_value: noPayloadTag ? 'none' : 'player-ident',
    };
    if (!noPayloadTag) form.ident_role = 'active';
    return form;
  });
  const taggedForms = tagged.filter((form: any, index: number) => tagged.findIndex((candidate: any) =>
    JSON.stringify(candidate) === JSON.stringify(form)) === index);
  assert.deepEqual(taggedForms, rules.tagged_forms);
  assert.equal(untagged.length, rules.untagged_effects.length);
  assert.deepEqual(controls
    .filter((parts: string[]) => parts.length === 5 && parts[3] === 'Helping Hand')
    .map((parts: string[]) => parts[4])
    .sort(), ['[of] p1a: Pikachu', '[of] p2a: Eevee']);
});

test('Helping Hand keeps its Pokemon source active while generic side-or-active fields retain their source role', () => {
  for (const source of ['p1a: Eevee', 'p2a: Eevee']) {
    const record = `|-singleturn|p1a: Pikachu|Helping Hand|[of] ${source}`;
    assert.doesNotThrow(() => validateRawProtocolRecord(record), record);
    assert.doesNotThrow(() => validateObservableProtocolPrefix([record], 'p1'), record);
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
  }
  for (const source of ['p1: Eevee', 'p2: Eevee']) {
    const record = `|-singleturn|p1a: Pikachu|Helping Hand|[of] ${source}`;
    assert.throws(() => validateRawProtocolRecord(record), /single-turn source ident/);
    assert.throws(() => validateObservableProtocolPrefix([record], 'p1'), /single-turn source ident/);
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
  for (const record of [
    '|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a:Eevee',
    '|-singleturn|p1a: Pikachu|Helping Hand|[of]',
    '|-singleturn|p1a: Pikachu|Helping Hand|[of] Eevee',
  ]) {
    assert.throws(() => validateRawProtocolRecord(record));
    assert.throws(() => validateObservableProtocolPrefix([record], 'p1'));
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
  assert.doesNotThrow(() => validateRawProtocolRecord('|-damage|p1a: Pikachu|50/100|[of] p2: Eevee'));
});

test('player-ident fields require the emitted colon-space spelling across active and side references', () => {
  const rejected = new Set(contract.rejection_fixtures.map((fixture: any) => fixture.record));
  for (const record of [
    '|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a:Eevee',
    '|-damage|p1a: Pikachu|50/100|[of] p2:Eevee',
    '|-heal|p1a: Pikachu|50/100|[of] p2a:Eevee',
    '|move|p1a: Pikachu|Tackle|p2:Eevee',
  ]) assert.ok(rejected.has(record), record);
  for (const record of [
    '|move|p1a: Pikachu|Tackle|p2: Eevee',
    '|move|p1a: Mr: Mime|Tackle|p2a: Farfetch\'d',
  ]) assert.doesNotThrow(() => validateRawProtocolRecord(record), record);
  assert.ok(contract.valid_record_controls.some((control: any) =>
    control.record === '|-heal|p1: Blissey|50/100|[from] move: Revival Blessing'));
  assert.ok(contract.valid_record_controls.some((control: any) =>
    control.record.endsWith('|[of] p2: Eevee')));
  const malformedBoostSource = '|-clearpositiveboost|p1a: Pikachu|p2: Eevee|move: Psych Up';
  assert.throws(() => publicBoostEvidence([malformedBoostSource]), /source identifier/);
  const pythonBoostCheck = runPython([malformedBoostSource], [
    'import json,sys',
    'from neural.public_boosts import public_boost_evidence',
    'try: public_boost_evidence(json.load(sys.stdin))',
    'except ValueError as error: assert "source identifier" in str(error)',
    'else: raise AssertionError("side-only source was accepted")',
  ].join('\n'));
  assert.equal(pythonBoostCheck.status, 0, pythonBoostCheck.stderr);
});

test('shared contract loaders reject bad structure and load only a complete supported contract', () => {
  const invalid = [
    (() => { const value = structuredClone(contract); value.supported_commands = 'move'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.integer.lexeme = 'unicode-decimal'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.player_ident.separator = ':'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.hitcount.count_values.pop(); return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.singleturn.tagged_forms[0].tag = '[of]'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.unreviewed = {}; return value; })(),
    (() => { const value = structuredClone(contract); value.supported_commands.push(value.supported_commands[0]); return value; })(),
    (() => { const value = structuredClone(contract); value.record_fixtures.find((row: any) => row.token === 'ability').token = '-ability'; return value; })(),
    (() => { const value = structuredClone(contract); value.supported_commands.push('clearstatus'); return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.singlemove.forms[1].pop(); return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.singlemove.forms.push(['Future Mechanic']); return value; })(),
    (() => { const value = structuredClone(contract); value.rejection_fixtures.find((row: any) => row.record === '|futuremechanic|opaque').kind = 'malformed'; return value; })(),
  ];
  for (const value of invalid) assert.throws(() => validateProtocolContract(value), ProtocolContractError);

  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'protocol-contract-loader-'));
  const validPath = path.join(directory, 'valid.json');
  const malformedPath = path.join(directory, 'malformed.json');
  const invalidPath = path.join(directory, 'invalid.json');
  const missingPath = path.join(directory, 'missing.json');
  try {
    fs.writeFileSync(validPath, JSON.stringify(contract));
    fs.writeFileSync(malformedPath, '{');
    fs.writeFileSync(invalidPath, JSON.stringify(invalid[0]));
    assert.doesNotThrow(() => loadProtocolContract(validPath));
    assert.throws(() => loadProtocolContract(malformedPath), /Unable to load shared protocol contract/);
    assert.throws(() => loadProtocolContract(invalidPath), /Invalid shared protocol contract/);
    assert.throws(() => loadProtocolContract(missingPath), /Unable to load shared protocol contract/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }

  const result = runPython({ invalid, contract }, `import json,sys,tempfile
from pathlib import Path
from neural.protocol_contract import ProtocolContractError, load_protocol_contract, validate_protocol_contract
x=json.load(sys.stdin)
for candidate in x['invalid']:
 try: validate_protocol_contract(candidate)
 except ProtocolContractError: pass
 else: raise AssertionError('invalid contract accepted')
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 valid=root/'valid.json'; malformed=root/'malformed.json'; invalid=root/'invalid.json'; missing=root/'missing.json'
 valid.write_text(json.dumps(x['contract']), encoding='utf-8')
 malformed.write_text('{', encoding='utf-8')
 invalid.write_text(json.dumps(x['invalid'][0]), encoding='utf-8')
 assert load_protocol_contract(valid)
 for file in (malformed, invalid, missing):
  try: load_protocol_contract(file)
  except ProtocolContractError: pass
  else: raise AssertionError(f'loader accepted {file}')
print('loader failures are closed')`);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), 'loader failures are closed');
});

test('prefix projection validates malformed filtered records and preserves legal filtering', () => {
  for (const record of ['|request|not-json', '|tier|', '|tier|[Gen 9] Random Battle|extra']) {
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
  assert.deepEqual(projectPipelineProtocolPrefix([
    '|', '|request|{}', '|tier|[Gen 9] Random Battle', '|ability|p1a: Rayquaza|Air Lock', '|-message|raw diagnostic',
  ]), ['|ability|p1a: Rayquaza|Air Lock', '|-message|raw diagnostic']);
  for (const control of contract.valid_record_controls) {
    const projected = projectPipelineProtocolPrefix([control.record]);
    assert.deepEqual(projected, ['request', 'tier'].includes(control.token) ? [] : [control.record]);
  }
});

test('raw identifier validation agrees across direct validation, observation validation, and prefix projection', () => {
  const identifierFixtures = contract.rejection_fixtures.filter((fixture: any) => {
    const command = fixture.record.split('|')[1];
    return ['faint', '-clearboost', '-transform'].includes(command);
  });
  assert.ok(identifierFixtures.some((fixture: any) => fixture.record === '|faint|p1a: Pikachu '));
  assert.ok(identifierFixtures.some((fixture: any) => fixture.record === '|-clearboost|p1a: Pikachu '));
  assert.deepEqual(identifierFixtures.filter((fixture: any) => fixture.record.startsWith('|-transform|p1a: Ditto|'))
    .map((fixture: any) => fixture.record), [
      '|-transform|p1a: Ditto|p2a:Eevee',
      '|-transform|p1a: Ditto|p2a: Eevee ',
      '|-transform|p1a: Ditto|p2a:  Eevee',
      '|-transform|p1a: Ditto|p2a:\tEevee',
      '|-transform|p1a: Ditto|p2a:\u00a0Eevee',
      '|-transform|p1a: Ditto|p2a:\u2009Eevee',
      '|-transform|p1a: Ditto|p2: Eevee',
    ]);
  for (const { record } of identifierFixtures) {
    assert.throws(() => validateRawProtocolRecord(record), record);
    assert.throws(() => validateObservableProtocolPrefix([record], 'p1'), record);
    assert.throws(() => projectPipelineProtocolPrefix([record]), record);
  }

  const validControls = contract.valid_record_controls.filter((control: any) =>
    ['faint', '-clearboost', '-transform'].includes(control.token));
  for (const control of validControls) {
    assert.doesNotThrow(() => validateRawProtocolRecord(control.record), control.record);
    assert.deepEqual(projectPipelineProtocolPrefix([control.record]), [control.record]);
  }
});

for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`${version} rehashed rejection matrix covers both actors and input/successor prefixes`, async () => {
    const session = await createPipelineIntegrationSession({
      battle_id: `protocol-contract-${version}`,
      format: 'gen9randombattle',
      seed: [31, 47, 59, 71],
      observation_schema_version: version,
    });
    try {
      const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
        const request = session.boundary.perspectives[player].observation.request!;
        return [player, canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0])];
      })) as Parameters<typeof session.step>[0];
      const result = await session.step(actions);
      const validBundles = (['p1', 'p2'] as const).map((player) => result.record_bundles[player]);
      const semanticRejectedBundles: any[] = [];
      const grammarRecords: string[] = [];
      let publishedAutoTieControls = 0;
      const semanticMismatch = /(?:Public (?:health|item|ability)|Typed lifecycle) evidence mismatch/i;
      // Hypothetical grammar targets do not establish an addressed owned roster.
      const classifyGrammarBundle = (candidate: any, record: string) => {
        grammarRecords.push(record);
        const before = structuredClone(candidate);
        try {
          validateObservableBattleState(candidate.input_observation);
          validateObservableBattleState(candidate.successor_observation);
          validBundles.push(candidate);
          if (record === autoTieWarning) publishedAutoTieControls++;
        } catch (error) {
          assert.notEqual(record, autoTieWarning, 'accepted CE-02D raw-only warning must still publish');
          assert.match(String(error), semanticMismatch, record);
          semanticRejectedBundles.push(candidate);
        }
        assert.deepEqual(candidate, before);
      };
      const singleturnControls = contract.valid_record_controls.filter((control: any) => control.token === '-singleturn');
      const roleControls = singleturnControls.flatMap((control: any) => control.record.includes('|Helping Hand|')
        ? [control, { ...control, record: control.record.replace('p2a: Eevee', 'p1a: Eevee') }]
        : [control]);
      roleControls.push({ token: 'bigerror', record: autoTieWarning, reconstruction_scope: 'CE-02D raw-only source warning' });
      roleControls.push(...contract.valid_record_controls.filter((control: any) => control.token === '-singlemove')
        .flatMap((control: any) => [control, { ...control, record: control.record.replace('p1a: Pikachu', 'p2a: Eevee') }]));
      roleControls.push(...contract.valid_record_controls.filter((control: any) => control.token === '-anim')
        .flatMap((control: any) => [control, { ...control, record: control.record
          .replace('p1a: Pikachu', 'p2a: Pikachu').replace('p2a: Eevee', 'p1a: Eevee') }]));
      const wisherControls = contract.valid_record_controls.filter((control: any) =>
        control.token === '-heal' && control.record.includes('|[wisher] '));
      assert.deepEqual(wisherControls.map((control: any) => control.record.split('|').slice(4)), [[
        contract.validation_rules.heal_wisher_dependency.required_from,
        '[wisher] Eevee',
      ]]);
      roleControls.push(...wisherControls);
      const abilityControls = contract.valid_record_controls.filter((control: any) => control.token === '-ability');
      assert.ok(abilityControls.some((control: any) => control.record.endsWith('|boost')));
      assert.ok(abilityControls.some((control: any) => control.record.includes('[from] ability: Trace|[of]')));
      roleControls.push(...abilityControls);
      const taglessItemControls = contract.valid_record_controls.filter((control: any) => control.token === '-enditem');
      assert.deepEqual(taglessItemControls.map((control: any) => control.record), [
        '|-enditem|p1a: Holder|Air Balloon',
        '|-enditem|p1a: Holder|Booster Energy',
        '|-enditem|p1a: Holder|Focus Sash',
        '|-enditem|p1a: Holder|Power Herb',
        '|-enditem|p1a: Holder|Throat Spray',
        '|-enditem|p1a: Holder|Weakness Policy',
        '|-enditem|p1a: Holder|White Herb',
      ]);
      roleControls.push(...taglessItemControls);
      const whiteHerbRecycleControls = contract.valid_record_controls.filter((control: any) =>
        control.token === '-item' && control.record === '|-item|p1a: Holder|White Herb|[from] move: Recycle');
      assert.equal(whiteHerbRecycleControls.length, 1);
      roleControls.push(...whiteHerbRecycleControls);
      const majorStatusControls = contract.valid_record_controls.filter((control: any) =>
        control.token === '-status' || control.token === '-curestatus');
      assert.equal(majorStatusControls.length, 13);
      roleControls.push(...majorStatusControls);
      const hitcountControls = contract.valid_record_controls.filter((control: any) => control.token === '-hitcount');
      assert.deepEqual(hitcountControls.map((control: any) => control.record), [
        '|-hitcount|p2a: Maushold|10',
        '|-hitcount|p1: Target|1',
        '|-hitcount|p1: Houndstone|2',
      ]);
      roleControls.push(...hitcountControls);
      const playerIdentControls = contract.valid_record_controls.filter((control: any) =>
        control.reconstruction_scope.startsWith('raw-only player-ident grammar control') || control.token === '-transform');
      let rehashedGrammarControls = 0;
      const rejectedBundles: any[] = [];
      let rehashedBigerrorRejections = 0;
      for (const player of ['p1', 'p2'] as const) {
        const original = result.record_bundles[player];
        assert.ok(original);
        for (const where of ['input', 'successor'] as const) {
          for (const control of roleControls) {
            const candidate = injectProtocolRecord(original, where, control.record);
            assertRehashedProtocolBundle(candidate);
            classifyGrammarBundle(candidate, control.record);
            rehashedGrammarControls++;
            assert.doesNotThrow(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ));
          }
          for (const control of playerIdentControls) {
            const candidate = injectProtocolRecord(original, where, control.record);
            assertRehashedProtocolBundle(candidate);
            classifyGrammarBundle(candidate, control.record);
            rehashedGrammarControls++;
            assert.doesNotThrow(() => validateObservableProtocolPrefix(
              candidate[where + '_observation'].protocol_prefix,
              player,
            ));
          }
          for (const fixture of contract.rejection_fixtures) {
            const candidate = injectProtocolRecord(original, where, fixture.record);
            assertRehashedProtocolBundle(candidate);
            const prefixBeforeValidation = [...candidate[`${where}_observation`].protocol_prefix];
            rejectedBundles.push(candidate);
            if (['faint', '-clearboost', '-transform'].includes(fixture.record.split('|')[1])) {
              assert.throws(() => projectPipelineProtocolPrefix([fixture.record]));
            }
            assert.throws(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ));
            assert.deepEqual(candidate[`${where}_observation`].protocol_prefix, prefixBeforeValidation);
          }
          for (const fixture of malformedAutoTieControls) {
            const candidate = injectProtocolRecord(original, where, fixture.record);
            assertRehashedProtocolBundle(candidate);
            const candidateBeforeValidation = structuredClone(candidate);
            rejectedBundles.push(candidate);
            assert.throws(() => validateRawProtocolRecord(fixture.record), fixture.record);
            assert.throws(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ), fixture.record);
            assert.deepEqual(candidate, candidateBeforeValidation);
            rehashedBigerrorRejections++;
          }
          for (const fixture of repeatedSingletonTagFixtures) {
            const candidate = injectProtocolRecord(original, where, fixture.record);
            const candidateBeforeValidation = structuredClone(candidate);
            rejectedBundles.push(candidate);
            assert.throws(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ), /duplicate singleton tag kind/);
            assert.deepEqual(candidate, candidateBeforeValidation);
          }
        }
      }
      assert.equal(rehashedBigerrorRejections, malformedAutoTieControls.length * 4);
      assert.equal(validBundles.length + semanticRejectedBundles.length, 2 + rehashedGrammarControls);
      assert.ok(semanticRejectedBundles.length > 0, 'foreign synthetic owners must not publish');
      assert.equal(publishedAutoTieControls, 4, 'both perspectives and input/successor raw-only warnings publish');
      assert.ok(validBundles.length >= 6, 'two unmodified source bundles and four warnings remain positive');
      const response = runPython({ validBundles, rejectedBundles, semanticRejectedBundles, grammarRecords }, `import io,json,sys,re
from unittest.mock import patch
from neural.pipeline_record import PipelineRecordError, main, validate_pipeline_bundle
from neural.ts_identity import verify_bundle_identities
from neural.protocol_contract import validate_protocol_record
x=json.load(sys.stdin)
for record in x['grammarRecords']: validate_protocol_record(record)
for b in x['validBundles']:
 verify_bundle_identities(b); validate_pipeline_bundle(b)
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(b))), patch('sys.stdout',out), patch('sys.stderr',err): status=main()
 assert status == 0 and out.getvalue(), (status,out.getvalue(),err.getvalue())
 record=json.loads(out.getvalue())
 assert 'observation_prefix_hash' in record
 assert not ({'request','protocol_prefix','simulator_snapshot','seed','team','hidden_set'} & set(record))
 if any(line.startswith('|bigerror|') for line in b['input_observation']['protocol_prefix']):
  assert 'bigerror' not in json.dumps(record)
for b in x['semanticRejectedBundles']:
 verify_bundle_identities(b)
 before=json.dumps(b,sort_keys=True)
 try: validate_pipeline_bundle(b)
 except PipelineRecordError as error:
  assert re.search(r'(?:Public (?:health|item|ability)|Typed lifecycle) evidence mismatch',str(error),re.I), str(error)
 else: raise AssertionError('synthetic grammar target acquired owned authority')
 assert json.dumps(b,sort_keys=True) == before
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(b))), patch('sys.stdout',out), patch('sys.stderr',err): status=main()
 assert status == 2 and out.getvalue() == '', (status,out.getvalue(),err.getvalue())
 assert json.dumps(b,sort_keys=True) == before
for b in x['rejectedBundles']:
 verify_bundle_identities(b)
 before=json.dumps(b,sort_keys=True)
 try: validate_pipeline_bundle(b)
 except PipelineRecordError: pass
 else: raise AssertionError('rehashed rejected candidate published')
 assert json.dumps(b,sort_keys=True) == before
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(b))), patch('sys.stdout',out), patch('sys.stderr',err): status=main()
 assert status == 2 and out.getvalue() == '', (status,out.getvalue(),err.getvalue())
 assert json.dumps(b,sort_keys=True) == before
print(len(x['validBundles']),len(x['semanticRejectedBundles']),len(x['rejectedBundles']))`);
      assert.equal(response.status, 0, response.stderr);
      console.log(`${version} grammar matrix: ${validBundles.length} semantic positives; ${semanticRejectedBundles.length} synthetic semantic negatives; ${rejectedBundles.length} grammar negatives`);
      assert.equal(response.stdout.trim(), `${validBundles.length} ${semanticRejectedBundles.length} ${(contract.rejection_fixtures.length + repeatedSingletonTagFixtures.length + malformedAutoTieControls.length) * 4}`);
    } finally {
      await session.close();
    }
  });
}
