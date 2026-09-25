import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { PlayerStateExtractor } from '../src/state_extractor';
import { PUBLIC_STAGES_SCHEMA_VERSION, OBSERVABLE_STATE_SCHEMA_VERSION, projectObservableBattleState } from '../src/observable_state';
import { opponentPublicBoosts } from '../src/public_boosts';
import { projectBeliefState } from '../src/belief_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import { illusionBattle, lifecycleChoices } from './helpers/state_lifecycle';
import type { PlayerID, StepResult } from '../src/types';
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const SEED = [1, 2, 3, 4];
const CONFIG = { observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION, battle_id: 'transform-boosts', format: 'gen9randombattle', seed: SEED };
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
    const observation = projectPipelineStepResult(result, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix), PUBLIC_STAGES_SCHEMA_VERSION);
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
        assert.deepEqual(projectPipelineStepResult(step, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix), PUBLIC_STAGES_SCHEMA_VERSION), frames.at(-1)!.observation);
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
    const published = projectPipelineStepResult(h.result, CONFIG.battle_id, projectPipelineProtocolPrefix(h.prefix), PUBLIC_STAGES_SCHEMA_VERSION);
    assert.deepEqual(published[viewer].view.opponent_team.find(p => p.active)!.public_boosts, oracle);
  }
}
for (const actor of ['p1', 'p2'] as const) {
  test(`Published v2 stages ${actor} replaces prior caller boosts with +2 Attack and implicit zeros`, async () => {
    const h = await harness(actor, 'attack');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 2', 'move 2'); check(h, actor);
      const copied = h.result.views[actor]!.self_team.find(p => p.active)!.boosts;
      assert.deepEqual(copied, { atk: 2 });
      await h.restore(); await h.turn('move 2', 'move 2'); check(h, actor); await h.restore();
    } finally { await h.close(); }
  });
  test(`Published v2 stages ${actor} copies mixed seven stages once and isolates later changes`, async () => {
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
  test(`Published v2 stages ${actor} copies explicit zero and clears absent caller stages`, async () => {
    const h = await harness(actor, 'zero');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 1', 'move 2');
      await h.turn('move 2', 'move 2'); check(h, actor);
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.active)!.boosts, { atk: 0, spa: 1 });
      await h.restore();
    } finally { await h.close(); }
  });
  test(`Published v2 stages ${actor} applies following copied-ability stage event once`, async () => {
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
    test(`Published v2 stages ${actor} clears on ${exit}`, async () => {
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
  test(`Published v2 stages ${actor} failed hidden Illusion copy preserves caller evidence`, async () => {
    const h = await harness(actor, 'illusion');
    try {
      await h.turn('move 3', 'move 1'); await h.turn('move 2', 'move 2'); check(h, actor);
      assert.deepEqual(h.result.views[actor]!.self_team.find(p => p.active)!.boosts, { spa: 1, spd: 1 });
      assert.ok(!h.result.log_delta.some(l => l.startsWith('|-transform|')));
      assert.ok(!JSON.stringify(h.result.views[actor]!.opponent_team).includes('Zoroark')); await h.restore();
    } finally { await h.close(); }
  });
  test(`Published v2 stages ${actor} deterministic private-safe Python publication`, async () => {
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
          assert.ok(view.opponent_team.every(p => Object.keys(p.public_boosts!).length === 7));
          if (p !== actor && (i === 2 || i === 3)) assert.deepEqual(view.opponent_team.find(p => p.active)!.public_boosts, { atk: 2, def: -1, spa: 2, spd: -1, spe: 2, accuracy: -1, evasion: 1 });
          if (p === actor && (i === 2 || i === 3)) assert.deepEqual(stages(view.self_team.find(p => p.active)!.boosts!), { atk: 2, def: -1, spa: 2, spd: -1, spe: 2, accuracy: -1, evasion: 1 });
          const python = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(bundle), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(python.status, 0, python.stderr);
          assert.equal(JSON.parse(python.stdout).schema_fingerprints.observation, PUBLIC_STAGES_SCHEMA_VERSION);
          if (i === 2 && p !== actor) {
            for (const mutation of ['stage', 'version', 'mixed', 'private', 'reference']) {
              const bad = structuredClone(bundle);
              if (mutation === 'stage') bad.successor_observation.view.opponent_team.find(p => p.active)!.public_boosts!.atk = 6;
              if (mutation === 'version') (bad.successor_observation as any).schema_version = 'observable-battle-state/v999';
              if (mutation === 'mixed') (bad.successor_observation as any).schema_version = OBSERVABLE_STATE_SCHEMA_VERSION;
              if (mutation === 'private') (bad.successor_observation.view.opponent_team[0] as any).stats = { atk: 999 };
              if (mutation === 'reference') (bad.successor_belief.observation as any).schema_version = OBSERVABLE_STATE_SCHEMA_VERSION;
              const rejected = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
                input: JSON.stringify(bad), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
              });
              assert.notEqual(rejected.status, 0, mutation);
            }
          }
          assert.deepEqual(bundle.successor_observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
        }
        i++;
      }
    } finally { for (const s of sessions) await s.close(); }
  });
}

