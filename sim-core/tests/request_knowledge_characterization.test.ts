import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { buildLegalActionSet, normalizeRequest } from '../src/action_codec';

/**
 * Prompt 13 / S01a characterization (no production change). Every `CURRENT_BEHAVIOR_LOSSY` test passes by
 * asserting what the system does TODAY and is expected to flip when S01b lands a request-knowledge
 * representation. `CONTROL` tests pin behaviour that must stay identical.
 *
 * Evidence chain: test-owned pinned BattleStream harness (exact addressed `|request|` text, before any
 * normalization) -> real PipelineIntegrationSession restored from the harness snapshot (v1 and v2) ->
 * real normalizeRequest / observation / record bundle -> real Python publication.
 */
const repositoryRoot = path.resolve(__dirname, '../../..');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const witness = require(path.join(repositoryRoot, 'docs/planning/perspective-fidelity-prompt13-witness.cjs'));
const V1 = 'observable-battle-state/v1';
const V2 = 'observable-battle-state/v2';
type Json = any;
const captured: Promise<Record<string, Json>> = witness.captureAll();

const view = (c: Json, version = V2) => c.versions[version];
const raw = (c: Json, owner: string): Json => JSON.parse(c.raw[owner].json);
const requestOf = (c: Json, owner: string, version = V2): Json => view(c, version).observations[owner].request;
const OWNERS = ['p1', 'p2'] as const;
const MOVE_KEYS = ['slot', 'move', 'id', 'pp', 'maxpp', 'target', 'disabled', 'type', 'category', 'base_power', 'accuracy'];
const ACTIVE_KEYS = ['moves', 'can_terastallize', 'tera_type', 'trapped', 'can_switch'];
const mirrorOwner = (id: string, owner: string) => (id.endsWith('_mirror') ? (owner === 'p1' ? 'p2' : 'p1') : owner);
const subjectOwner = (id: string) => (id.endsWith('_mirror') ? 'p2' : 'p1');
const clone = (value: Json): Json => JSON.parse(JSON.stringify(value));
const keysDeep = (value: Json): string[] => (Array.isArray(value) ? value.flatMap(keysDeep)
  : value && typeof value === 'object' ? Object.entries(value).flatMap(([key, child]) => [key, ...keysDeep(child)]) : []);

function runPython(args: string[], input: string) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  assert.ok(!Object.keys(env).some((key) => ['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  return spawnSync(process.env.PYTHON || 'python3', args, {
    cwd: repositoryRoot, env: { ...env, PYTHONPATH: path.resolve(repositoryRoot, 'trainer/src') }, input, encoding: 'utf8', timeout: 60_000,
  });
}

// ---------------------------------------------------------------------------------------------- controls
test('CONTROL: exact addressed text from the independent harness equals the live request and its normalization equals the pipeline observation', async () => {
  const cases = await captured;
  assert.equal(Object.keys(cases).length, 20);
  for (const [id, c] of Object.entries(cases)) {
    assert.equal(c.harness_errors.length, id === 'trapped_after_rejection' ? 1 : 0, id);
    for (const version of [V1, V2]) {
      for (const owner of OWNERS) {
        const entry = view(c, version);
        const live = c.raw[owner] ? entry.live_raw_equals_harness[owner] : true;
        const expectedMismatch = (id === 'trapped_after_rejection' && owner === 'p1') // restored branch re-emits the pre-rejection request
          || (c.raw[owner] && JSON.parse(c.raw[owner].json).wait === true) // env.getRequest hides wait requests
          || id === 'terminal_requestless' || (id === 'revival_selection_and_waiting' && owner === 'p2');
        if (!expectedMismatch) assert.equal(live, true, `${id} ${owner} ${version}: live raw text != harness text`);
        const normalized = entry.direct_normalization[owner];
        const observed = entry.observations[owner].request;
        if (id === 'terminal_requestless') { assert.equal(observed, null); continue; }
        if (id === 'trapped_after_rejection' && owner === 'p1') continue; // asserted separately
        const { legal_actions_from_raw: _derived, ...withoutDerived } = normalized;
        assert.deepEqual(withoutDerived, observed, `${id} ${owner} ${version}: normalizing the independent raw must reproduce the observation request`);
      }
    }
  }
});

test('CONTROL: every addressed request text round-trips exactly through JSON parse/stringify and fits the contract raw bound', async () => {
  for (const [id, c] of Object.entries(await captured)) {
    for (const text of [...OWNERS.flatMap((o) => (c.raw[o] ? [c.raw[o].json] : [])), ...OWNERS.flatMap((o) => c.raw_history[o])]) {
      assert.equal(JSON.stringify(JSON.parse(text)), text, id);
      assert.ok([...text].length <= 65536, id);
    }
  }
});

