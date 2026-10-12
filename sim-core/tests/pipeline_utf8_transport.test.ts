import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { PLAYERS } from '../src/types';

const repositoryRoot = path.resolve(__dirname, '../../..');

function runPython(args: string[], input: string | Buffer) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  assert.ok(!Object.keys(env).some((key) => ['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  return spawnSync(process.env.PYTHON || 'python3', args, {
    cwd: repositoryRoot,
    env: { ...env, PYTHONPATH: path.resolve(repositoryRoot, 'trainer/src') },
    input, encoding: 'utf8', timeout: 30_000,
  });
}

async function unicodeBundles() {
  const direct = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  direct.setPlayer('p1', { name: 'One', team: Teams.import('Flabébé (Pikachu)\nAbility: Static\n- Tackle')! });
  direct.setPlayer('p2', { name: 'Two', team: Teams.import('Pokémon (Eevee)\nAbility: Run Away\n- Tackle')! });
  const snapshot = structuredClone(direct.toJSON());
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(snapshot), options);
    };
    session = await createPipelineIntegrationSession({
      battle_id: 'Pokémon-Flabébé-transport', format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    });
    return (await session.step()).record_bundles;
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
    direct.destroy();
    await session?.close();
  }
}

test('Node UTF-8 names and canonical identities survive actual Python publication without encoding overrides', async () => {
  const bundles = await unicodeBundles();
  for (const player of PLAYERS) {
    const bundle = bundles[player];
    assert.ok(bundle);
    const wire = JSON.stringify(bundle);
    assert.ok(wire.includes('Flabébé') && wire.includes('Pokémon'));
    const published = runPython(['-m', 'neural.pipeline_record'], wire);
    assert.equal(published.status, 0, published.stderr);
    assert.equal(published.stderr, '');
    const row = JSON.parse(published.stdout);
    assert.equal(row.battle_id, 'Pokémon-Flabébé-transport');
    assert.equal(row.source_ref, bundle.source_ref);
    assert.equal(row.observation_id, bundle.input_observation.observation_id);
    assert.equal(row.belief_id, bundle.input_belief.belief_id);
    assert.equal(row.action_id, bundle.action.action_id);
    assert.equal(row.transition_id, bundle.transition.transition_id);
    assert.equal(row.perspective, player);

    const tampered = structuredClone(bundle);
    tampered.input_observation.protocol_prefix.push('|message|Flabébé');
    const rejected = runPython(['-m', 'neural.pipeline_record'], JSON.stringify(tampered));
    assert.equal(rejected.status, 2, rejected.stderr);
    assert.equal(rejected.stdout, '');
    assert.doesNotMatch(rejected.stderr, /Traceback/);
  }
});

test('Node UTF-8 canonical identity probe reads the same accented bundles as production publication', async () => {
  const bundles = await unicodeBundles();
  const checked = runPython(['-c', [
    'import sys',
    'from neural.ts_identity import verify_bundle_identities',
    'from neural.pipeline_json_wire import load_json',
    'for bundle in load_json(sys.stdin):',
    '    verify_bundle_identities(bundle)',
  ].join('\n')], JSON.stringify(PLAYERS.map((player) => bundles[player])));
  assert.equal(checked.status, 0, checked.stderr);
  assert.equal(checked.stdout, '');
});

test('Python production CLI rejects malformed wire input and Unicode diagnostics atomically', () => {
  const cases: Array<{ wire: string | Buffer; diagnostic?: RegExp }> = [
    { wire: Buffer.from('{') },
    { wire: Buffer.from([0x7b, 0x22, 0x78, 0x22, 0x3a, 0x22, 0xff, 0x22, 0x7d]) },
    { wire: JSON.stringify({ '未知😀': true }), diagnostic: /未知😀/ },
    { wire: '{"\\ud800":{"root_seed":1}}', diagnostic: /\\ud800/ },
  ];
  for (const { wire, diagnostic } of cases) {
    const rejected = runPython(['-m', 'neural.pipeline_record'], wire);
    assert.equal(rejected.status, 2, rejected.stderr);
    assert.equal(rejected.stdout, '');
    assert.match(rejected.stderr, /^pipeline-record validation failed:/);
    assert.doesNotMatch(rejected.stderr, /Traceback/);
    if (diagnostic) assert.match(rejected.stderr, diagnostic);
  }
});
