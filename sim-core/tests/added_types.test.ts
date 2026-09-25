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
const CONFIG = { battle_id: 'added-types', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, species = 'Charizard', tera = 'Fire', reveal = false) {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(`Target (${species})
Ability: ${species === 'Zoroark' ? 'Illusion' : 'Blaze'}
Tera Type: ${tera}
- Splash
- Explosion
- Recover

Mask (Charizard)
Ability: Immunity
- Splash
`)!;
  const other = Teams.import(`Soaker (Mew)
Ability: Pressure
- Soak
- Forest's Curse
- Trick-or-Treat
- ${reveal ? 'Swift' : 'Whirlwind'}

Reserve (Blissey)
- Splash
`)!;
  battle.setPlayer('p1', { team: actor === 'p1' ? own : other });
  battle.setPlayer('p2', { team: actor === 'p2' ? own : other });
  return battle;
}
function choices(actor: PlayerID, own: string, other = 'move 1') {
  return actor === 'p1' ? { p1: own, p2: other } : { p1: other, p2: own };
}
async function harness(actor: PlayerID, species = 'Charizard', tera = 'Fire', reveal = false) {
  const battle = fixture(actor, species, tera, reveal);
  const env = new LocalBattleEnv('added-types', CONFIG.format, SEED);
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
    async turn(own: string, other = 'move 1') {
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
  test(`added types ${actor}: three types, repetition, replacement and Soak ordering`, async () => {
    const h = await harness(actor);
    try {
      for (const [move, expected] of [
        ['move 2', ['Fire', 'Flying', 'Grass']], // native + added
        ['move 2', ['Fire', 'Flying', 'Grass']], // same added type fails
        ['move 3', ['Fire', 'Flying', 'Ghost']], // replaces Grass, not a fourth type
        ['move 1', ['Water']], // setType removes added slot
        ['move 2', ['Water', 'Grass']], // original reproduction
        ['move 2', ['Water', 'Grass']], // fresh request after failed repetition
        ['move 1', ['Water']],
      ] as const) {
        await h.turn('move 1', move);
        assert.deepEqual(h.battle[actor].active[0].getTypes(), expected);
        activeTypes(h.result, actor, [...expected]); await h.restore();
      }
    } finally { await h.close(); }
  });
  for (const exit of ['switch', 'drag', 'faint'] as const) {
    test(`added types ${actor} clears on ${exit}`, async () => {
      const h = await harness(actor);
      const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        await h.turn('move 1', 'move 2');
        if (exit === 'switch') await h.turn('switch 2', 'switch 2');
        if (exit === 'drag') await h.turn('move 1', 'move 4');
        if (exit === 'faint') await h.turn('move 2', 'move 2');
        assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Target')!.types, ['Fire', 'Flying']);
        assert.deepEqual(h.result.views[other]!.opponent_team.find(p => p.name === 'Target')!.types, ['Fire', 'Flying']);
        await h.restore();
        if (exit === 'faint') await h.replacement();
        else {
          await h.turn('switch 2', exit === 'switch' ? 'move 1' : 'switch 2');
          activeTypes(h.result, actor, ['Fire', 'Flying']);
        }
        await h.restore();
      } finally { await h.close(); }
    });
  }
  for (const tera of ['Fire', 'Stellar']) {
    test(`added types ${actor} ${tera} removes addition and prevents reapplication`, async () => {
      const h = await harness(actor, 'Charizard', tera);
      try {
        await h.turn('move 1', 'move 1'); await h.turn('move 1', 'move 2');
        activeTypes(h.result, actor, ['Water', 'Grass']);
        await h.turn('move 1 terastallize', 'move 3');
        assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
        const expected = tera === 'Stellar' ? ['Water'] : ['Fire'];
        activeTypes(h.result, actor, expected);
        assert.deepEqual(h.battle[actor].active[0].getTypes(), expected); await h.restore();
        await h.turn('move 2', 'move 2');
        assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Target')!.types, ['Fire', 'Flying']);
        await h.restore();
      } finally { await h.close(); }
    });
  }
  test(`added types ${actor} Illusion reveal preserves evidence and teammate privacy`, async () => {
    const h = await harness(actor, 'Zoroark', 'Fire', true);
    const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1', 'move 2');
      activeTypes(h.result, actor, ['Dark', 'Grass'], ['Fire', 'Flying', 'Grass']);
      assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Mask')!.types, ['Fire', 'Flying']);
      await h.restore(); await h.turn('move 1', 'move 4');
      assert.ok(h.result.log_delta.some(l => l.startsWith('|replace|')));
      activeTypes(h.result, actor, ['Dark', 'Grass']); await h.restore();
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Mask')!.types, ['Fire', 'Flying']);
    } finally { await h.close(); }
  });
  for (const exit of ['drag', 'faint'] as const) {
    test(`added types ${actor} unrevealed Illusion ${exit} preserves roster privacy`, async () => {
      const h = await harness(actor, 'Zoroark');
      const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        await h.turn('move 1', 'move 2');
        await h.turn(exit === 'faint' ? 'move 2' : 'move 1', exit === 'faint' ? 'move 2' : 'move 4');
        assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Target')!.types, ['Dark']);
        assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.name === 'Mask')!.types, ['Fire', 'Flying']);
        assert.ok(!JSON.stringify(h.result.views[other]!.opponent_team).includes('Zoroark'));
        assert.deepEqual(h.result.views[other]!.opponent_team.find(p => p.name === 'Mask')!.types, ['Fire', 'Flying']);
        await h.restore();
      } finally { await h.close(); }
    });
  }
  test(`added types ${actor} deterministic three-type Python publication`, async () => {
    const battle = fixture(actor, 'Charizard', 'Stellar'); const data = structuredClone(battle.toJSON()); battle.destroy();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    try {
      for (const [own, other, expected] of [
        ['move 1', 'move 2', ['Fire', 'Flying', 'Grass']],
        ['move 1', 'move 3', ['Fire', 'Flying', 'Ghost']],
        ['move 1', 'move 1', ['Water']],
        ['move 1', 'move 2', ['Water', 'Grass']],
        ['move 1 terastallize', 'move 2', ['Water']],
      ] as const) {
        const c = choices(actor, own, other);
        const results: Awaited<ReturnType<(typeof sessions)[number]['step']>>[] = [];
        for (const s of sessions) {
          const actions = Object.fromEntries((['p1', 'p2'] as const).map(p => {
            const req = s.boundary.perspectives[p].observation.request!;
            return [p, canonicalActionFromLegalAction(req, req.legal_actions.actions.find(a => a?.choice === c[p])!.index)];
          })) as Parameters<typeof s.step>[0];
          results.push(await s.step(actions));
        }
        assert.deepEqual(results[0], results[1]);
        for (const p of ['p1', 'p2'] as const) {
          const bundle = results[0].record_bundles[p]; const view = bundle.successor_observation.view;
          assert.deepEqual((p === actor ? view.self_team : view.opponent_team).find(p => p.active)!.types, expected);
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