test('CONTROL: v1 and v2 observations carry byte-identical request views for every case', async () => {
  for (const [id, c] of Object.entries(await captured)) {
    for (const owner of OWNERS) assert.deepEqual(requestOf(c, owner, V1), requestOf(c, owner, V2), `${id} ${owner}`);
  }
});

test('CONTROL: ordinary slots emit pp/maxpp/target/disabled and the observation preserves them (both owners)', async () => {
  const c = (await captured).ordinary_slots;
  for (const owner of OWNERS) {
    const rawMoves = raw(c, owner).active[0].moves;
    const observed = requestOf(c, owner).active.moves;
    assert.equal(observed.length, rawMoves.length);
    rawMoves.forEach((move: Json, index: number) => {
      assert.deepEqual(Object.keys(move), ['move', 'id', 'pp', 'maxpp', 'target', 'disabled']);
      for (const key of ['pp', 'maxpp', 'target', 'disabled']) assert.equal(observed[index][key], move[key]);
    });
  }
});

test('CONTROL: legal actions derive only from the current addressed request, and absent PP never creates a legal move', async () => {
  const cases = await captured;
  for (const [id, c] of Object.entries(cases)) {
    for (const version of [V1, V2]) for (const owner of OWNERS) {
      const observed = view(c, version).observations[owner].request;
      if (!observed || observed.wait) continue;
      // The restored rejection branch re-emits the pre-rejection request (history[0]); legality follows that live request.
      const source = id === 'trapped_after_rejection' && owner === 'p1' ? JSON.parse(c.raw_history.p1[0]) : raw(c, owner);
      assert.deepEqual(observed.legal_actions, buildLegalActionSet(source), `${id} ${owner}: legal set must be a pure function of the raw request`);
      if (source === raw(c, owner) || id !== 'trapped_after_rejection') assert.deepEqual(observed.legal_actions, view(c, version).direct_normalization[owner].legal_actions_from_raw);
    }
  }
  // Tamper A: dropping `pp` from an ordinary move removes its action rather than inferring legality.
  const ordinary = clone(raw((await captured).ordinary_slots, 'p1'));
  const before = buildLegalActionSet(ordinary).actions.filter((a) => a && a.kind === 'move').map((a) => a!.choice);
  delete ordinary.active[0].moves[1].pp;
  const after = buildLegalActionSet(ordinary).actions.filter((a) => a && a.kind === 'move').map((a) => a!.choice);
  assert.deepEqual(before, ['move 1', 'move 2', 'move 3', 'move 4']);
  assert.deepEqual(after, ['move 1', 'move 3', 'move 4']);
  // Tamper B: the maybe* flags never influence legality; only the request's moves/disabled/trapped do.
  const imprison = (await captured).maybe_disabled_imprison;
  const flagged = clone(raw(imprison, 'p1'));
  const unflagged = clone(flagged); delete unflagged.active[0].maybeDisabled;
  assert.deepEqual(buildLegalActionSet(flagged), buildLegalActionSet(unflagged));
  const shadow = (await captured).maybe_trapped_shadow_tag;
  const flaggedTrap = clone(raw(shadow, 'p1'));
  const unflaggedTrap = clone(flaggedTrap); delete unflaggedTrap.active[0].maybeTrapped;
  assert.deepEqual(buildLegalActionSet(flaggedTrap), buildLegalActionSet(unflaggedTrap));
});

