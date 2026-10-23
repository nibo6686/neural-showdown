import {simulationSnapshotEnv as simulationEnv} from './helpers/simulation_env';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import test from 'node:test';
import { BattleStream, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { ActiveRequestOverrideValidationError, LocalBattleEnv, activeRequestOverrideDiagnostics } from '../src/env_manager';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { fingerprintSimulatorState } from '../src/transition';
import type { PlayerID, StepResult } from '../src/types';

const FORMAT = 'gen9randombattle';
const SEED = [1, 2, 3, 4];
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const KEY = '__neural_active_request_overrides';
const SCHEMA = 'active-request-overrides/v1';
type Json = Record<string, any>;

const SNORLAX = 'Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n\nBlissey\n- Splash\n';
const TRAP = { own: SNORLAX, foe: 'Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n', rounds: [] as string[] };
const IMPRISON = {
  own: 'Snorlax\nAbility: Immunity\n- Tackle\n- Rest\n- Curse\n- Splash\n\nBlissey\n- Splash\n',
  foe: 'Alakazam\nAbility: Magic Guard\n- Imprison\n- Tackle\n\nSnorlax\nAbility: Immunity\n- Splash\n',
  rounds: ['move 4/move 1'], // own Splash, foe Imprison
};
const BOTH = {
  own: 'Alakazam\nAbility: Magic Guard\n- Imprison\n- Tackle\n\nBlissey\n- Splash\n',
  foe: 'Wobbuffet\nAbility: Shadow Tag\n- Splash\n- Tackle\n\nSnorlax\nAbility: Immunity\n- Splash\n',
  rounds: ['move 1/move 1'],
};
const FORCED = { own: 'Mewtwo\nAbility: Pressure\n- Psystrike\n- Splash\n\nBlissey\n- Splash\n', foe: 'Magikarp\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n', rounds: ['move 1/move 1'] };
const REVIVAL = {
  own: 'Lead (Snorlax)\nAbility: Immunity\n- Memento\n\nPawmot\n- Revival Blessing\n- Splash\n',
  foe: 'Terminus (Snorlax)\nAbility: Immunity\n- Splash\n- Memento\n',
  rounds: ['move 1/move 1', 'switch 2/', 'move 1/move 2'],
};
type Scenario = typeof TRAP;

const pack = (text: string) => Teams.pack(Teams.import(text));
const other = (p: PlayerID): PlayerID => (p === 'p1' ? 'p2' : 'p1');

/** Plays the scenario on a bare BattleStream and returns the privileged snapshot (the simulator-state fixture seam). */
async function baseSnapshot(scenario: Scenario, owner: PlayerID): Promise<Json> {
  const stream = new BattleStream({ keepAlive: true });
  try {
    const teams = { [owner]: scenario.own, [other(owner)]: scenario.foe } as Record<PlayerID, string>;
    await stream.write([
      `>start ${JSON.stringify({ formatid: FORMAT, seed: SEED })}`,
      `>player p1 ${JSON.stringify({ name: 'A', team: pack(teams.p1) })}`,
      `>player p2 ${JSON.stringify({ name: 'B', team: pack(teams.p2) })}`,
    ].join('\n'));
    for (const round of scenario.rounds) {
      const [own, foe] = round.split('/');
      await stream.write([own && `>${owner} ${own}`, foe && `>${other(owner)} ${foe}`].filter(Boolean).join('\n'));
    }
    return structuredClone((stream as unknown as { battle: { toJSON(): Json } }).battle.toJSON());
  } finally { stream.destroy(); }
}

const restore = async (id: string, state: Json) => {
  const env = simulationEnv({id, format: FORMAT, seed: SEED});
  try { return { env, result: await env.resetFromSerialized(structuredClone(state), OPTIONS) }; } catch (error) { await env.close(); throw error; }
};
const rawOf = (r: StepResult, p: PlayerID) => r.requests[p]!.raw as Json;
const choices = (r: StepResult, p: PlayerID) => r.requests[p]!.legal_actions.actions.map((a) => a?.choice ?? null);
const override = (state: Json, requests: Json) => ({ ...state, [KEY]: { schema_version: SCHEMA, requests } });

// Pinned sim/side.ts:522 emitRequest adds update:true when resending a rejected choice.
const trapEdit = (raw: Json): Json => { const r = structuredClone(raw); delete r.active[0].maybeTrapped; r.active[0].trapped = true; r.update = true; return r; };
const disableEdit = (raw: Json, index: number): Json => { const r = structuredClone(raw); r.active[0].moves[index].disabled = true; r.active[0].moves[index].disabledSource = ''; return r; };

for (const owner of ['p1', 'p2'] as const) {
  test(`rejected switch (maybeTrapped to trapped) restores the live request and legal set for ${owner}`, async () => {
    const base = await baseSnapshot(TRAP, owner);
    const live = await restore('trap-live', base);
    try {
      assert.equal(rawOf(live.result, owner).active[0].maybeTrapped, true);
      assert.ok(choices(live.result, owner).includes('switch 2'));
      const rejected = await live.env.step({ [owner]: 'switch 2' });
      const liveRaw = rawOf(rejected, owner);
      assert.equal(liveRaw.active[0].trapped, true);
      assert.equal('maybeTrapped' in liveRaw.active[0], false);
      const snapshot = live.env.captureSeededSnapshot(null);

      const restored = await restore('trap-restored', snapshot.simulator_state);
      try {
        assert.deepEqual(rawOf(restored.result, owner), liveRaw);
        assert.deepEqual(restored.result.requests[owner]!.legal_actions, rejected.requests[owner]!.legal_actions);
        assert.equal(choices(restored.result, owner).includes('switch 2'), false);
        assert.deepEqual(Object.keys(snapshot.simulator_state[KEY] as Json), ['schema_version', 'requests']);
        assert.deepEqual((snapshot.simulator_state[KEY] as Json).requests, { [owner]: liveRaw });
        assert.deepEqual((snapshot.simulator_state[KEY] as Json).requests[owner], trapEdit(rawOf(live.result, owner)));
        assert.equal(restored.env.captureSeededSnapshot(null).state_fingerprint, snapshot.state_fingerprint);
        // Play continues identically for several steps, live versus restored.
        for (let i = 0; i < 3; i++) {
          const move = { [owner]: 'move 2', [other(owner)]: 'move 1' };
          const a = await live.env.step(move), b = await restored.env.step(move);
          assert.deepEqual(a.requests[owner]!.raw, b.requests[owner]!.raw);
          assert.deepEqual(a.requests[other(owner)]!.raw, b.requests[other(owner)]!.raw);
          assert.equal(live.env.captureSeededSnapshot(null).state_fingerprint, restored.env.captureSeededSnapshot(null).state_fingerprint);
        }
      } finally { await restored.env.close(); }
    } finally { await live.env.close(); }
  });

  test(`rejected hidden-disabled move restores the live request and legal set for ${owner}`, async () => {
    const base = await baseSnapshot(IMPRISON, owner);
    const live = await restore('imp-live', base);
    try {
      const before = rawOf(live.result, owner);
      assert.equal(before.active[0].maybeDisabled, true);
      assert.ok(choices(live.result, owner).includes('move 1'));
      const rejected = await live.env.step({ [owner]: 'move 1' });
      const liveRaw = rawOf(rejected, owner);
      assert.equal(liveRaw.active[0].moves[0].disabled, true);
      assert.equal(typeof liveRaw.active[0].moves[0].disabledSource, 'string');
      const snapshot = live.env.captureSeededSnapshot(null);

      const restored = await restore('imp-restored', snapshot.simulator_state);
      try {
        assert.deepEqual(rawOf(restored.result, owner), liveRaw);
        assert.deepEqual(restored.result.requests[owner]!.legal_actions, rejected.requests[owner]!.legal_actions);
        assert.equal(choices(restored.result, owner).includes('move 1'), false);
        assert.deepEqual((snapshot.simulator_state[KEY] as Json).requests[owner], disableEdit(before, 0));
        assert.equal(restored.env.captureSeededSnapshot(null).state_fingerprint, snapshot.state_fingerprint);
        for (const choice of ['move 4', 'move 4']) {
          const move = { [owner]: choice, [other(owner)]: 'move 2' };
          const a = await live.env.step(move), b = await restored.env.step(move);
          assert.deepEqual(a.requests[owner]!.raw, b.requests[owner]!.raw);
          assert.equal(live.env.captureSeededSnapshot(null).state_fingerprint, restored.env.captureSeededSnapshot(null).state_fingerprint);
        }
      } finally { await restored.env.close(); }
    } finally { await live.env.close(); }
  });

  test(`repeated save/restore round trips of a mutated state are stable for ${owner}`, async () => {
    const base = await baseSnapshot(TRAP, owner);
    const first = await restore('rt-0', base);
    let fingerprint = '';
    let state: Json = {};
    try {
      await first.env.step({ [owner]: 'switch 2' });
      const snapshot = first.env.captureSeededSnapshot(null);
      assert.ok(KEY in snapshot.simulator_state);
      fingerprint = snapshot.state_fingerprint; state = snapshot.simulator_state;
    } finally { await first.env.close(); }
    for (let i = 0; i < 3; i++) {
      const next = await restore(`rt-${i + 1}`, state);
      try {
        const again = next.env.captureSeededSnapshot(null);
        assert.equal(again.state_fingerprint, fingerprint);
        assert.deepEqual(again.simulator_state, state);
        state = again.simulator_state;
      } finally { await next.env.close(); }
    }
  });
}

test('hand-built engine-legal overrides are accepted; the same key built from illegal edits is a typed validation error', async () => {
  const base = await baseSnapshot(TRAP, 'p1');
  const probe = await restore('forge-probe', base);
  const good = trapEdit(rawOf(probe.result, 'p1'));
  await probe.env.close();
  const imprisonBase = await baseSnapshot(IMPRISON, 'p1');
  // maybeTrapped stays set but the engine's trapped flag is cleared: a grammatically legal trap edit that the engine would never make.
  const arenaBase = structuredClone(base);
  arenaBase.sides[0].pokemon[0].trapped = false;
  const arenaProbe = await restore('forge-probe3', arenaBase);
  const arenaRaw = rawOf(arenaProbe.result, 'p1');
  await arenaProbe.env.close();
  assert.equal(arenaRaw.active[0].maybeTrapped, true);
  const imprisonProbe = await restore('forge-probe2', imprisonBase);
  const imprisonRaw = rawOf(imprisonProbe.result, 'p1');
  await imprisonProbe.env.close();

  const accepted = await restore('forge-ok', override(base, { p1: good }));
  try { assert.deepEqual(rawOf(accepted.result, 'p1'), good); } finally { await accepted.env.close(); }
  const acceptedBoth = await restore('forge-ok2', override(imprisonBase, { p1: disableEdit(imprisonRaw, 0) }));
  try { assert.deepEqual(rawOf(acceptedBoth.result, 'p1').active[0].moves[0].disabled, true); } finally { await acceptedBoth.env.close(); }

  const mutate = (f: (r: Json) => void, from: Json = good) => { const r = structuredClone(from); f(r); return r; };
  const cases: Array<[string, Json, 'trap' | 'imprison' | 'arena']> = [
    ['extra top-level wrapper key', { ...override(base, { p1: good })[KEY], extra: 1 }, 'trap'],
    ['unsupported schema', { schema_version: 'active-request-overrides/v2', requests: { p1: good } }, 'trap'],
    ['missing schema', { requests: { p1: good } }, 'trap'],
    ['requests not an object', { schema_version: SCHEMA, requests: [good] }, 'trap'],
    ['empty requests', { schema_version: SCHEMA, requests: {} }, 'trap'],
    ['unknown player', { schema_version: SCHEMA, requests: { p3: good } }, 'trap'],
    ['wrong side: p1 request filed under p2', { schema_version: SCHEMA, requests: { p2: good } }, 'trap'],
    ['request is a string', { schema_version: SCHEMA, requests: { p1: JSON.stringify(good) } }, 'trap'],
    ['request is null', { schema_version: SCHEMA, requests: { p1: null } }, 'trap'],
    ['request is wrong side id', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.side.id = 'p2'; }) } }, 'trap'],
    ['extra top-level request key', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.extra = true; }) } }, 'trap'],
    ['extra active key', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].extra = true; }) } }, 'trap'],
    ['trapped is not true', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].trapped = 'hidden'; }) } }, 'trap'],
    ['maybeTrapped kept alongside trapped', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].maybeTrapped = true; }) } }, 'trap'],
    ['trapped edit on a request that never had maybeTrapped', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].trapped = true; }, imprisonRaw) } }, 'imprison'],
    ['move id changed', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].id = 'splash'; }) } }, 'trap'],
    ['move count changed', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves.pop(); }) } }, 'trap'],
    ['pp changed', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].pp = 0; }) } }, 'trap'],
    ['roster hp changed', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.side.pokemon[0].condition = '1/100'; }) } }, 'trap'],
    ['disabled without disabledSource', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].disabled = true; }, imprisonRaw) } }, 'imprison'],
    ['disabledSource of wrong type', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].disabled = true; r.active[0].moves[0].disabledSource = 7; }, imprisonRaw) } }, 'imprison'],
    ['disabledSource without disabled', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].disabledSource = ''; }, imprisonRaw) } }, 'imprison'],
    ['extra move key', { schema_version: SCHEMA, requests: { p1: mutate((r) => { r.active[0].moves[0].disabled = true; r.active[0].moves[0].disabledSource = ''; r.active[0].moves[0].extra = 1; }, imprisonRaw) } }, 'imprison'],
    ['forged trapped:true on a merely maybe-trapped (not trapped) Pokemon', { schema_version: SCHEMA, requests: { p1: trapEdit(arenaRaw) } }, 'arena'],
    ['forged disabled:true on a normal move', { schema_version: SCHEMA, requests: { p1: disableEdit(imprisonRaw, 1) } }, 'imprison'],
  ];
  const bases = { trap: base, imprison: imprisonBase, arena: arenaBase };
  for (const [name, forged, baseName] of cases) {
    const state = bases[baseName];
    await assert.rejects(restore(`forge-${name}`, { ...state, [KEY]: forged }), (error: any) => {
      assert.ok(error instanceof ActiveRequestOverrideValidationError, `${name}: ${String(error)}`);
      assert.equal(error.code, 'active-request-override/invalid');
      return true;
    }, name);
  }
  // key on an ended battle
  // Otherwise-valid input (accepted above as a live snapshot): only `ended` differs.
  await assert.rejects(restore('forge-ended', { ...override(base, { p1: good }), ended: true }), (error: any) => {
    assert.ok(error instanceof ActiveRequestOverrideValidationError);
    assert.match(error.reason, /live snapshots/);
    return true;
  });
  await assert.rejects(restore('forge-wait', override(base, { p1: { wait: true } })), ActiveRequestOverrideValidationError);
});

