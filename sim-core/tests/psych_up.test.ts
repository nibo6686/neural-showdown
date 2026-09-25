import { createHash } from 'node:crypto';
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
import { projectBeliefState } from '../src/belief_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const SEED = [1, 2, 3, 4];
const CONFIG = { observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION, battle_id: 'psych-up', format: 'gen9randombattle', seed: SEED };
function fixture(actor: PlayerID, scenario = 'mixed') {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const ownMoves = scenario === 'zero' ? ['Growl', 'Psych Up', 'Calm Mind', 'Splash'] : ['Splash', 'Psych Up', 'Calm Mind', 'Sand Attack'];
  const targetMoves = scenario === 'zero' ? ['Growth', 'Splash', 'Whirlwind', 'Explosion']
    : scenario === 'mixed' ? ['Shell Smash', 'Double Team', 'Swords Dance', 'Splash']
    : ['Swords Dance', 'Splash', 'Whirlwind', 'Explosion'];
  const own = Teams.import(`Copier (Mew)
Ability: No Guard
${ownMoves.map(m => '- ' + m).join('\n')}

Reserve (Blissey)
- Splash
`)!;
  const other = Teams.import(`Target (${scenario === 'illusion' ? 'Zoroark' : 'Gengar'})
Ability: ${scenario === 'illusion' ? 'Illusion' : scenario === 'intimidate' ? 'Intimidate' : 'Pressure'}
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
  const env = new LocalBattleEnv('psych-up', CONFIG.format, SEED);
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
function canonical(v: any): string {
  return Array.isArray(v) ? '['+v.map(canonical).join(',')+']' : v && typeof v === 'object' ? '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}' : JSON.stringify(v);
}
const hash=(v:any)=>createHash('sha256').update(canonical(v)).digest('hex');
const sequences = {
  mixed: [['move 3', 'move 1'], ['move 4', 'move 2'], ['move 2', 'move 4'], ['move 4', 'move 3'], ['move 3', 'move 4'], ['move 2', 'move 4'], ['move 2', 'move 4']],
  zero: [['move 3', 'move 1'], ['move 1', 'move 2'], ['move 2', 'move 2']],
};
for (const actor of ['p1', 'p2'] as const) for (const scenario of ['mixed', 'zero'] as const) {
  test(`Psych Up ${actor} ${scenario}: replacement, independence, refresh, restore, exact prefixes`, async () => {
    const h = await harness(actor, scenario); const other = actor === 'p1' ? 'p2' : 'p1';
    try {
      for (const [own, foe] of sequences[scenario]) {
        await h.turn(own, foe); check(h, actor); await h.restore();
        const legacy = projectPipelineStepResult(h.result, CONFIG.battle_id, projectPipelineProtocolPrefix(h.prefix));
        assert.ok(legacy[other].view.opponent_team.every(p => p.public_boosts === undefined));
      }
      const indices = h.prefix.flatMap((line,i) => line.startsWith('|-copyboost|') ? [i] : []);
      assert.equal(indices.length, scenario === 'mixed' ? 3 : 1);
      for (const i of indices) {
        const parts=h.prefix[i].split('|'); assert.equal(parts[4], '[from] move: Psych Up');
        const before=projectPipelineProtocolPrefix(h.prefix.slice(0,i));
        const after=projectPipelineProtocolPrefix(h.prefix.slice(0,i+1));
        const expected=opponentPublicBoosts(before,parts[3]);
        if (i === indices[0]) assert.deepEqual(expected, scenario === 'mixed'
          ? {atk:2,def:-1,spa:2,spd:-1,spe:2,accuracy:-1,evasion:1}
          : {atk:0,def:0,spa:1,spd:0,spe:0,accuracy:0,evasion:0});
        assert.deepEqual(opponentPublicBoosts(after,parts[2]),expected);
        assert.deepEqual(opponentPublicBoosts(after,parts[3]),expected);
        for (const viewer of ['p1','p2'] as const) {
          const extractor=new PlayerStateExtractor('copy-prefix', CONFIG.format, viewer);
          extractor.consumeChunk(h.prefix.slice(0,i).join('\n'));
          const earlier=extractor.getView(), saved=JSON.stringify(earlier);
          extractor.consumeChunk(h.prefix[i]);
          const view=extractor.getView();
          assert.deepEqual(stages((viewer===actor ? view.self_team : view.opponent_team).find(p=>p.active)!.boosts),expected);
          extractor.consumeChunk(h.prefix.slice(i+1).join('\n'));
          assert.equal(JSON.stringify(earlier),saved);
        }
      }
    } finally { await h.close(); }
  });
}
for (const actor of ['p1', 'p2'] as const) {
  test(`Psych Up ${actor}: actual v2 records repeat and Python validates`, async () => {
    const battle = fixture(actor); const data = structuredClone(battle.toJSON());
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(data, o); };
      sessions.push(await createPipelineIntegrationSession(CONFIG), await createPipelineIntegrationSession(CONFIG));
    } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
    const saved: { value: unknown; json: string }[] = [];
    try {
      for (const [own, foe] of sequences.mixed) {
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
          if (bundle.successor_observation.protocol_prefix.some(l => l.startsWith('|-copyboost|'))) {
            const bad: any = structuredClone(bundle);
            const o = bad.successor_observation;
            o.view.opponent_team.find((p: any) => p.active).public_boosts.atk = 6;
            const old = o.observation_id;
            const next = 'obs-' + hash(Object.fromEntries(Object.entries(o).filter(([k]) => !['observation_id', 'protocol_prefix'].includes(k))));
            const replace = (x: any, old: string, next: string): any => Array.isArray(x) ? x.map(v => replace(v, old, next)) : x && typeof x === 'object' ? Object.fromEntries(Object.entries(x).map(([k,v]) => [k,replace(v,old,next)])) : x === old ? next : x;
            let falseBundle = replace(bad, old, next);
            const belief = falseBundle.successor_belief;
            falseBundle = replace(falseBundle, belief.belief_id, 'belief-' + hash(Object.fromEntries(Object.entries(belief).filter(([k]) => k !== 'belief_id'))));
            assert.throws(() => projectBeliefState({observation:falseBundle.successor_observation, parent:falseBundle.input_belief}), /stages/);
            const rejected = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
              input: JSON.stringify(falseBundle), encoding:'utf8', env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')},
            });
            assert.equal(rejected.status,2,rejected.stderr); assert.equal(rejected.stdout,''); assert.match(rejected.stderr,/exact prefix/);
          }
          assert.deepEqual(bundle.successor_observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
          saved.push({value: bundle, json: JSON.stringify(bundle)});
        }
        for (const f of saved) assert.equal(JSON.stringify(f.value), f.json);
      }
    } finally { battle.destroy(); for (const s of sessions) await s.close(); }
  });
}

for (const actor of ['p1','p2'] as const) test(`Psych Up ${actor}: incomplete public evidence overwrites stale stages without invented zero`, () => {
  const other=actor==='p1'?'p2':'p1'; const caller=`${actor}a: Caller`, donor=`${other}a: Donor`;
  const prefix=[`|-setboost|${caller}|atk|6`,`|-setboost|${caller}|spa|4`, `|-setboost|${donor}|atk|-2`, `|-setboost|${donor}|spe|0`, `|-copyboost|${caller}|${donor}|[from] move: Psych Up`];
  const expected={atk:-2,def:null,spa:null,spd:null,spe:0,accuracy:null,evasion:null};
  assert.deepEqual(opponentPublicBoosts(prefix,caller),expected);
  const original=opponentPublicBoosts(prefix,caller);
  prefix.push(`|-boost|${donor}|atk|1`,`|-setboost|${caller}|def|2`);
  assert.deepEqual(opponentPublicBoosts(prefix,caller),{...expected,def:2});
  assert.equal(opponentPublicBoosts(prefix,donor).atk,-1); assert.deepEqual(original,expected);
  const python=spawnSync(process.env.PYTHON || 'python3',['-c','import json,sys; from neural.public_boosts import public_boost_evidence; print(json.dumps(public_boost_evidence(json.load(sys.stdin))))'],{
    input:JSON.stringify(prefix),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')},
  });
  assert.equal(python.status,0,python.stderr);assert.deepEqual(JSON.parse(python.stdout)[`${actor}: Caller`],{...expected,def:2});
  const extractor=new PlayerStateExtractor('incomplete',CONFIG.format,actor);extractor.consumeChunk(prefix.join('\n'));
  assert.deepEqual(extractor.getView().self_team[0].boosts,{atk:-2,spe:0,def:2});
});
test('Psych Up supports only its exact copy tag; Costar, missing and extra fields reject', () => {
  const good='|-copyboost|p1a: Caller|p2a: Donor|[from] move: Psych Up';
  validateObservableProtocolPrefix([good],'p1');
  for(const line of [good.replace('Psych Up','Other'),good.replace('[from] move: Psych Up','[from] ability: Costar'),good+'|extra',good.replace('|[from] move: Psych Up','')]) {
    assert.throws(()=>validateObservableProtocolPrefix([line],'p1'));
    assert.throws(()=>opponentPublicBoosts([line],'p1a: Caller'));
    const python=spawnSync(process.env.PYTHON || 'python3',['-c','import json,sys; from neural.public_boosts import public_boost_evidence; public_boost_evidence(json.load(sys.stdin))'],{
      input:JSON.stringify([line]),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')},
    });assert.notEqual(python.status,0);
  }
});