// ------------------------------------------------------------------------- CURRENT_BEHAVIOR_LOSSY: K07
for (const id of ['two_turn_locked_move', 'two_turn_locked_move_mirror', 'recharge', 'recharge_mirror']) {
  test(`CURRENT_BEHAVIOR_LOSSY K07: ${id} omits pp/maxpp/target/disabled and the normalizer fabricates 0/0/normal/false`, async () => {
    const c = (await captured)[id];
    const owner = subjectOwner(id);
    const rawActive = raw(c, owner).active[0];
    const isRecharge = id.startsWith('recharge');
    assert.deepEqual(Object.keys(rawActive), ['moves', 'trapped']);
    assert.deepEqual(rawActive.moves, [isRecharge ? { move: 'Recharge', id: 'recharge' } : { move: 'Solar Beam', id: 'solarbeam' }]);
    for (const version of [V1, V2]) {
      const active = requestOf(c, owner, version).active;
      assert.deepEqual(Object.keys(active), ACTIVE_KEYS);
      assert.deepEqual(Object.keys(active.moves[0]), MOVE_KEYS);
      const { pp, maxpp, target, disabled } = active.moves[0];
      assert.deepEqual({ pp, maxpp, target, disabled }, { pp: 0, maxpp: 0, target: 'normal', disabled: false });
      // A source `trapped:true` that is really a lock side effect is the same field as a real trap.
      assert.equal(active.trapped, true);
      assert.equal(active.can_switch, false);
      assert.equal(active.can_terastallize, false);
      assert.equal(active.tera_type, null);
    }
    // Legal authority is the simulator `default`, not a PP>0 move: the pp=0 move row exists only as the sentinel.
    const legal = requestOf(c, owner).legal_actions;
    assert.deepEqual(legal.available_indices, [0]);
    assert.equal(legal.actions[0].choice, 'default');
    assert.equal(legal.actions[0].move, null);
    // The previously emitted PP of the move is gone from the locked-turn observation.
    const history = c.raw_history[owner].map((text: string) => JSON.parse(text));
    assert.equal(history.length, 2);
    const earlier = history[0].active[0].moves[0];
    assert.equal(earlier.pp, isRecharge ? 8 : 16);
    assert.equal(JSON.stringify(requestOf(c, owner).active.moves).includes(`"pp":${earlier.pp}`), false);
  });
}

test('CURRENT_BEHAVIOR_LOSSY K07: Struggle fallback omits pp/maxpp, keeps randomNormal, and is indistinguishable from pp=0 except through maxpp', async () => {
  for (const id of ['struggle_fallback', 'struggle_fallback_mirror']) {
    const c = (await captured)[id];
    const owner = subjectOwner(id);
    assert.deepEqual(raw(c, owner).active[0].moves, [{ move: 'Struggle', id: 'struggle', target: 'randomNormal', disabled: false }]);
    for (const version of [V1, V2]) {
      const m = requestOf(c, owner, version).active.moves[0];
      assert.deepEqual({ pp: m.pp, maxpp: m.maxpp, target: m.target, disabled: m.disabled }, { pp: 0, maxpp: 0, target: 'randomNormal', disabled: false });
    }
    const legal = requestOf(c, owner).legal_actions;
    assert.equal(legal.actions[0].choice, 'move 1'); // legal only through the request-supplied struggle exception
    assert.equal(legal.actions[0].move, 'Struggle');
  }
});

test('CURRENT_BEHAVIOR_LOSSY K07: real PP 0 and "PP absent" both become pp=0; only a maxpp==0 convention separates them; omitted target equals ordinary "normal"', async () => {
  const cases = await captured;
  const zero = cases.real_pp_zero;
  const rawZero = raw(zero, 'p1').active[0].moves[0];
  assert.deepEqual(rawZero, { move: 'Destiny Bond', id: 'destinybond', pp: 0, maxpp: 8, target: 'self', disabled: true });
  const observedZero = requestOf(zero, 'p1').active.moves[0];
  assert.equal(observedZero.pp, 0);
  const locked = requestOf(cases.two_turn_locked_move, 'p1').active.moves[0];
  assert.equal(locked.pp, observedZero.pp, 'real zero and absent PP are the same pp value');
  // The normalizer is non-injective: an explicit zero/normal/false row and a row with those keys omitted are identical.
  const omitted = { active: [{ moves: [{ move: 'Solar Beam', id: 'solarbeam' }], trapped: true }], side: raw(cases.two_turn_locked_move, 'p1').side };
  const explicit = clone(omitted);
  Object.assign(explicit.active[0].moves[0], { pp: 0, maxpp: 0, target: 'normal', disabled: false });
  const a = normalizeRequest('p1', omitted); const b = normalizeRequest('p1', explicit);
  assert.deepEqual({ ...a, raw: null }, { ...b, raw: null });
  // Non-finite / non-number PP is silently coerced the same way.
  const garbage = clone(omitted); Object.assign(garbage.active[0].moves[0], { pp: 'x', maxpp: null });
  assert.deepEqual(normalizeRequest('p1', garbage).active!.moves[0], a.active!.moves[0]);
  // Omitted target is the same value a real `normal`-target move (Tackle) carries.
  const tackle = requestOf(cases.ordinary_slots, 'p1').active.moves[0];
  assert.equal(raw(cases.ordinary_slots, 'p1').active[0].moves[0].target, 'normal');
  assert.equal(locked.target, tackle.target);
  assert.equal(locked.disabled, tackle.disabled);
});