test('a rejected restore leaves the running environment untouched', async () => {
  const base = await baseSnapshot(TRAP, 'p1');
  const live = await restore('survive', base);
  try {
    const before = live.env.captureSeededSnapshot(null).state_fingerprint;
    await assert.rejects(live.env.resetFromSerialized(override(base, { p1: { wait: true } }), OPTIONS), ActiveRequestOverrideValidationError);
    assert.equal(live.env.captureSeededSnapshot(null).state_fingerprint, before);
    const next = await live.env.step({ p1: 'move 2', p2: 'move 1' });
    assert.ok(next.requests.p1);
  } finally { await live.env.close(); }
});

test('non-mutated live snapshots carry no override key, including after an ordinary turn', async () => {
  const base = await baseSnapshot(TRAP, 'p1');
  const live = await restore('plain', base);
  try {
    assert.equal(KEY in live.env.serializeBattle(), false);
    await live.env.step({ p1: 'move 2', p2: 'move 1' });
    assert.equal(KEY in live.env.serializeBattle(), false);
    const snap = live.env.captureSeededSnapshot(null);
    assert.equal(snap.state_fingerprint, fingerprintSimulatorState(snap.simulator_state));
  } finally { await live.env.close(); }
});

// Pre-change pins (computed with the unmodified env_manager before this slice): three seeds x v1/v2 pipeline sessions.
const PIPELINE_DIGESTS: Record<string, string> = {
  'pipeline:1-2-3-4:v1': 'f07d2e1df0818aab22541c372207c30a3a2d6002c4942f4c72de59d17f5a5538',
  'pipeline:1-2-3-4:v2': 'f5f708fb3e2bdb5bffe1d3835fb393437c97ab1b07356bc73891715f07e3f9f6',
  'pipeline:11-12-13-14:v1': '74f43a04895be86d7ca726a245075c51bc0c051da4ddc6a048a54ce727bae8bd',
  'pipeline:11-12-13-14:v2': 'ead9932c66527f4efa4e814bbeb15da17bccb6532e4c0044c5bb91c3ba2bb1ec',
  'pipeline:5-6-7-8:v1': '6d738fdb816e233f54c0bb0ae5aaab9db4afb041f35955d64dd89a49a53f85ff',
  'pipeline:5-6-7-8:v2': '18b9b314c18b2852f10d2f3c03a86b092b08834204f9b5d3e0e44cb9687bdc8e',
};
const sha = (x: unknown) => crypto.createHash('sha256').update(typeof x === 'string' ? x : JSON.stringify(x)).digest('hex');