test('v2 stages require public baseline, ignore supplied future boosts, and preserve v1 projection', async () => {
  const h = await harness('p1', 'attack');
  try {
    const prefix = projectPipelineProtocolPrefix(h.prefix);
    const input = { schema_version: OBSERVABLE_STATE_SCHEMA_VERSION, source_kind: 'sim_core' as const,
      battle_id: CONFIG.battle_id, perspective: 'p1' as const, snapshot_phase: 'pre_decision', protocol_prefix: prefix,
      view: h.result.views.p1!, request: h.result.requests.p1! };
    const v1 = projectObservableBattleState(input);
    const v2 = projectObservableBattleState({ ...input, schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
    assert.notEqual(v1.observation_id, v2.observation_id);
    assert.equal(v1.view.opponent_team[0].public_boosts, undefined);
    assert.deepEqual(v2.view.opponent_team[0].public_boosts, stages({}));
    const poisoned = structuredClone(input);
    poisoned.view.opponent_team[0].boosts = { atk: 6, def: -6 };
    poisoned.view.opponent_team[0].stats = { atk: 999 };
    assert.deepEqual(projectObservableBattleState({ ...poisoned, schema_version: PUBLIC_STAGES_SCHEMA_VERSION }), v2);
    assert.deepEqual(projectObservableBattleState(input), v1);
    const before = JSON.stringify(v2);
    await h.turn('move 1', 'move 1');
    const later = projectPipelineStepResult(h.result, CONFIG.battle_id, projectPipelineProtocolPrefix(h.prefix), PUBLIC_STAGES_SCHEMA_VERSION);
    assert.equal(later.p1.view.opponent_team[0].public_boosts!.atk, 2);
    assert.equal(JSON.stringify(v2), before);
    assert.throws(() => projectObservableBattleState({ ...input, schema_version: 'observable-battle-state/v999' }), /Unsupported/);
    assert.throws(() => projectBeliefState({ observation: v2, parent: projectBeliefState({ observation: v1 }) }), /Cross-version/);
    assert.throws(() => projectBeliefState({ observation: { ...v2, view: { ...v2.view, opponent_team: v2.view.opponent_team.map(p => ({ ...p, public_boosts: { ...p.public_boosts!, atk: 6 } })) } } }), /stages/);
    assert.deepEqual(opponentPublicBoosts([], 'p2a: Target'), Object.fromEntries(STAGES.map(s => [s, null])));
    assert.equal(opponentPublicBoosts(['|-boost|p2a: Target|atk|2'], 'p2a: Target').atk, null);
    assert.equal(opponentPublicBoosts(['|-setboost|p2a: Target|atk|0'], 'p2a: Target').atk, 0);
    assert.equal(opponentPublicBoosts(['|-setboost|p2a: Target|atk|-6', '|boost|p2a: Target|atk|12'], 'p2a: Target').atk, 6);
    for (const line of ['|-copyboost|p2a: Target|p1a: Copier', '|-swapboost|p1a: Copier|p2a: Target', '|move|p1a: Copier|Baton Pass|p1a: Copier']) {
      assert.throws(() => opponentPublicBoosts([...prefix, line], 'p2a: Target'), /Unsupported/);
    }
  } finally { await h.close(); }
});

for (const actor of ['p1', 'p2'] as const) {
  test(`v2 public stages ${actor} reconcile Illusion reveal without changing teammate or earlier prefixes`, async () => {
    const battle = illusionBattle(actor, true);
    const env = new LocalBattleEnv('public-illusion', CONFIG.format, SEED);
    const restored = new LocalBattleEnv('public-illusion-restore', CONFIG.format, SEED);
    const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      let result = await env.resetFromSerialized(battle.toJSON(), OPTIONS);
      const prefix = [...result.log_delta];
      const frames: { value: unknown; json: string }[] = [];
      const step = async (own: string, foe = 'move 1') => {
        result = await env.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
        prefix.push(...result.log_delta);
        const obs = projectPipelineStepResult(result, 'public-illusion', projectPipelineProtocolPrefix(prefix), PUBLIC_STAGES_SCHEMA_VERSION);
        frames.push({ value: obs, json: JSON.stringify(obs) });
        const replay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
        assert.deepEqual(projectPipelineStepResult(replay, 'public-illusion', projectPipelineProtocolPrefix(replay.log_delta), PUBLIC_STAGES_SCHEMA_VERSION), obs);
        for (const frame of frames) assert.equal(JSON.stringify(frame.value), frame.json);
        return obs;
      };
      await step('move 1'); await step('switch 2');
      const hidden = await step('move 1');
      assert.ok(hidden[other].view.opponent_team.every(p => p.name !== 'Fox' && p.species !== 'Zoroark'));
      assert.equal(hidden[other].view.opponent_team.find(p => p.active)!.public_boosts!.spa, 2);
      const revealed = await step('move 3', 'move 2');
      assert.equal(revealed[other].view.opponent_team.find(p => p.name === 'Fox')!.public_boosts!.spa, 2);
      assert.deepEqual(revealed[other].view.opponent_team.find(p => p.name === 'Mask')!.public_boosts, stages({}));
      const departed = await step('switch 2');
      assert.deepEqual(departed[other].view.opponent_team.find(p => p.name === 'Fox')!.public_boosts, stages({}));
    } finally { battle.destroy(); await env.close(); await restored.close(); }
  });
}