test('CURRENT_BEHAVIOR_LOSSY K07: waiting, forced-switch, revival and terminal observations carry no active slots and the bench roster has no PP at all', async () => {
  const cases = await captured;
  const wf = cases.waiting_and_forced_switch;
  assert.deepEqual(Object.keys(raw(wf, 'p1')), ['wait', 'side']);
  assert.deepEqual(Object.keys(raw(wf, 'p2')), ['forceSwitch', 'side', 'noCancel']);
  for (const version of [V1, V2]) {
    const waiting = requestOf(wf, 'p1', version); const forced = requestOf(wf, 'p2', version);
    assert.equal(waiting.wait, true); assert.equal(waiting.active, null); assert.equal(waiting.legal_actions.available_indices.length, 0);
    assert.equal(forced.force_switch, true); assert.equal(forced.active, null); assert.deepEqual(forced.legal_actions.available_indices, [8]);
    assert.equal(view(wf, version).observations.p1.decision_availability.reason, 'waiting');
    for (const request of [waiting, forced]) for (const member of request.side) {
      assert.ok(member.moves.every((m: Json) => typeof m === 'string'), 'roster moves are names only');
      assert.equal(JSON.stringify(member).includes('"pp"'), false);
    }
  }
  const rv = cases.revival_selection_and_waiting;
  assert.equal(requestOf(rv, 'p1').side.some((p: Json) => p.reviving === true), true);
  assert.equal(requestOf(rv, 'p1').active, null);
  assert.equal(requestOf(rv, 'p2').wait, true);
  assert.equal(view(rv).boundary_kind, 'one_sided_revival');
  // Terminal: owners had real requests earlier (raw history), but the terminal observation retains none.
  const terminal = cases.terminal_requestless;
  for (const version of [V1, V2]) for (const owner of OWNERS) {
    assert.equal(view(terminal, version).observations[owner].request, null);
    assert.deepEqual(view(terminal, version).observations[owner].decision_availability, { available: false, reason: 'terminal', legal_action_indices: null });
  }
  assert.ok(terminal.raw_history.p1.length >= 3 && terminal.raw_history.p2.length >= 3);
  assert.equal(JSON.parse(terminal.raw_history.p1[2]).active[0].moves[0].pp, 1); // Revival Blessing PP emitted earlier, not retained
  const played = view(rv).after_revival;
  assert.equal(played.boundary_kind, 'terminal');
  for (const owner of OWNERS) assert.equal(played.observations[owner].request, null);
});

// ------------------------------------------------------------------------- CURRENT_BEHAVIOR_LOSSY: K08
for (const id of ['maybe_disabled_imprison', 'maybe_disabled_imprison_mirror']) {
  test(`CURRENT_BEHAVIOR_LOSSY K08: ${id} drops maybeDisabled and presents hidden-disabled moves as definitely enabled`, async () => {
    const c = (await captured)[id];
    const owner = subjectOwner(id);
    const rawRequest = raw(c, owner);
    assert.equal(rawRequest.active[0].maybeDisabled, true);
    assert.ok(rawRequest.active[0].moves.every((m: Json) => m.disabled === false));
    for (const version of [V1, V2]) {
      const request = requestOf(c, owner, version);
      assert.deepEqual(Object.keys(request.active), ACTIVE_KEYS);
      assert.equal(JSON.stringify(request).includes('maybe'), false);
      assert.ok(request.active.moves.every((m: Json) => m.disabled === false));
      assert.ok(request.legal_actions.actions.some((a: Json) => a && a.label === 'move:Tackle'));
    }
    // Identical observation with and without the source flag.
    const stripped = clone(rawRequest); delete stripped.active[0].maybeDisabled;
    assert.deepEqual({ ...normalizeRequest(owner as 'p1', rawRequest), raw: null }, { ...normalizeRequest(owner as 'p1', stripped), raw: null });
    // The engine rejects the shared move the request listed as legal and enabled.
    assert.equal(view(c).reject_probe.rejected, true);
    assert.equal(view(c).reject_probe.code, 'pipeline/v1/rejected-action');
  });
}

for (const id of ['maybe_trapped_shadow_tag', 'maybe_trapped_shadow_tag_mirror']) {
  test(`CURRENT_BEHAVIOR_LOSSY K08: ${id} drops maybeTrapped and reports not-trapped with switching available`, async () => {
    const c = (await captured)[id];
    const owner = subjectOwner(id);
    const rawRequest = raw(c, owner);
    assert.equal(rawRequest.active[0].maybeTrapped, true);
    assert.equal(Object.hasOwn(rawRequest.active[0], 'trapped'), false);
    for (const version of [V1, V2]) {
      const request = requestOf(c, owner, version);
      assert.equal(JSON.stringify(request).includes('maybe'), false);
      assert.equal(request.trapped, false);
      assert.equal(request.active.trapped, false);
      assert.equal(request.active.can_switch, true);
      assert.ok(request.legal_actions.actions.some((a: Json) => a && a.kind === 'switch'));
    }
    const stripped = clone(rawRequest); delete stripped.active[0].maybeTrapped;
    assert.deepEqual({ ...normalizeRequest(owner as 'p1', rawRequest), raw: null }, { ...normalizeRequest(owner as 'p1', stripped), raw: null });
  });
}