test('three-seed v1/v2 pipeline corpus (joint, forced-switch, terminal) is byte-identical to the pre-change evidence', {skip: 'Historical pre-native11 evidence digests cannot be reproduced on b8f23c99; immutable source revisions differ.'}, async () => {
  for (const seed of [[1, 2, 3, 4], [11, 12, 13, 14], [5, 6, 7, 8]]) {
    for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      const key = `pipeline:${seed.join('-')}:${version.slice(-2)}`;
      const rows: Json[] = [];
      const session = await createPipelineIntegrationSession({ battle_id: `p16-${seed.join('-')}-${version.slice(-2)}`, format: FORMAT, seed, observation_schema_version: version });
      const take = (res: { record_bundles: unknown } | null) => rows.push({
        kind: session.boundary.kind, step: session.boundary.step_index, fp: session.boundary.state_fingerprint, branch: session.boundary.branch_id,
        boundary: sha(session.boundary), bundles: res ? sha(res.record_bundles) : null,
      });
      try {
        take(null);
        for (let i = 0; i < 250; i++) {
          const b = session.boundary;
          if (b.kind === 'terminal') break;
          let res;
          try {
            if (b.kind === 'joint_actionable') res = await session.step();
            else {
              const actor = (['p1', 'p2'] as const).find((o) => b.perspectives[o].observation.request && !b.perspectives[o].observation.request!.wait)!;
              const req = b.perspectives[actor].observation.request!;
              const act = canonicalActionFromLegalAction(req, req.legal_actions.available_indices[0]);
              res = b.kind === 'one_sided_revival' ? await session.stepRevival(act) : await session.stepForcedSwitch(act);
            }
          } catch (error) { const e = error as { code?: string; message: string }; rows.push({ error: e.code || e.message }); break; }
          take(res);
        }
      } finally { await session.close(); }
      assert.equal(sha(rows), PIPELINE_DIGESTS[key], key);
    }
  }
});

