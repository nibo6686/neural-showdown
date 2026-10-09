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
const CONFIG = { battle_id: 'transform-types', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, species = 'Charizard', tera = 'Fire', targetTera = 'Ghost') {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(`Copier (Mew)
Ability: Synchronize
Tera Type: ${tera}
- Forest's Curse
- Transform
- Soak
- Splash

Reserve (Blissey)
- Splash
`)!;
  const other = Teams.import(`Target (${species})
Ability: ${species === 'Zoroark' ? 'Illusion' : 'Blaze'}
Tera Type: ${targetTera}
- Splash
- Soak
- Whirlwind
- Explosion

Mask (Charizard)
- Splash
`)!;
  battle.setPlayer('p1', { team: actor === 'p1' ? own : other });
  battle.setPlayer('p2', { team: actor === 'p2' ? own : other });
  return battle;
}
function choices(actor: PlayerID, own: string, other = 'move 1') {
  return actor === 'p1' ? { p1: own, p2: other } : { p1: other, p2: own };
}
async function harness(actor: PlayerID, species = 'Charizard', tera = 'Fire', targetTera = 'Ghost') {
  const battle = fixture(actor, species, tera, targetTera);
  const env = new LocalBattleEnv('transform-types', CONFIG.format, SEED);
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
  test(`Transform ${actor} copies three types independently across refresh and restoration`, async () => {
    const h = await harness(actor); const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1');
      const target = JSON.stringify(h.result.views[other]!.self_team.find(p => p.active)!.types);
      await h.turn('move 2'); activeTypes(h.result, actor, ['Fire', 'Flying', 'Grass']);
      assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Fire', 'Flying', 'Grass']);
      assert.equal(JSON.stringify(h.result.views[other]!.self_team.find(p => p.active)!.types), target);
      assert.equal(h.result.views[actor]!.self_team.find(p => p.active)!.species, 'Mew');
      assert.equal(h.result.views[actor]!.self_team.find(p => p.active)!.current_species, 'Charizard');
      await h.restore(); await h.turn('move 1');
      activeTypes(h.result, actor, ['Fire', 'Flying', 'Grass']); await h.restore();
      await h.turn('move 2'); // copied Soak affects original target only
      activeTypes(h.result, actor, ['Fire', 'Flying', 'Grass']);
      assert.deepEqual(h.result.views[other]!.self_team.find(p => p.active)!.types, ['Water']);
      await h.restore(); await h.turn('move 1', 'move 2');
      activeTypes(h.result, actor, ['Water']);
      assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Water']); await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform ${actor} replaces prior copier override and isolates later target Tera`, async () => {
    const h = await harness(actor);
    try {
      await h.turn('move 1', 'move 2'); // copier Water; target Fire/Flying/Grass
      activeTypes(h.result, actor, ['Water']);
      await h.turn('move 2'); activeTypes(h.result, actor, ['Fire', 'Flying', 'Grass']);
      await h.turn('move 1', 'move 1 terastallize');
      activeTypes(h.result, actor, ['Fire', 'Flying', 'Grass']);
      assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Fire', 'Flying', 'Grass']);
      await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform ${actor} own Tera survives switch but clears on faint`, async () => {
    for (const exit of ['switch', 'faint']) {
      const h = await harness(actor); const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        await h.turn('move 1'); await h.turn('move 2 terastallize');
        if (exit === 'switch') await h.turn('switch 2');
        else await h.turn('move 4', 'move 1 terastallize');
        for (const p of ['p1', 'p2'] as const) {
          const copier = (p === actor ? h.result.views[p]!.self_team : h.result.views[p]!.opponent_team).find(p => p.name === 'Copier')!;
          assert.deepEqual(copier.types, exit === 'switch' ? ['Fire'] : ['Psychic']);
          assert.equal(copier.terastallized, exit === 'switch');
          assert.equal(copier.tera_type, 'Fire');
        }
        await h.restore();
        if (exit === 'switch') { await h.turn('switch 2'); activeTypes(h.result, actor, ['Fire']); await h.restore(); }
        assert.ok(h.result.views[other]);
      } finally { await h.close(); }
    }
  });
  for (const exit of ['switch', 'drag', 'faint'] as const) {
    test(`Transform ${actor} ${exit} restores original typing`, async () => {
      const h = await harness(actor); const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        await h.turn('move 1'); await h.turn('move 2');
        if (exit === 'switch') await h.turn('switch 2');
        if (exit === 'drag') await h.turn('move 1', 'move 3');
        if (exit === 'faint') await h.turn('move 4', 'move 1 terastallize');
        for (const p of ['p1', 'p2'] as const) {
          const team = p === actor ? h.result.views[p]!.self_team : h.result.views[p]!.opponent_team;
          const copier = team.find(p => p.name === 'Copier')!;
          assert.deepEqual(copier.types, ['Psychic']); assert.equal(copier.transformed, false);
        }
        await h.restore();
        if (exit !== 'faint') { await h.turn('switch 2'); activeTypes(h.result, actor, ['Psychic']); await h.restore(); }
        else { assert.equal(h.battle[actor].pokemon.find(p => p.name === 'Copier')!.fainted, true); }
        assert.ok(h.result.views[other]);
      } finally { await h.close(); }
    });
  }
  for (const tera of ['Ghost', 'Stellar']) {
    test(`Transform ${actor} ignores target ${tera} and copies known ordinary Water`, async () => {
      const h = await harness(actor, 'Charizard', 'Fire', tera);
      try {
        await h.turn('move 3'); await h.turn('move 2', 'move 1 terastallize');
        activeTypes(h.result, actor, ['Water']);
        assert.deepEqual(h.battle[actor].active[0].getTypes(), ['Water']); await h.restore();
        await h.turn('move 1 terastallize'); activeTypes(h.result, actor, ['Fire']); await h.restore();
      } finally { await h.close(); }
    });
  }
  test(`Transform ${actor} retains own Fire Tera and rejects own Stellar`, async () => {
    for (const tera of ['Fire', 'Stellar']) {
      const h = await harness(actor, 'Charizard', tera);
      try {
        await h.turn('move 1'); await h.turn('move 2 terastallize');
        activeTypes(h.result, actor, tera === 'Fire' ? ['Fire'] : ['Psychic']);
        assert.equal(h.result.log_delta.some(l => l.startsWith('|-transform|')), tera === 'Fire');
        assert.deepEqual(h.battle[actor].active[0].getTypes(), tera === 'Fire' ? ['Fire'] : ['Psychic']);
        await h.restore();
      } finally { await h.close(); }
    }
  });
  test(`Transform ${actor} fails against Illusion without exposing hidden identity`, async () => {
    const h = await harness(actor, 'Zoroark');
    try {
      await h.turn('move 2'); activeTypes(h.result, actor, ['Psychic']);
      assert.ok(!h.result.log_delta.some(l => l.startsWith('|-transform|')));
      assert.ok(!JSON.stringify(h.result.views[actor]!.opponent_team).includes('Zoroark'));
      await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform ${actor} publishes deterministic three-type Python-validated bundles`, async () => {
    const battle = fixture(actor); const data = structuredClone(battle.toJSON()); battle.destroy();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    try {
      for (const [own, expected] of [['move 1', ['Psychic']], ['move 2', ['Fire', 'Flying', 'Grass']], ['move 1', ['Fire', 'Flying', 'Grass']], ['move 2', ['Fire', 'Flying', 'Grass']]] as const) {
        const c = choices(actor, own, 'move 1');
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
