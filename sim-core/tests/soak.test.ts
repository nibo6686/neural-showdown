import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import type { PlayerID, StepResult } from '../src/types';
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const SEED = [1, 2, 3, 4];
const CONFIG = { battle_id: 'soak', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, species = 'Snorlax', tera = 'Fire') {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(`Target (${species})
Ability: ${species === 'Zoroark' ? 'Illusion' : 'Immunity'}
Tera Type: ${tera}
- Splash
- Explosion
- Conversion

Mask (Snorlax)
Ability: Immunity
- Splash
`)!;
  const other = Teams.import(`Soaker (Giratina)
Ability: Pressure
- Soak
- Splash
- Whirlwind
- Swift

Reserve (Blissey)
- Splash
`)!;
  battle.setPlayer('p1', { team: actor === 'p1' ? own : other });
  battle.setPlayer('p2', { team: actor === 'p2' ? own : other });
  return battle;
}
function choices(actor: PlayerID, own: string, other = 'move 2') {
  return actor === 'p1' ? { p1: own, p2: other } : { p1: other, p2: own };
}
async function harness(actor: PlayerID, species = 'Snorlax', tera = 'Fire') {
  const battle = fixture(actor, species, tera);
  const env = new LocalBattleEnv('soak', CONFIG.format, SEED);
  let result = await env.resetFromSerialized(structuredClone(battle.toJSON()), OPTIONS);
  const prefix = [...result.log_delta];
  const frames: { observation: ReturnType<typeof projectPipelineStepResult>; json: string }[] = [];
  const remember = () => {
    const observation = projectPipelineStepResult(result, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix));
    frames.push({ observation, json: JSON.stringify(observation) }); return observation;
  };
  remember();
  return {
    battle, env,
    get result() { return result; },
    async turn(own: string, other = 'move 2') {
      const c = choices(actor, own, other); battle.makeChoices(c.p1, c.p2);
      result = await env.stepWithOptions(c, OPTIONS); prefix.push(...result.log_delta); return remember();
    },
    async replacement(slot = 2) {
      battle.choose(actor, `switch ${slot}`);
      result = await env.stepWithOptions({ [actor]: `switch ${slot}` }, OPTIONS); prefix.push(...result.log_delta); return remember();
    },
    async restore() {
      const restored = new LocalBattleEnv('soak-restore', CONFIG.format, SEED);
      try {
        const step = await restored.resetFromSerialized(env.captureSeededSnapshot(null).simulator_state, OPTIONS);
        assert.deepEqual(projectPipelineStepResult(step, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix)), frames.at(-1)!.observation);
        for (const f of frames) assert.equal(JSON.stringify(f.observation), f.json);
      } finally { await restored.close(); }
    },
    async close() { battle.destroy(); await env.close(); },
  };
}
function activeTypes(result: StepResult, actor: PlayerID, own: string[], publicTypes = own) {
  const other = actor === 'p1' ? 'p2' : 'p1';
  assert.deepEqual(result.views[actor]!.self_team.find(p => p.active)!.types, own);
  assert.deepEqual(result.views[other]!.opponent_team.find(p => p.active)!.types, publicTypes);
}
for (const actor of ['p1', 'p2'] as const) {
  test(`Soak ${actor} survives requests, replaces public types, and restores`, async () => {
    const h = await harness(actor);
    try {
      await h.turn('move 1', 'move 1'); activeTypes(h.result, actor, ['Water']);
      assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Water']);
      await h.restore();
      for (let i = 0; i < 2; i++) { await h.turn('move 1'); activeTypes(h.result, actor, ['Water']); }
      await h.turn('move 1', 'move 1'); // Already Water: failure cannot erase public typing.
      assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
      assert.ok(!h.result.log_delta.some(l => l.includes('|typechange|')));
      activeTypes(h.result, actor, ['Water']);
      await h.turn('move 3'); // Shared replacement plumbing; not full Conversion acceptance.
      assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Normal']); activeTypes(h.result, actor, ['Normal']);
      await h.turn('move 1', 'move 1'); activeTypes(h.result, actor, ['Water']);
      await h.restore();
    } finally { await h.close(); }
  });
  for (const exit of ['switch', 'drag', 'faint'] as const) {
    test(`Soak ${actor} ${exit} clears temporary typing and re-entry starts native`, async () => {
      const h = await harness(actor);
      try {
        await h.turn('move 1', 'move 1');
        if (exit === 'switch') await h.turn('switch 2');
        else if (exit === 'drag') await h.turn('move 1', 'move 3');
        else await h.turn('move 2');
        for (const p of ['p1', 'p2'] as const) {
          const team = p === actor ? h.result.views[p]!.self_team : h.result.views[p]!.opponent_team;
          assert.deepEqual(team.find(p => p.name === 'Target')!.types, ['Normal']);
        }
        await h.restore();
        if (exit === 'faint') await h.replacement();
        else { await h.turn('switch 2'); activeTypes(h.result, actor, ['Normal']); }
        await h.restore();
      } finally { await h.close(); }
    });
  }
  for (const tera of ['Fire', 'Stellar']) {
    test(`Soak ${actor} then ${tera} retains underlying types until switch`, async () => {
      const h = await harness(actor, 'Snorlax', tera);
      const expected = tera === 'Stellar' ? ['Water'] : ['Fire'];
      try {
        await h.turn('move 1', 'move 1'); await h.turn('move 1 terastallize');
        assert.deepEqual(h.battle[actor].active[0].getTypes(), expected);
        activeTypes(h.result, actor, expected); await h.restore();
        await h.turn('move 1', 'move 1'); // Tera blocks Soak (including Stellar).
        assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
        activeTypes(h.result, actor, expected);
        await h.turn('switch 2'); await h.turn('switch 2');
        activeTypes(h.result, actor, tera === 'Stellar' ? ['Normal'] : ['Fire']); await h.restore();
      } finally { await h.close(); }
    });
    test(`Soak then ${tera} ${actor} faint resets defensive typing but retains known Tera`, async () => {
      const h = await harness(actor, 'Zoroark', tera);
      const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        await h.turn('move 1', 'move 1'); await h.turn('move 1 terastallize');
        await h.turn('move 2');
        const own = h.result.views[actor]!.self_team.find(p => p.name === 'Target')!;
        const publicTarget = h.result.views[other]!.opponent_team.find(p => p.name === 'Mask')!;
        for (const target of [own, publicTarget]) {
          assert.equal(target.terastallized, false); assert.equal(target.tera_type, tera);
        }
        assert.deepEqual(own.types, ['Dark']); assert.deepEqual(publicTarget.types, ['Normal']);
        assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Mask')!.types, ['Normal']);
        assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
        await h.restore();
      } finally { await h.close(); }
    });
    test(`already ${tera} ${actor} rejects Soak without inventing an override`, async () => {
      const h = await harness(actor, 'Snorlax', tera);
      try {
        await h.turn('move 1 terastallize', 'move 1');
        assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
        assert.ok(!h.result.log_delta.some(l => l.includes('|typechange|')));
        activeTypes(h.result, actor, tera === 'Stellar' ? ['Normal'] : ['Fire']); await h.restore();
      } finally { await h.close(); }
    });
  }
  test(`Soak ${actor} preserves Illusion privacy through reveal and Stellar re-entry`, async () => {
    const h = await harness(actor, 'Zoroark', 'Stellar');
    const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1', 'move 1'); activeTypes(h.result, actor, ['Water']);
      assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
      await h.restore(); await h.turn('move 1 terastallize'); activeTypes(h.result, actor, ['Water']);
      await h.turn('move 1', 'move 4'); // Real damage reveals identity without resetting Soak.
      assert.ok(h.result.log_delta.some(l => l.startsWith('|replace|')));
      activeTypes(h.result, actor, ['Water']); await h.restore();
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Mask')!.types, ['Normal']);
      await h.turn('switch 2'); await h.turn('switch 2');
      activeTypes(h.result, actor, ['Dark'], ['Normal']); await h.restore();
    } finally { await h.close(); }
  });
  test(`Soaked unrevealed Illusion ${actor} drag leaves the teammate unchanged`, async () => {
    const h = await harness(actor, 'Zoroark');
    const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1', 'move 1'); await h.turn('move 1', 'move 3');
      activeTypes(h.result, actor, ['Normal']);
      assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Target')!.types, ['Dark']);
      await h.restore(); await h.turn('switch 2');
      activeTypes(h.result, actor, ['Dark'], ['Normal']); await h.restore();
    } finally { await h.close(); }
  });
  test(`Soaked unrevealed Illusion ${actor} faint uses displayed public native typing`, async () => {
    const h = await harness(actor, 'Zoroark');
    const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1', 'move 1'); await h.turn('move 2');
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Target')!.types, ['Dark']);
      assert.deepEqual(h.result.views[other]!.opponent_team.find(p => p.name === 'Mask')!.types, ['Normal']);
      assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
      await h.restore();
    } finally { await h.close(); }
  });
  test(`Soak ${actor} publishes deterministic private-safe Python-validated records`, async () => {
    const battle = fixture(actor, 'Zoroark', 'Stellar'); const data = structuredClone(battle.toJSON()); battle.destroy();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    try {
      for (const [own, other] of [['move 1', 'move 1'], ['move 1', 'move 2'], ['move 1 terastallize', 'move 2'], ['move 1', 'move 4']]) {
        const c = choices(actor, own, other);
        const results: Awaited<ReturnType<(typeof sessions)[number]["step"]>>[] = [];
        for (const s of sessions) {
          const actions = Object.fromEntries((['p1', 'p2'] as const).map(p => {
            const req = s.boundary.perspectives[p].observation.request!;
            return [p, canonicalActionFromLegalAction(req, req.legal_actions.actions.find(a => a?.choice === c[p])!.index)];
          })) as Parameters<typeof s.step>[0];
          results.push(await s.step(actions));
        }
        assert.deepEqual(results[0], results[1]);
        for (const p of ['p1', 'p2'] as const) {
          const bundle = results[0].record_bundles[p];
          const ownView = bundle.successor_observation.view;
          const target = p === actor ? ownView.self_team.find(p => p.active)! : ownView.opponent_team.find(p => p.active)!;
          assert.deepEqual(target.types, ['Water']);
          const python = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(bundle), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(python.status, 0, python.stderr);
          assert.deepEqual(bundle.successor_observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
        }
      }
    } finally { for (const s of sessions) await s.close(); }
  });
}
for (const species of ['Arceus', 'Silvally']) {
  test(`Soak cannot replace ${species} typing`, async () => {
    const h = await harness('p1', species);
    try {
      await h.turn('move 1', 'move 1');
      assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
      assert.ok(!h.result.log_delta.some(l => l.includes('|typechange|')));
      activeTypes(h.result, 'p1', ['Normal']); await h.restore();
    } finally { await h.close(); }
  });
}