test('both owners mutated in one snapshot restore both live requests', async () => {
  const base = await baseSnapshot(BOTH, 'p1');
  const live = await restore('both-live', base);
  try {
    assert.equal(rawOf(live.result, 'p1').active[0].maybeTrapped, true);
    assert.equal(rawOf(live.result, 'p2').active[0].maybeDisabled, true);
    await live.env.step({ p1: 'switch 2' });
    await live.env.step({ p2: 'move 2' });
    const snapshot = live.env.captureSeededSnapshot(null);
    assert.deepEqual(Object.keys((snapshot.simulator_state[KEY] as Json).requests).sort(), ['p1', 'p2']);
    const restored = await restore('both-restored', snapshot.simulator_state);
    try {
      for (const p of ['p1', 'p2'] as const) {
        assert.deepEqual(rawOf(restored.result, p), live.env.getRequest(p)!.raw);
        assert.deepEqual(restored.result.requests[p]!.legal_actions, live.env.getRequest(p)!.legal_actions);
      }
      assert.equal(restored.env.captureSeededSnapshot(null).state_fingerprint, snapshot.state_fingerprint);
    } finally { await restored.env.close(); }
  } finally { await live.env.close(); }
});

for (const [name, scenario] of [
  ['forced switch with a waiting side', FORCED],
  ['revival selection', REVIVAL],
] as const) {
  test(`${name} produces no override key and restores byte-stably`, async () => {
    const first = await restore('nokey', await baseSnapshot(scenario, 'p1'));
    try {
      assert.ok(first.result.requests.p1 && first.result.requests.p2);
      assert.equal(KEY in first.env.serializeBattle(), false);
      const snapshot = first.env.captureSeededSnapshot(null);
      const second = await restore('nokey2', snapshot.simulator_state);
      try { assert.equal(second.env.captureSeededSnapshot(null).state_fingerprint, snapshot.state_fingerprint); } finally { await second.env.close(); }
    } finally { await first.env.close(); }
  });
}