test('CURRENT_BEHAVIOR_LOSSY K08: a rejected switch re-emits the request with trapped:true and no maybeTrapped; the pre-rejection maybe is unrecorded and the restored branch re-emits the stale request', async () => {
  const c = (await captured).trapped_after_rejection;
  assert.equal(c.harness_errors.length, 1);
  assert.match(c.harness_errors[0].line, /^\|error\|\[Unavailable choice\] Can't switch: The active Pok/);
  const [first, second] = c.raw_history.p1.map((text: string) => JSON.parse(text));
  assert.equal(first.active[0].maybeTrapped, true); assert.equal(Object.hasOwn(first.active[0], 'trapped'), false);
  assert.equal(second.active[0].trapped, true); assert.equal(Object.hasOwn(second.active[0], 'maybeTrapped'), false);
  const before = normalizeRequest('p1', first); const after = normalizeRequest('p1', second);
  assert.equal(before.active!.trapped, false); assert.equal(after.active!.trapped, true);
  assert.equal(after.active!.can_switch, false);
  assert.equal(after.legal_actions.actions.some((a) => a && a.kind === 'switch'), false);
  // Restoration finding: the snapshot-restored branch re-emits the pre-rejection request (maybeTrapped, not trapped).
  for (const version of [V1, V2]) {
    assert.equal(view(c, version).live_raw_equals_harness.p1, false);
    assert.equal(requestOf(c, 'p1', version).active.trapped, false);
    assert.ok(requestOf(c, 'p1', version).legal_actions.actions.some((a: Json) => a && a.kind === 'switch'));
  }
});

test('CURRENT_BEHAVIOR_LOSSY K08: known trap, lock-induced trap and soft locks collapse into undifferentiated booleans (no reason, no lock identity)', async () => {
  const cases = await captured;
  const mean = requestOf(cases.known_trapped_mean_look, 'p1').active;
  const lock = requestOf(cases.two_turn_locked_move, 'p1').active;
  assert.equal(mean.trapped, true); assert.equal(lock.trapped, true); // real trap vs engine lock side effect
  for (const id of ['choice_lock_soft', 'encore_soft', 'real_pp_zero']) {
    const moves = requestOf(cases[id], 'p1').active.moves;
    const disabled = moves.filter((m: Json) => m.disabled === true);
    assert.ok(disabled.length >= 1, id);
    for (const move of moves) assert.deepEqual(Object.keys(move), MOVE_KEYS); // no reason / source / lock-target field exists
  }
  // Choice lock, Encore and a PP-0 move all surface as the same `disabled:true` on a pp>0 or pp=0 row, with no lock identity.
  const choice = requestOf(cases.choice_lock_soft, 'p1').active.moves;
  assert.deepEqual(choice.map((m: Json) => m.disabled), [false, true, true, true]);
  assert.deepEqual(requestOf(cases.encore_soft, 'p1').active.moves.map((m: Json) => m.disabled), [false, true, true, true]);
  assert.equal(JSON.stringify(requestOf(cases.choice_lock_soft, 'p1')).includes('lock'), false);
});

// ------------------------------------------------------------------------- real Python path
test('CURRENT_BEHAVIOR_LOSSY: actual Python publication accepts every actionable bundle (v1 and v2, both owners) with no request-knowledge in the published record', async () => {
  const cases = await captured;
  let published = 0;
  for (const [id, c] of Object.entries(cases)) {
    for (const version of [V1, V2]) {
      const bundles = view(c, version).bundles;
      if (!bundles) continue;
      for (const owner of OWNERS) {
        const wire = JSON.stringify(bundles[owner]);
        assert.equal(keysDeep(bundles[owner]).some((key) => /maybe/i.test(key)), false, `${id} ${owner}`);
        const result = runPython(['-m', 'neural.pipeline_record'], wire);
        assert.equal(result.status, 0, `${id} ${owner} ${version}: ${result.stderr}`);
        const row = JSON.parse(result.stdout);
        assert.equal(row.observation_id, bundles[owner].input_observation.observation_id);
        published += 1;
      }
    }
  }
  assert.equal(published, 2 * 2 * 17);
});
