import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {LocalBattleEnv} from '../src/env_manager';
import {SettlingError} from '../src/settling';
import {NATIVE11_CONTEXT, HISTORICAL10_CONTEXT} from '../src/version_profile';
import {validateRawProtocolRecord} from '../src/observable_state';

const root = path.resolve(__dirname, '../../..');
const {extractReplay} = require(path.join(root, 'tools/replay_repro/index.cjs'));
const families = new Set(['-start','-end','-sidestart','-sideend','-weather','-fieldstart','-fieldend','cant','heal','-swapsideconditions']);
const comparison = NATIVE11_CONTEXT.inventory.effect_source_comparison.entries;
const blocked = new Set(comparison.filter((e: any) => e.status !== 'unchanged').map((e: any) => e.id));

for (const directory of ['replay-repro', 'replay-extract']) {
  for (const name of fs.readdirSync(path.join(root, 'sim-core/tests/fixtures', directory)).filter(n => n.endsWith('.json'))) {
    test(`full both-owner extraction diagnoses retained blocks: ${name}`, {timeout: 30000}, async () => {
      const replay = JSON.parse(fs.readFileSync(path.join(root, 'sim-core/tests/fixtures', directory, name), 'utf8'));
      const result = await extractReplay(replay);
      assert.ok(result.records.p1 > 10 && result.records.p2 > 10);
      for (const failure of result.failures) {
        assert.ok(['p1','p2'].includes(failure.owner));
        assert.ok(failure.message && failure.record);
        if (families.has(failure.command)) {
          assert.ok(blocked.has(failure.effect_id), JSON.stringify(failure));
          assert.match(failure.message, /unsupported-fail-closed/);
        }
      }
      // Diagnostics never export a view after skipping a rejected record.
      assert.deepEqual(Object.keys(result).sort(), ['failures','id','records']);
    });
  }
}

test('native lifecycle restores raw shapes while source changes, unknown IDs and Court Change fail closed', () => {
  for (const record of ['|cant|p1a: Pikachu|par','|heal|p1a: Pikachu|100/100',
    '|-weather|none','|-fieldstart|move: Gravity','|-fieldend|move: Gravity']) {
    assert.doesNotThrow(() => validateRawProtocolRecord(record, NATIVE11_CONTEXT));
  }
  for (const row of comparison.filter((e: any) => e.status !== 'unchanged')) {
    const command = row.category === 'weather' ? '-weather' : ['terrain','pseudo_weather'].includes(row.category) ? '-fieldstart'
      : row.category === 'side_condition' ? '-sidestart' : '-start';
    if (row.category === 'major_status') continue;
    const record = command === '-weather' || command === '-fieldstart' ? `|${command}|${row.id}`
      : command === '-sidestart' ? `|${command}|p1: Alice|${row.id}` : `|${command}|p1a: Pikachu|${row.id}`;
    assert.throws(() => validateRawProtocolRecord(record, NATIVE11_CONTEXT), Error, row.id);
  }
  assert.throws(() => validateRawProtocolRecord('|-start|p1a: Pikachu|unreviewed', NATIVE11_CONTEXT), /unclassified-effect-value/);
  assert.throws(() => validateRawProtocolRecord('|-swapsideconditions', NATIVE11_CONTEXT), /court-change/);
  assert.throws(() => validateRawProtocolRecord('|cant|p1a: Pikachu', NATIVE11_CONTEXT), /Malformed/);
  assert.doesNotThrow(() => validateRawProtocolRecord('|-start|p1a: Pikachu|Substitute', HISTORICAL10_CONTEXT));
});

test('simulation replay cannot run in an authoritative environment or execute arbitrary input', async () => {
  const env = LocalBattleEnv.createSimulationOnly({id:'replay-denial',format:'gen9randombattle'});
  const authoritative = new LocalBattleEnv('authoritative-replay-denial','gen9randombattle');
  try {
    await assert.rejects(env.replaySimulation('>eval process.exit()', () => {}), /Unsupported simulation replay command/);
    await assert.rejects(authoritative.replaySimulation('', () => {}), /simulation-only/);
  } finally {await env.close();await authoritative.close();}
});

test('settling simulator errors retain the class, message and first cause frame', async () => {
  const env = LocalBattleEnv.createSimulationOnly({id:'cause',format:'gen9randombattle',seed:[31,32,33,34]});
  try {
    await env.reset();
    const cause = new TypeError('Unsupported raw protocol event: -end.');
    env.markError(cause);
    await assert.rejects(env.step({}), error => {
      assert.ok(error instanceof SettlingError);
      assert.equal(error.message, 'settling/v1/simulator-error');
      assert.deepEqual(error.diagnostic.cause, {name:'TypeError',message:cause.message,
        at:cause.stack!.split('\n').find(line => /^\s+at /.test(line))!.trim()});
      assert.match(error.stack!, /Caused by TypeError: Unsupported raw protocol event: -end\./);
      return true;
    });
  } finally {await env.close();}
});
