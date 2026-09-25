import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import {
  RECOGNIZED_UNSUPPORTED_RAW_COMMANDS,
  SUPPORTED_RAW_COMMANDS,
} from '../src/protocol_contract';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';

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
  assert.deepEqual(new Set(contract.recognized_unsupported_commands.map((item: any) => item.token)),
    new Set(RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.keys()));
  for (const fixture of contract.record_fixtures) {
    assert.doesNotThrow(() => validateRawProtocolRecord(fixture.record), fixture.token);
  }
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
      const rejectedBundles: any[] = [];
      for (const player of ['p1', 'p2'] as const) {
        const original = result.record_bundles[player];
        assert.ok(original);
        for (const where of ['input', 'successor'] as const) {
          for (const fixture of contract.rejection_fixtures) {
            const candidate = injectProtocolRecord(original, where, fixture.record);
            rejectedBundles.push(candidate);
            assert.throws(() => validateObservableProtocolPrefix(
              candidate[`${where}_observation`].protocol_prefix,
              player,
            ));
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
      assert.equal(response.stdout.trim(), `2 ${contract.rejection_fixtures.length * 4}`);
    } finally {
      await session.close();
    }
  });
}