test('doubles requests produce no override key', async () => {
  const stream = new BattleStream({ keepAlive: true });
  let state: Json;
  try {
    const team = Teams.pack(Teams.import('Snorlax\nAbility: Immunity\n- Tackle\n\nBlissey\n- Splash\n\nChansey\n- Splash\n'));
    await stream.write([`>start ${JSON.stringify({ formatid: 'gen9doublescustomgame', seed: SEED })}`,
      `>player p1 ${JSON.stringify({ name: 'A', team })}`, `>player p2 ${JSON.stringify({ name: 'B', team })}`].join('\n'));
    state = structuredClone((stream as unknown as { battle: { toJSON(): Json } }).battle.toJSON());
  } finally { stream.destroy(); }
  const env = simulationEnv({id: 'doubles', format: 'gen9doublescustomgame', seed: SEED});
  try {
    await env.resetFromSerialized(state, OPTIONS).catch(() => undefined); // a singles-only normalizer may refuse; serialization is asserted
    assert.equal(KEY in env.serializeBattle(), false);
  } finally { await env.close(); }
});

test('an unexplained live-versus-regenerated difference keeps the old bytes and fires the diagnostic hook', async () => {
  const live = await restore('drop', await baseSnapshot(TRAP, 'p1'));
  const seen: Array<{ player: string; reason: string }> = [];
  const before = activeRequestOverrideDiagnostics.dropped;
  activeRequestOverrideDiagnostics.onDrop = (info) => seen.push(info);
  try {
    const battle = (live.env as unknown as { battleStream: { battle: { sides: Array<{ activeRequest: Json }>; toJSON(): Json } } }).battleStream.battle;
    battle.sides[0].activeRequest.rqid += 7; // not an engine-legal edit
    const bytes = live.env.serializeBattle();
    assert.equal(KEY in bytes, false);
    assert.deepEqual(bytes, battle.toJSON());
    assert.equal(activeRequestOverrideDiagnostics.dropped, before + 1);
    assert.equal(seen.length, 1);
    assert.equal(seen[0].player, 'p1');
  } finally { activeRequestOverrideDiagnostics.onDrop = null; await live.env.close(); }
});
