import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
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

const pythonPath = path.resolve(__dirname, '../../../trainer/src');
const runPython = (input: unknown, script: string) => spawnSync(
  process.env.PYTHON || 'python3', ['-c', script], {
    input: JSON.stringify(input), encoding: 'utf8', env: { ...process.env, PYTHONPATH: pythonPath },
  },
);

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
  assert.deepEqual(tagged, rules.tagged_forms);
  assert.equal(controls.length, rules.untagged_effects.length + rules.tagged_forms.length);
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

for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`${version} rehashed rejection matrix covers both actors and input/successor prefixes`, async () => {
    const session = await createPipelineIntegrationSession({
      battle_id: `protocol-contract-${version}`,
      format: 'gen9randombattle',
      seed: [31, 47, 59, 71],
      observation_schema_version: version,
});

test('shared contract loaders reject bad structure and load only a complete supported contract', () => {
  const invalid = [
    (() => { const value = structuredClone(contract); value.supported_commands = 'move'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.integer.lexeme = 'unicode-decimal'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.player_ident.separator = ':'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.singleturn.tagged_forms[0].tag = '[of]'; return value; })(),
    (() => { const value = structuredClone(contract); value.validation_rules.unreviewed = {}; return value; })(),
    (() => { const value = structuredClone(contract); value.supported_commands.push(value.supported_commands[0]); return value; })(),
    (() => { const value = structuredClone(contract); value.record_fixtures.find((row: any) => row.token === 'ability').token = '-ability'; return value; })(),
    (() => { const value = structuredClone(contract); value.supported_commands.push('clearstatus'); return value; })(),
    (() => { const value = structuredClone(contract); value.recognized_unsupported_commands.find((row: any) => row.token === '-singlemove').kind = 'raw-only'; return value; })(),
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
    '|', '|request|{}', '|tier|[Gen 9] Random Battle', '|ability|p1a: Pikachu|Static', '|-message|raw diagnostic',
  ]), ['|ability|p1a: Pikachu|Static', '|-message|raw diagnostic']);
  for (const control of contract.valid_record_controls) {
    const projected = projectPipelineProtocolPrefix([control.record]);
    assert.deepEqual(projected, ['request', 'tier'].includes(control.token) ? [] : [control.record]);
  }
});

test('raw identifier validation agrees across direct validation, observation validation, and prefix projection', () => {
  const identifierFixtures = contract.rejection_fixtures.filter((fixture: any) => {
    const command = fixture.record.split('|')[1];
    return ['faint', '-clearboost', '-endability', '-transform'].includes(command);
  });
  assert.ok(identifierFixtures.some((fixture: any) => fixture.record === '|faint|p1a: Pikachu '));
  assert.ok(identifierFixtures.some((fixture: any) => fixture.record === '|-clearboost|p1a: Pikachu '));
  assert.ok(identifierFixtures.some((fixture: any) => fixture.record === '|-endability|p1a: Pikachu '));
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
    ['faint', '-clearboost', '-endability', '-transform'].includes(control.token));
  for (const control of validControls) {
    assert.doesNotThrow(() => validateRawProtocolRecord(control.record), control.record);
    assert.deepEqual(projectPipelineProtocolPrefix([control.record]), [control.record]);
  }
});
    try {
      const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
        const request = session.boundary.perspectives[player].observation.request!;
        return [player, canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0])];
      })) as Parameters<typeof session.step>[0];
      const result = await session.step(actions);
      const validBundles = (['p1', 'p2'] as const).map((player) => result.record_bundles[player]);
      const singleturnControls = contract.valid_record_controls.filter((control: any) => control.token === '-singleturn');
      const roleControls = singleturnControls.flatMap((control: any) => control.record.includes('|Helping Hand|')
        ? [control, { ...control, record: control.record.replace('p2a: Eevee', 'p1a: Eevee') }]
        : [control]);
      const playerIdentControls = contract.valid_record_controls.filter((control: any) =>
        control.reconstruction_scope.startsWith('raw-only player-ident grammar control') || control.token === '-transform');
      let rehashedGrammarControls = 0;
      const rejectedBundles: any[] = [];
      for (const player of ['p1', 'p2'] as const) {
        const original = result.record_bundles[player];
        assert.ok(original);
        for (const where of ['input', 'successor'] as const) {
          for (const control of roleControls) {
            const candidate = injectProtocolRecord(original, where, control.record);
            validBundles.push(candidate);
            rehashedGrammarControls++;
            assert.doesNotThrow(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ));
          }
          for (const control of playerIdentControls) {
            const candidate = injectProtocolRecord(original, where, control.record);
            validBundles.push(candidate);
            rehashedGrammarControls++;
            assert.doesNotThrow(() => validateObservableProtocolPrefix(
              candidate[where + '_observation'].protocol_prefix,
              player,
            ));
          }
          for (const fixture of contract.rejection_fixtures) {
            const candidate = injectProtocolRecord(original, where, fixture.record);
            const prefixBeforeValidation = [...candidate[`${where}_observation`].protocol_prefix];
            rejectedBundles.push(candidate);
            if (['faint', '-clearboost', '-endability', '-transform'].includes(fixture.record.split('|')[1])) {
              assert.throws(() => projectPipelineProtocolPrefix([fixture.record]));
            }
            assert.throws(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ));
            assert.deepEqual(candidate[`${where}_observation`].protocol_prefix, prefixBeforeValidation);
          }
        }
      }
      const response = runPython({ validBundles, rejectedBundles }, `import io,json,sys
from unittest.mock import patch
from neural.pipeline_record import PipelineRecordError, main, validate_pipeline_bundle
from neural.ts_identity import verify_bundle_identities
x=json.load(sys.stdin)
for b in x['validBundles']:
 verify_bundle_identities(b); validate_pipeline_bundle(b)
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(b))), patch('sys.stdout',out), patch('sys.stderr',err): status=main()
 assert status == 0 and out.getvalue(), (status,out.getvalue(),err.getvalue())
for b in x['rejectedBundles']:
 verify_bundle_identities(b)
 try: validate_pipeline_bundle(b)
 except PipelineRecordError: pass
 else: raise AssertionError('rehashed rejected candidate published')
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(b))), patch('sys.stdout',out), patch('sys.stderr',err): status=main()
 assert status == 2 and out.getvalue() == '', (status,out.getvalue(),err.getvalue())
print(len(x['validBundles']),len(x['rejectedBundles']))`);
      assert.equal(response.status, 0, response.stderr);
      assert.equal(response.stdout.trim(), `${2 + rehashedGrammarControls} ${contract.rejection_fixtures.length * 4}`);
    } finally {
      await session.close();
    }
  });
}
