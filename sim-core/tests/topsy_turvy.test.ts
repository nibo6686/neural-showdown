import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { PlayerStateExtractor } from '../src/state_extractor';
import { PUBLIC_STAGES_SCHEMA_VERSION, OBSERVABLE_STATE_SCHEMA_VERSION, validateObservableProtocolPrefix } from '../src/observable_state';
import { opponentPublicBoosts } from '../src/public_boosts';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const SEED = [1, 2, 3, 4];
const CONFIG = { observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION, battle_id: 'topsy-turvy', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, scenario = 'positive') {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(scenario === 'negative' ? `Target (Mew) @ White Herb
Ability: Synchronize
- Shell Smash
- Recycle
- Splash
- Howl
` : `Target (Gengar)
Ability: Pressure
- Shell Smash
- Double Team
- Splash
- Recover
`)!;
  const other = Teams.import(`Source (Mew)
Level: 20
Ability: No Guard
- Topsy-Turvy
- Sand Attack
- Splash
`)!;
  battle.setPlayer('p1', { team: actor === 'p1' ? own : other });
  battle.setPlayer('p2', { team: actor === 'p2' ? own : other });
  return battle;
}
function choices(actor: PlayerID, own: string, other = 'move 1') {
  return actor === 'p1' ? { p1: own, p2: other } : { p1: other, p2: own };
}
async function harness(actor: PlayerID, scenario = 'positive') {
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
const sequences = {
  positive: [['move 3', 'move 1'], ['move 1', 'move 3'], ['move 3', 'move 2'], ['move 3', 'move 1'], ['move 3', 'move 1'], ['move 1', 'move 2'], ['move 3', 'move 1']],
};
for (const actor of ['p1', 'p2'] as const) for (const direction of ['positive'] as const) {
  test(`Topsy-Turvy ${actor}: simulator signs, refresh, exact prefix and restoration`, async () => {
    const h = await harness(actor, direction);
    try {
      let turnIndex = 0;
      for (const [own, foe] of sequences[direction]) {
        await h.turn(own, foe); check(h, actor); await h.restore();
        if (turnIndex++ === 0) {
          assert.ok(h.result.log_delta.some(l => l.startsWith('|-fail|')));
          assert.ok(!h.result.log_delta.some(l => l.startsWith('|-invertboost|')));
        }
        const legacy = projectPipelineStepResult(h.result, CONFIG.battle_id, projectPipelineProtocolPrefix(h.prefix));
        for (const p of ['p1', 'p2'] as const) {
          assert.equal(legacy[p].schema_version, OBSERVABLE_STATE_SCHEMA_VERSION);
          assert.ok(legacy[p].view.opponent_team.every(p => p.public_boosts === undefined && p.boosts === undefined));
        }
      }
      const clears = h.prefix.flatMap((line, i) => line.startsWith('|-invertboost|') ? [i] : []);
      assert.equal(clears.length, 3);
      assert.ok(h.prefix.some(line => line.startsWith('|-fail|')));
      for (const index of clears) {
        const beforePrefix = projectPipelineProtocolPrefix(h.prefix.slice(0, index));
        const afterPrefix = projectPipelineProtocolPrefix(h.prefix.slice(0, index + 1));
        const ident = h.prefix[index].split('|')[2];
        const before = opponentPublicBoosts(beforePrefix, ident);
        assert.equal(before.evasion, 0);
        const expected = Object.fromEntries(Object.entries(before).map(([s, v]) => [s, v === null || v === 0 ? v : -v]));
        assert.deepEqual(opponentPublicBoosts(afterPrefix, ident), expected);
        const source = `${actor === 'p1' ? 'p2' : 'p1'}a: Source`;
        assert.deepEqual(opponentPublicBoosts(afterPrefix, source), opponentPublicBoosts(beforePrefix, source));
        for (const viewer of ['p1', 'p2'] as const) {
          const extractor = new PlayerStateExtractor('prefix', CONFIG.format, viewer);
          extractor.consumeChunk(h.prefix.slice(0, index).join('\n'));
          const earlier = extractor.getView(); const saved = JSON.stringify(earlier);
          extractor.consumeChunk(h.prefix[index]);
          const view = extractor.getView();
          assert.deepEqual(stages((viewer === actor ? view.self_team : view.opponent_team).find(p => p.active)!.boosts), expected);
          assert.equal(JSON.stringify(earlier), saved);
        }
      }
    } finally { await h.close(); }
  });
  test(`Topsy-Turvy ${actor}: actual v2 records repeat and Python validates`, async () => {
    const battle = fixture(actor, direction); const data = structuredClone(battle.toJSON());
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    const saved: { value: unknown; json: string }[] = [];
    try {
      for (const [own, foe] of sequences[direction]) {
        const c = choices(actor, own, foe); battle.makeChoices(c.p1, c.p2);
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
          const other = p === 'p1' ? 'p2' : 'p1';
          assert.deepEqual(view.opponent_team.find(p => p.active)!.public_boosts, stages(battle[other].active[0].boosts));
          assert.ok(view.opponent_team.every(p => p.boosts === undefined && p.stats === undefined));
          const python = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(bundle), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(python.status, 0, python.stderr);
          assert.deepEqual(bundle.successor_observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
          saved.push({value: bundle, json: JSON.stringify(bundle)});
        }
        for (const f of saved) assert.equal(JSON.stringify(f.value), f.json);
      }
    } finally { battle.destroy(); for (const s of sessions) await s.close(); }
  });
}
for (const actor of ['p1','p2'] as const) test(`Topsy-Turvy ${actor}: sparse unknowns and explicit zero`,()=>{
 const id=`${actor}a: Unknown`;
 const prefix=[`|-setboost|${id}|atk|2`,`|-setboost|${id}|def|-1`,`|-setboost|${id}|spe|0`];
 const old=opponentPublicBoosts(prefix,id);prefix.push(`|-invertboost|${id}|[from] move: Topsy-Turvy`);
 const expected={atk:-2,def:1,spa:null,spd:null,spe:0,accuracy:null,evasion:null};
 assert.deepEqual(opponentPublicBoosts(prefix,id),expected);
 const e=new PlayerStateExtractor('unknown',CONFIG.format,actor);e.consumeChunk(prefix.join('\n'));assert.deepEqual(e.getView().self_team[0].boosts,{atk:-2,def:1,spe:0});
 const py=spawnSync(process.env.PYTHON||'python3',['-c','import json,sys; from neural.public_boosts import public_boost_evidence; print(json.dumps(public_boost_evidence(json.load(sys.stdin))))'],{input:JSON.stringify(prefix),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')}});assert.equal(py.status,0,py.stderr);assert.deepEqual(JSON.parse(py.stdout)[`${actor}: Unknown`],expected);
 prefix.push(`|-invertboost|${id}|[from] move: Topsy-Turvy`);assert.deepEqual(opponentPublicBoosts(prefix,id),old);
});
