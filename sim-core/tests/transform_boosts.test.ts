import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { PlayerStateExtractor } from '../src/state_extractor';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import type { PlayerID, StepResult } from '../src/types';
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const SEED = [1, 2, 3, 4];
const CONFIG = { battle_id: 'transform-boosts', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, scenario = 'mixed') {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const ownMoves = scenario === 'zero' ? ['Growl', 'Transform', 'Calm Mind', 'Splash'] : ['Splash', 'Transform', 'Calm Mind', 'Sand Attack'];
  const targetMoves = scenario === 'zero' ? ['Growth', 'Splash', 'Whirlwind', 'Explosion']
    : scenario === 'mixed' ? ['Shell Smash', 'Double Team', 'Swords Dance', 'Splash']
    : ['Swords Dance', 'Splash', 'Whirlwind', 'Explosion'];
  const own = Teams.import(`Copier (Mew)
Ability: Synchronize
${ownMoves.map(m => '- ' + m).join('\n')}

Reserve (Blissey)
- Splash
`)!;
  const other = Teams.import(`Target (${scenario === 'illusion' ? 'Zoroark' : 'Gengar'})
Ability: ${scenario === 'illusion' ? 'Illusion' : scenario === 'intimidate' ? 'Intimidate' : 'Cursed Body'}
${targetMoves.map(m => '- ' + m).join('\n')}

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
async function harness(actor: PlayerID, scenario = 'mixed') {
  const battle = fixture(actor, scenario);
  const env = new LocalBattleEnv('transform-boosts', CONFIG.format, SEED);
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
    get prefix() { return [...prefix]; },
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
const STAGES = ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'] as const;
function stages(boosts: Partial<Record<string, number>>) { return Object.fromEntries(STAGES.map(k => [k, boosts[k] || 0])); }
function check(h: Awaited<ReturnType<typeof harness>>, actor: PlayerID) {
  const other = actor === 'p1' ? 'p2' : 'p1';
  for (const who of [actor, other] as PlayerID[]) {
    const oracle = stages(h.battle[who].active[0].boosts);
    assert.deepEqual(stages(h.result.views[who]!.self_team.find(p => p.active)!.boosts), oracle);
    const viewer = who === 'p1' ? 'p2' : 'p1';
    assert.deepEqual(stages(h.result.views[viewer]!.opponent_team.find(p => p.active)!.boosts), oracle);
  }
}
for (const actor of ['p1', 'p2'] as const) {
  test(`Transform boosts ${actor} replaces prior caller boosts with +2 Attack and implicit zeros`, async () => {
    const h = await harness(actor, 'attack');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 2', 'move 2'); check(h, actor);
      const copied = h.result.views[actor]!.self_team.find(p => p.active)!.boosts;
      assert.deepEqual(copied, { atk: 2 });
      await h.restore(); await h.turn('move 2', 'move 2'); check(h, actor); await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform boosts ${actor} copies mixed seven stages once and isolates later changes`, async () => {
    const h = await harness(actor); const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 4', 'move 2');
      const targetBefore = { ...h.battle[other].active[0].boosts };
      await h.turn('move 2', 'move 4'); check(h, actor);
      assert.deepEqual(stages(h.result.views[actor]!.self_team.find(p => p.active)!.boosts), { atk: 2, def: -1, spa: 2, spd: -1, spe: 2, accuracy: -1, evasion: 1 });
      assert.deepEqual(h.battle[other].active[0].boosts, targetBefore);
      await h.restore(); await h.turn('move 4', 'move 1'); check(h, actor);
      assert.deepEqual(h.battle[actor].active[0].boosts, targetBefore); await h.restore();
      const targetLater = { ...h.battle[other].active[0].boosts };
      await h.turn('move 1', 'move 4'); check(h, actor);
      assert.deepEqual(h.battle[other].active[0].boosts, targetLater); await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform boosts ${actor} copies explicit zero and clears absent caller stages`, async () => {
    const h = await harness(actor, 'zero');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 1', 'move 2');
      await h.turn('move 2', 'move 2'); check(h, actor);
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.active)!.boosts, { atk: 0, spa: 1 });
      await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform boosts ${actor} applies following copied-ability stage event once`, async () => {
    const h = await harness(actor, 'intimidate'); const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      await h.turn('move 1', 'move 1'); await h.turn('move 2', 'move 2'); check(h, actor);
      assert.equal(h.battle[actor].active[0].boosts.atk, 2);
      assert.equal(h.battle[other].active[0].boosts.atk, 1);
      const copyIndex = h.result.log_delta.findIndex(l => l.startsWith('|-transform|'));
      const deltaIndex = h.result.log_delta.findIndex(l => l.startsWith('|-unboost|'));
      assert.ok(copyIndex >= 0 && deltaIndex > copyIndex);
      const copyEnd = h.prefix.findIndex(l => l.startsWith('|-transform|')) + 1;
      for (const viewer of ['p1', 'p2'] as const) {
        const projection = new PlayerStateExtractor('copy-prefix', CONFIG.format, viewer);
        projection.consumeChunk(h.prefix.slice(0, copyEnd).join('\n'));
        const atCopy = projection.getView();
        assert.equal((viewer === actor ? atCopy.self_team : atCopy.opponent_team).find(p => p.active)!.boosts.atk, 2);
        assert.equal((viewer === other ? atCopy.self_team : atCopy.opponent_team).find(p => p.active)!.boosts.atk, 2);
        const earlier = JSON.stringify(atCopy);
        projection.consumeChunk(h.prefix.slice(copyEnd).join('\n'));
        const after = projection.getView();
        assert.equal((viewer === other ? after.self_team : after.opponent_team).find(p => p.active)!.boosts.atk, 1);
        assert.equal(JSON.stringify(atCopy), earlier);
      }
      await h.restore();
    } finally { await h.close(); }
  });
  for (const exit of ['switch', 'drag', 'faint'] as const) {
    test(`Transform boosts ${actor} clears on ${exit}`, async () => {
      const h = await harness(actor, 'attack');
      try {
        await h.turn('move 1', 'move 1'); await h.turn('move 2', 'move 2');
        if (exit === 'switch') await h.turn('switch 2', 'move 2');
        if (exit === 'drag') await h.turn('move 2', 'move 3');
        if (exit === 'faint') await h.turn('move 4', 'move 2'); // Ghost target survives Explosion.
        for (const p of ['p1', 'p2'] as const) {
          const team = p === actor ? h.result.views[p]!.self_team : h.result.views[p]!.opponent_team;
          assert.deepEqual(team.find(p => p.name === 'Copier')!.boosts, {});
        }
        await h.restore();
        if (exit !== 'faint') { await h.turn('switch 2', 'move 2'); check(h, actor); await h.restore(); }
      } finally { await h.close(); }
    });
  }
  test(`Transform boosts ${actor} failed hidden Illusion copy preserves caller evidence`, async () => {
    const h = await harness(actor, 'illusion');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 2', 'move 2'); check(h, actor);
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.active)!.boosts, { spa: 1, spd: 1 });
      assert.ok(!h.result.log_delta.some(l => l.startsWith('|-transform|')));
      assert.ok(!JSON.stringify(h.result.views[actor]!.opponent_team).includes('Zoroark')); await h.restore();
    } finally { await h.close(); }
  });
  test(`Transform boosts ${actor} deterministic private-safe Python publication`, async () => {
    const battle = fixture(actor); const data = structuredClone(battle.toJSON()); battle.destroy();
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    try {
      let i = 0;
      for (const [own, other] of [['move 3', 'move 1'], ['move 4', 'move 2'], ['move 2', 'move 4'], ['move 4', 'move 1'], ['move 1', 'move 4']]) {
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
          assert.ok(view.opponent_team.every(p => p.boosts === undefined));
          if (p === actor && (i === 2 || i === 3)) assert.deepEqual(stages(view.self_team.find(p => p.active)!.boosts!), { atk: 2, def: -1, spa: 2, spd: -1, spe: 2, accuracy: -1, evasion: 1 });
          const python = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(bundle), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(python.status, 0, python.stderr);
          assert.deepEqual(bundle.successor_observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
        }
        i++;
      }
    } finally { for (const s of sessions) await s.close(); }
  });
}
