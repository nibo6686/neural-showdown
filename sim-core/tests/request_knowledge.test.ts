import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { buildLegalActionSet, normalizeRequest } from '../src/action_codec';
import { buildRequestKnowledge, canonicalRequestKnowledgeJson, requestKnowledgeId, RequestKnowledgeError } from '../src/request_knowledge';

/**
 * Prompt 14 / S01b. Expected values come from the exact addressed raw text (an independent `?? null` reader in
 * this file) and from the hand-audited literal tables below, never from the builder under test. Cases and
 * observations come from the test-owned Prompt 13/14 witness (pinned BattleStream harness text + real legacy sessions).
 */
const repositoryRoot = path.resolve(__dirname, '../../..');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const witness = require(path.join(repositoryRoot, 'docs/planning/perspective-fidelity-prompt14-witness.cjs'));
const RETIRED = 'Retired Prompt14 raw-restore sidecar witness: native11 rejects imported authority; replay-born K coverage is in replay_session.test.ts; native moves/flags are W1.2/W1.3.';
const retiredTest = (name: string, fn: () => void | Promise<void>) => test(name, {skip: RETIRED}, fn);
const FRESH = 'fresh_delivery';
const V1 = 'observable-battle-state/v1';
const V2 = 'observable-battle-state/v2';
type Json = any;
const OWNERS = ['p1', 'p2'] as const;
const captured: Promise<Record<string, Json>> = Promise.resolve({} as Record<string, Json>);

const clone = (value: Json): Json => JSON.parse(JSON.stringify(value));
const canon = (value: Json): string => (Array.isArray(value) ? '[' + value.map(canon).join(',') + ']'
  : value && typeof value === 'object' ? '{' + Object.keys(value).sort().map((k) => JSON.stringify(k) + ':' + canon(value[k])).join(',') + '}' : JSON.stringify(value));
const sha = (text: string) => createHash('sha256').update(text, 'utf8').digest('hex');
const reseal = (observation: Json): Json => {
  const { observation_id: _id, protocol_prefix: _prefix, ...identity } = observation;
  return { ...observation, observation_id: 'obs-' + sha(canon(identity)) };
};
const deepFreeze = (value: Json): Json => { if (value && typeof value === 'object') { Object.values(value).forEach(deepFreeze); Object.freeze(value); } return value; };
const observationOf = (c: Json, owner: string, version = V2): Json => c.versions[version].observations[owner];
const rawTextOf = (c: Json, owner: string, version = V2): string | null => {
  const observation = observationOf(c, owner, version);
  return observation.view.terminated || observation.request === null ? null : c.raw[owner].json;
};
const build = (c: Json, owner: string, version = V2): Json => buildRequestKnowledge(owner, rawTextOf(c, owner, version), observationOf(c, owner, version), FRESH);
const codeOf = (fn: () => unknown): string => { try { fn(); } catch (error) { assert.ok(error instanceof RequestKnowledgeError, String(error)); return error.code; } return 'NO_ERROR'; };

/** Independent reader: what the raw row text alone entitles a record to say (absent key -> null). */
function independentMoves(text: string): Json[] {
  return JSON.parse(text).active[0].moves.map((row: Json, index: number) => ({
    slot: index + 1, id: row.id, name: row.move, pp: row.pp ?? null, max_pp: row.maxpp ?? null, target: row.target ?? null, disabled: row.disabled ?? null,
  }));
}

// ---------------------------------------------------------------- hand-audited literal tables (audited against the raw texts)
const D = (t: string, m: string, d: string, l = 'pp_bearing_rows') => ({ lock: l, trapped: t, maybe_trapped: m, maybe_disabled: d });
const BARE = 'bare_single_row';
const WITH = 'omitted_with_switch_in', WITHOUT = 'omitted_without_switch_in', SIM = 'omitted_singles_rule';
const PLAIN = { lock: 'no_hard_lock', trapped: false, maybe_trapped: false, maybe_disabled: false, switch_in_available: true, derivation: D(WITH, WITH, SIM) };
const LOCKED = (lock: string) => ({ ...PLAIN, lock, trapped: true, derivation: D('raw_true', 'superseded_by_trapped', SIM, BARE) });
const STRUGGLE = { ...PLAIN, lock: 'struggle', derivation: D(WITH, WITH, SIM, BARE) };
const FLAGS: Record<string, [string, Json]> = {
  two_turn_locked_move: ['p1', LOCKED('locked_move')], two_turn_locked_move_mirror: ['p2', LOCKED('locked_move')],
  recharge: ['p1', LOCKED('recharge')], recharge_mirror: ['p2', LOCKED('recharge')],
  struggle_fallback: ['p1', STRUGGLE], struggle_fallback_mirror: ['p2', STRUGGLE],
  maybe_disabled_imprison: ['p1', { ...PLAIN, maybe_disabled: true, derivation: D(WITH, WITH, 'raw_true') }],
  maybe_disabled_imprison_mirror: ['p2', { ...PLAIN, maybe_disabled: true, derivation: D(WITH, WITH, 'raw_true') }],
  maybe_trapped_shadow_tag: ['p1', { ...PLAIN, maybe_trapped: true, derivation: D(WITH, 'raw_true', SIM) }],
  maybe_trapped_shadow_tag_mirror: ['p2', { ...PLAIN, maybe_trapped: true, derivation: D(WITH, 'raw_true', SIM) }],
  known_trapped_mean_look: ['p1', { ...PLAIN, trapped: true, derivation: D('raw_true', 'superseded_by_trapped', SIM) }],
  known_trapped_mean_look_mirror: ['p2', { ...PLAIN, trapped: true, derivation: D('raw_true', 'superseded_by_trapped', SIM) }],
  struggle_maybe_disabled: ['p1', { ...STRUGGLE, maybe_disabled: true, derivation: D(WITH, WITH, 'raw_true', BARE) }],
  struggle_all_pp_zero: ['p1', STRUGGLE],
  outrage_lock: ['p1', LOCKED('locked_move')], rollout_lock: ['p1', LOCKED('locked_move')], uproar_lock: ['p1', LOCKED('locked_move')],
  maybe_trapped_empty_bench: ['p1', { ...PLAIN, trapped: null, maybe_trapped: null, switch_in_available: false, derivation: D(WITHOUT, WITHOUT, SIM) }],
  locked_empty_bench: ['p1', { ...LOCKED('locked_move'), trapped: null, maybe_trapped: null, switch_in_available: false, derivation: D(WITHOUT, WITHOUT, SIM, BARE) }],
  trapped_after_rejection: ['p1', { ...PLAIN, trapped: true, derivation: D('raw_true', 'superseded_by_trapped', SIM) }],
};
const R = (id: string, pp: number | null, max: number | null, target: string | null, disabled: boolean | null) => [id, pp, max, target, disabled];
const LOCKROW = (id: string) => [R(id, null, null, null, null)];
/** Subject-owner move rows, (id, pp, maxpp, target, disabled), from the raw texts. */
const MOVES: Record<string, Json[]> = {
  ordinary_slots: [R('tackle', 56, 56, 'normal', false), R('rest', 8, 8, 'self', false), R('curse', 16, 16, 'self', false), R('bodyslam', 24, 24, 'normal', false)],
  choice_lock_soft: [R('tackle', 55, 56, 'normal', false), R('rest', 8, 8, 'self', true), R('curse', 16, 16, 'self', true), R('bodyslam', 24, 24, 'normal', true)],
  encore_soft: [R('tackle', 55, 56, 'normal', false), R('growl', 64, 64, 'allAdjacentFoes', true), R('thunderwave', 32, 32, 'normal', true), R('splash', 64, 64, 'self', true)],
  two_turn_locked_move: LOCKROW('solarbeam'), two_turn_locked_move_mirror: LOCKROW('solarbeam'), recharge: LOCKROW('recharge'), recharge_mirror: LOCKROW('recharge'),
  struggle_fallback: [R('struggle', null, null, 'randomNormal', false)], struggle_fallback_mirror: [R('struggle', null, null, 'randomNormal', false)],
  real_pp_zero: [R('destinybond', 0, 8, 'self', true), R('splash', 64, 64, 'self', false)],
  maybe_disabled_imprison: [R('tackle', 56, 56, 'normal', false), R('rest', 8, 8, 'self', false), R('curse', 16, 16, 'self', false), R('splash', 63, 64, 'self', false)],
  maybe_disabled_imprison_mirror: [R('tackle', 56, 56, 'normal', false), R('rest', 8, 8, 'self', false), R('curse', 16, 16, 'self', false), R('splash', 63, 64, 'self', false)],
  maybe_trapped_shadow_tag: [R('tackle', 56, 56, 'normal', false), R('splash', 64, 64, 'self', false)],
  maybe_trapped_shadow_tag_mirror: [R('tackle', 56, 56, 'normal', false), R('splash', 64, 64, 'self', false)],
  known_trapped_mean_look: [R('tackle', 56, 56, 'normal', false), R('splash', 63, 64, 'self', false)],
  known_trapped_mean_look_mirror: [R('tackle', 56, 56, 'normal', false), R('splash', 63, 64, 'self', false)],
  struggle_maybe_disabled: [R('struggle', null, null, 'randomNormal', false)], struggle_all_pp_zero: [R('struggle', null, null, 'randomNormal', false)],
  outrage_lock: LOCKROW('outrage'), rollout_lock: LOCKROW('rollout'), uproar_lock: LOCKROW('uproar'), locked_empty_bench: LOCKROW('solarbeam'),
  maybe_trapped_empty_bench: [R('tackle', 56, 56, 'normal', false), R('splash', 64, 64, 'self', false)],
  trapped_after_rejection: [R('tackle', 56, 56, 'normal', false), R('splash', 64, 64, 'self', false)],
  unicode_names: [R('tackle', 56, 56, 'normal', false), R('splash', 64, 64, 'self', false)],
};
/** Non-subject owner rows per case (hand-audited from the raw texts); every one is a plain request. */
const SPLASH63 = [R('splash', 63, 64, 'self', false)], SPLASH64 = [R('splash', 64, 64, 'self', false)];
const SPLASH_TACKLE = [R('splash', 64, 64, 'self', false), R('tackle', 56, 56, 'normal', false)];
const IMPRISON = [R('imprison', 15, 16, 'self', false), R('tackle', 56, 56, 'normal', false)];
const TAUNT = [R('taunt', 31, 32, 'normal', false), R('splash', 64, 64, 'self', false)];
const SPITE = [R('spite', 14, 16, 'normal', false), R('splash', 64, 64, 'self', false)];
const MEANLOOK = [R('meanlook', 7, 8, 'normal', false), R('splash', 64, 64, 'self', false)];
const OTHER: Record<string, Json[]> = {
  ordinary_slots: SPLASH_TACKLE, choice_lock_soft: SPLASH63, encore_soft: [R('encore', 7, 8, 'normal', false), R('splash', 64, 64, 'self', false)],
  two_turn_locked_move: SPLASH63, two_turn_locked_move_mirror: SPLASH63, recharge: SPLASH63, recharge_mirror: SPLASH63,
  struggle_fallback: TAUNT, struggle_fallback_mirror: TAUNT, real_pp_zero: SPITE,
  maybe_disabled_imprison: IMPRISON, maybe_disabled_imprison_mirror: IMPRISON, maybe_trapped_shadow_tag: SPLASH64, maybe_trapped_shadow_tag_mirror: SPLASH64,
  known_trapped_mean_look: MEANLOOK, known_trapped_mean_look_mirror: MEANLOOK,
  struggle_maybe_disabled: [R('imprison', 15, 16, 'self', false), R('splash', 64, 64, 'self', false)], struggle_all_pp_zero: SPITE,
  outrage_lock: SPLASH63, rollout_lock: SPLASH63, uproar_lock: SPLASH63, maybe_trapped_empty_bench: SPLASH64, locked_empty_bench: SPLASH63,
  trapped_after_rejection: SPLASH64, unicode_names: SPLASH_TACKLE,
};
/** Exact subject-owner lock per case; every other actionable record is no_hard_lock (soft locks Choice/Encore/PP-0 included). */
const LOCK: Record<string, string> = {
  two_turn_locked_move: 'locked_move', two_turn_locked_move_mirror: 'locked_move', recharge: 'recharge', recharge_mirror: 'recharge',
  struggle_fallback: 'struggle', struggle_fallback_mirror: 'struggle', struggle_maybe_disabled: 'struggle', struggle_all_pp_zero: 'struggle',
  outrage_lock: 'locked_move', rollout_lock: 'locked_move', uproar_lock: 'locked_move', locked_empty_bench: 'locked_move',
};
const PRESENCE: Record<string, Record<string, string>> = {
  waiting_and_forced_switch: { p1: 'waiting', p2: 'forced_switch' }, revival_selection_and_waiting: { p1: 'revival_selection', p2: 'waiting' },
  terminal_requestless: { p1: 'terminal', p2: 'terminal' },
};
const NON_ACTIONABLE = new Set(Object.keys(PRESENCE));

retiredTest('CONTROL: 28 cases (20 prompt13 + 8 decision-6/Unicode), observation pins reproduce byte-for-byte, helper reseal reproduces identities', async () => {
  const cases = await captured;
  assert.equal(Object.keys(cases).length, 28);
  const pins = JSON.parse(readFileSync(path.join(repositoryRoot, 'docs/planning/perspective-fidelity-prompt13-observation-pins.json'), 'utf8')).pins;
  assert.equal(Object.keys(pins).length, 20);
  let checked = 0;
  for (const [id, entries] of Object.entries<Json>(pins)) {
    for (const [key, pin] of Object.entries<Json>(entries)) {
      const [version, owner] = key.split('/');
      const observation = observationOf(cases[id], owner, `observable-battle-state/${version}`);
      assert.equal(observation.observation_id, pin.observation_id, `${id} ${key}`);
      assert.equal(sha(canon(observation)), pin.observation_sha256, `${id} ${key}`);
      assert.equal(sha(canon(observation.request)), pin.request_sha256, `${id} ${key}`);
      checked += 1;
    }
  }
  assert.equal(checked, 80);
  for (const c of Object.values<Json>(cases)) for (const owner of OWNERS) assert.equal(reseal(observationOf(c, owner)).observation_id, observationOf(c, owner).observation_id);
});

retiredTest('records match raw text and hand-audited literals for every case, owner and version; ids are recomputed independently', async () => {
  const cases = await captured;
  let built = 0;
  for (const [id, c] of Object.entries(cases)) {
    for (const version of [V1, V2]) for (const owner of OWNERS) {
      if (id === 'trapped_after_rejection' && owner === 'p1') continue; // observation is the stale restored one; see restoration test
      const record = build(c, owner, version);
      built += 1;
      const label = `${id} ${version} ${owner}`;
      const observation = observationOf(c, owner, version);
      const expectedPresence = PRESENCE[id]?.[owner] ?? 'actionable';
      assert.equal(record.presence, expectedPresence, label);
      assert.equal(record.schema_version, 'request-knowledge/v1');
      assert.deepEqual([record.battle_id, record.perspective, record.observation_schema_version, record.observation_id, record.event_cursor],
        [observation.battle_id, owner, version, observation.observation_id, observation.event_cursor], label);
      assert.equal(record.request_present, expectedPresence !== 'terminal');
      assert.equal(record.raw_request, expectedPresence === 'terminal' ? null : c.raw[owner].json, label);
      assert.equal(record.rqid, null, label);
      assert.equal(record.id, 'rkn-' + sha('request-knowledge/v1\n' + canon((({ id: _i, ...rest }) => rest)(record))), label); // independent canonical + hash
      if (expectedPresence !== 'actionable') { assert.equal(record.active, null, label); continue; }
      const [subject, flags] = FLAGS[id] ?? ['p1', PLAIN];
      const expected = owner === subject ? flags : PLAIN;
      const { moves, ...core } = record.active;
      assert.deepEqual(core, expected, label);
      assert.deepEqual(moves, independentMoves(c.raw[owner].json), label); // raw-derived expectation
      const literal = owner === subject ? MOVES[id] : OTHER[id];
      assert.ok(literal, `missing hand-audited literal for ${label}`);
      assert.deepEqual(moves.map((m: Json) => [m.id, m.pp, m.max_pp, m.target, m.disabled]), literal, label); // literal
      assert.equal(record.active.lock, owner === subject ? (LOCK[id] ?? 'no_hard_lock') : 'no_hard_lock', label);
    }
  }
  assert.equal(built, 110);
});

retiredTest('group 1: locked, recharge and Struggle records carry nulls and a lock, ordinary rows are non-null, both owners', async () => {
  const cases = await captured;
  for (const id of ['two_turn_locked_move', 'two_turn_locked_move_mirror', 'recharge', 'recharge_mirror', 'outrage_lock', 'rollout_lock', 'uproar_lock']) {
    const owner = id.endsWith('_mirror') ? 'p2' : 'p1';
    const record = build(cases[id], owner);
    assert.equal(record.active.trapped, true);
    assert.equal(record.active.lock, LOCK[id], id);
    assert.equal(record.active.derivation.lock, 'bare_single_row');
    assert.deepEqual(Object.keys(JSON.parse(record.raw_request).active[0].moves[0]), ['move', 'id']);
    for (const key of ['pp', 'max_pp', 'target', 'disabled']) assert.equal(record.active.moves[0][key], null, `${id} ${key}`);
  }
  for (const id of ['struggle_fallback', 'struggle_fallback_mirror', 'struggle_maybe_disabled', 'struggle_all_pp_zero']) {
    const owner = id.endsWith('_mirror') ? 'p2' : 'p1';
    const row = build(cases[id], owner).active.moves[0];
    assert.deepEqual([row.pp, row.max_pp, row.target, row.disabled], [null, null, 'randomNormal', false], id);
    assert.equal(build(cases[id], owner).active.lock, 'struggle', id);
  }
  for (const owner of OWNERS) for (const row of build(cases.ordinary_slots, owner).active.moves) {
    for (const key of ['pp', 'max_pp', 'target', 'disabled']) assert.notEqual(row[key], null);
  }
  assert.equal(build(cases.recharge, 'p1').active.lock, 'recharge');
  assert.equal(build(cases.recharge, 'p1').active.moves[0].name, 'Recharge');
});

retiredTest('group 2: real PP 0 differs from absent PP; an explicit zero/normal/false raw row differs from an omitted raw row under the same observation', async () => {
  const cases = await captured;
  const zero = build(cases.real_pp_zero, 'p1').active.moves[0];
  assert.deepEqual([zero.pp, zero.max_pp, zero.disabled], [0, 8, true]);
  const locked = cases.two_turn_locked_move;
  const omitted = build(locked, 'p1');
  const explicitText = JSON.stringify((() => { const r = JSON.parse(locked.raw.p1.json); Object.assign(r.active[0].moves[0], { pp: 0, maxpp: 0, target: 'normal', disabled: false }); return r; })());
  const explicit = buildRequestKnowledge('p1', explicitText, observationOf(locked, 'p1'), FRESH); // the legacy observation cannot tell them apart
  assert.deepEqual(explicit.active.moves[0], { slot: 1, id: 'solarbeam', name: 'Solar Beam', pp: 0, max_pp: 0, target: 'normal', disabled: false });
  assert.equal(explicit.active.lock, 'no_hard_lock');
  assert.equal(explicit.active.derivation.lock, 'pp_bearing_rows');
  assert.equal(omitted.active.lock, 'locked_move');
  assert.notEqual(explicit.id, omitted.id);
});

retiredTest('group 3: maybeDisabled, maybeTrapped, known trap and nothing are four distinct records; absent without a switch-in is null', async () => {
  const cases = await captured;
  const ids = new Set(['maybe_disabled_imprison', 'maybe_trapped_shadow_tag', 'known_trapped_mean_look', 'ordinary_slots'].map((id) => build(cases[id], 'p1').id));
  assert.equal(ids.size, 4);
  const flags = (id: string) => { const a = build(cases[id], 'p1').active; return [a.trapped, a.maybe_trapped, a.maybe_disabled]; };
  assert.deepEqual(flags('maybe_disabled_imprison'), [false, false, true]);
  assert.deepEqual(flags('maybe_trapped_shadow_tag'), [false, true, false]);
  assert.deepEqual(flags('known_trapped_mean_look'), [true, false, false]);
  assert.deepEqual(flags('maybe_trapped_empty_bench'), [null, null, false]);
  assert.deepEqual(flags('locked_empty_bench'), [null, null, false]);
  // The flag text is the only difference: stripping it from the raw (same observation) changes the record, not the legal set.
  for (const [id, key] of [['maybe_disabled_imprison', 'maybeDisabled'], ['maybe_trapped_shadow_tag', 'maybeTrapped']]) {
    const c = cases[id];
    const raw = JSON.parse(c.raw.p1.json); delete raw.active[0][key];
    const stripped = buildRequestKnowledge('p1', JSON.stringify(raw), observationOf(c, 'p1'), FRESH);
    assert.notEqual(stripped.id, build(c, 'p1').id);
    assert.deepEqual(buildLegalActionSet(raw), buildLegalActionSet(JSON.parse(c.raw.p1.json)));
    assert.deepEqual(observationOf(c, 'p1').request.legal_actions, buildLegalActionSet(JSON.parse(c.raw.p1.json)));
  }
});

retiredTest('group 4: waiting, forced switch, revival and terminal have no active slots, correct presence, null raw only for terminal, both owners', async () => {
  const cases = await captured;
  const wf = cases.waiting_and_forced_switch; const rv = cases.revival_selection_and_waiting; const term = cases.terminal_requestless;
  for (const [c, owner, presence] of [[wf, 'p1', 'waiting'], [wf, 'p2', 'forced_switch'], [rv, 'p1', 'revival_selection'], [rv, 'p2', 'waiting'], [term, 'p1', 'terminal'], [term, 'p2', 'terminal']] as Json[]) {
    const record = build(c, owner);
    assert.equal(record.presence, presence); assert.equal(record.active, null);
    assert.equal(record.request_present, presence !== 'terminal');
    assert.equal(record.raw_request === null, presence === 'terminal');
  }
  assert.equal(build(wf, 'p1').raw_request!.startsWith('{"wait":true'), true);
  assert.equal(build(rv, 'p1').raw_request!.includes('"reviving":true'), true);
  // The terminal owners had real earlier requests; a terminal record must not be built from them.
  assert.equal(codeOf(() => buildRequestKnowledge('p1', term.raw.p1.json, observationOf(term, 'p1'), FRESH)), 'presence-mismatch');
  // Requestless (non-terminal, no request) is accepted only with null raw.
  const requestless = reseal({ ...clone(observationOf(wf, 'p1')), request: null, decision_availability: { available: false, reason: 'requestless', legal_action_indices: null } });
  assert.equal(buildRequestKnowledge('p1', null, requestless, FRESH).presence, 'requestless');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', wf.raw.p1.json, requestless, FRESH)), 'presence-mismatch');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', null, observationOf(wf, 'p1'), FRESH)), 'presence-mismatch');
});

/** Fresh (post-rejection) observation consistent with the harness text: the legacy normalizer applied to the freshly delivered request. */
function freshObservation(c: Json): { observation: Json; text: string; stale: Json } {
  const stale = observationOf(c, 'p1');
  const text = c.raw_history.p1[1];
  const { raw: _raw, ...request } = normalizeRequest('p1', JSON.parse(text));
  const observation = reseal({ ...clone(stale), request: clone(request), decision_availability: { available: true, reason: 'request', legal_action_indices: request.legal_actions.available_indices } });
  return { observation, text, stale };
}

retiredTest('group 5 and decision 3: rejection rollback gives two distinct records; a restored-session request is refused, fresh text builds trapped:true', async () => {
  const c = (await captured).trapped_after_rejection;
  const { observation, text, stale } = freshObservation(c);
  const before = buildRequestKnowledge('p1', c.raw_history.p1[0], stale, FRESH); // genuinely delivered earlier; matches the restored observation
  const after = buildRequestKnowledge('p1', text, observation, FRESH);
  assert.equal(text, c.raw.p1.json);
  assert.deepEqual([before.active.trapped, before.active.maybe_trapped], [false, true]);
  assert.deepEqual([after.active.trapped, after.active.maybe_trapped, after.active.derivation.trapped], [true, false, 'raw_true']);
  assert.notEqual(before.id, after.id);
  assert.notEqual(before.observation_id, after.observation_id);
  // Restored StepResult.requests are refused by provenance, whatever the text.
  for (const provenance of ['restored_session', 'restored', '', 'FRESH_DELIVERY']) assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw_history.p1[0], stale, provenance)), 'provenance');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw_history.p1[0], stale, undefined as unknown as string)), 'provenance');
  // The live restored request is the stale pre-rejection text: it must not be joinable to the fresh observation, nor the fresh text to the stale one.
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw_history.p1[0], observation, FRESH)), 'observation-mismatch');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', text, stale, FRESH)), 'observation-mismatch');
  assert.equal(observationOf(c, 'p1').request.active.trapped, false); // the restored observation is the stale one
});

retiredTest('group 6: building never changes observations or legal sets, is pure and deterministic, and sidecar code cannot reach legal-action construction', async () => {
  const cases = await captured;
  for (const [id, c] of Object.entries(cases)) for (const owner of OWNERS) {
    if (id === 'trapped_after_rejection' && owner === 'p1') continue;
    const observation = deepFreeze(clone(observationOf(c, owner)));
    const before = canon(observation);
    const first = buildRequestKnowledge(owner, rawTextOf(c, owner), observation, FRESH);
    const second = buildRequestKnowledge(owner, rawTextOf(c, owner), observation, FRESH);
    assert.equal(canon(observation), before, id);
    assert.deepEqual(first, second);
    if (observation.request && !observation.request.wait) assert.deepEqual(observation.request.legal_actions, buildLegalActionSet(JSON.parse(c.raw[owner].json)), id);
  }
  const source = readFileSync(path.join(repositoryRoot, 'sim-core/src/request_knowledge.ts'), 'utf8');
  assert.equal(/from '\.\/(action_codec|env_manager|state_extractor|pipeline_)/.test(source), false);
  assert.equal(/buildLegalActionSet|normalizeRequest/.test(source), false);
});

retiredTest('builder grammar negatives: doubles, team preview, no_legal_actions, unknown keys, wrong owner, wrong presence, duplicate key, oversize', async () => {
  const cases = await captured;
  const c = cases.maybe_trapped_shadow_tag;
  const observation = observationOf(c, 'p1');
  const raw = JSON.parse(c.raw.p1.json);
  const withRaw = (mutate: (r: Json) => void, obs = observation) => { const r = clone(raw); mutate(r); return codeOf(() => buildRequestKnowledge('p1', JSON.stringify(r), obs, FRESH)); };
  assert.equal(withRaw((r) => r.active.push(clone(r.active[0]))), 'doubles');
  assert.equal(withRaw((r) => { r.side.pokemon[1].active = true; }), 'doubles');
  assert.equal(withRaw((r) => { r.teamPreview = true; }), 'team-preview');
  assert.equal(withRaw((r) => { r.active[0].canMegaEvo = true; }), 'raw-grammar');
  assert.equal(withRaw((r) => { r.active[0].moves[0].extra = 1; }), 'raw-grammar');
  assert.equal(withRaw((r) => { r.active[0].trapped = false; }), 'raw-grammar');
  assert.equal(withRaw((r) => { r.active[0].trapped = true; }), 'raw-grammar'); // trapped and maybeTrapped together
  assert.equal(withRaw((r) => { r.active[0].moves[0].pp = 1.5; }), 'raw-json');
  assert.equal(withRaw((r) => { r.side.id = 'p2'; }), 'wrong-owner');
  assert.equal(withRaw((r) => { r.side.pokemon.forEach((p: Json) => { p.ident = p.ident.replace('p1:', 'p2:'); }); }), 'wrong-owner');
  assert.equal(withRaw((r) => { r.active[0].moves[0].pp = 3; }), 'observation-mismatch');
  assert.equal(withRaw((r) => { r.active[0].moves[0].disabled = true; }), 'observation-mismatch');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json.replace('"maybeTrapped":true', '"maybeTrapped":true,"maybeTrapped":true'), observation, FRESH)), 'raw-json');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', ' '.repeat(65537) + c.raw.p1.json, observation, FRESH)), 'raw-size');
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p2.json, observation, FRESH)), 'wrong-owner'); // other owner's raw
  assert.equal(codeOf(() => buildRequestKnowledge('p2', c.raw.p2.json, observation, FRESH)), 'wrong-owner'); // other owner's observation
  assert.equal(codeOf(() => buildRequestKnowledge('p3', c.raw.p1.json, observation, FRESH)), 'wrong-owner');
  // Doubles in a forced-switch request.
  const forced = cases.waiting_and_forced_switch;
  const forcedRaw = JSON.parse(forced.raw.p2.json); forcedRaw.forceSwitch = [true, false];
  assert.equal(codeOf(() => buildRequestKnowledge('p2', JSON.stringify(forcedRaw), observationOf(forced, 'p2'), FRESH)), 'doubles');
  // Legality drift: a numbered move action the request does not support.
  const tampered = clone(observation); tampered.request.legal_actions.actions[0] = { ...tampered.request.legal_actions.actions[0], slot: 9 };
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json, tampered, FRESH)), 'legality-mismatch');
  // no_legal_actions (synthetic: engine paths never produce it) is rejected, not mapped.
  const none = clone(observation); none.request.legal_actions.available_indices = [];
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json, none, FRESH)), 'no-legal-actions');
  const unavailable = clone(observation); unavailable.decision_availability.available = false;
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json, unavailable, FRESH)), 'no-legal-actions');
  const preview = clone(observation); preview.request.team_preview = true;
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json, preview, FRESH)), 'team-preview');
});

retiredTest('Unicode names: the exact non-ASCII text round-trips through the record and the canonical bytes', async () => {
  const c = (await captured).unicode_names;
  const record = build(c, 'p1');
  assert.ok(record.raw_request.includes('p1: Ñandú 日本'));
  assert.equal(JSON.parse(record.raw_request).side.pokemon[0].ident, 'p1: Ñandú 日本');
  const bytes = Buffer.from(canonicalRequestKnowledgeJson(record), 'utf8');
  assert.deepEqual(JSON.parse(bytes.toString('utf8')), record);
  assert.equal(requestKnowledgeId(record), record.id);
});

// ------------------------------------------------------------------------------------------ cross-runtime
function runPython(args: string[], input: string) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  assert.ok(!Object.keys(env).some((key) => ['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  return spawnSync(process.env.PYTHON || 'python3', args, {
    cwd: repositoryRoot, env: { ...env, PYTHONPATH: path.resolve(repositoryRoot, 'trainer/src') }, input: Buffer.from(input, 'utf8'), timeout: 120_000, maxBuffer: 1 << 28,
  });
}

retiredTest('parity: Python builds byte-identical canonical records (110 case/version/owner) and its independent validator accepts them (UTF-8 env unset)', async () => {
  const cases = await captured;
  const jobs: Json[] = []; const expected: string[] = [];
  for (const [id, c] of Object.entries(cases)) for (const version of [V1, V2]) for (const owner of OWNERS) {
    if (id === 'trapped_after_rejection' && owner === 'p1') continue;
    jobs.push({ owner, raw_request: rawTextOf(c, owner, version), observation: observationOf(c, owner, version) });
    expected.push(canonicalRequestKnowledgeJson(build(c, owner, version)));
  }
  assert.equal(jobs.length, 110);
  const built = runPython(['-m', 'neural.request_knowledge', 'build'], JSON.stringify(jobs));
  assert.equal(built.status, 0, built.stderr.toString('utf8'));
  const lines = built.stdout.toString('utf8').split('\n'); lines.pop();
  assert.equal(lines.length, 110);
  lines.forEach((line, index) => assert.equal(line, expected[index], `job ${index}`));
  assert.ok(lines.some((line) => line.includes('Ñandú 日本')), 'non-ASCII text survives Python UTF-8 output');
  const validated = runPython(['-m', 'neural.request_knowledge', 'validate'], JSON.stringify(jobs.map((job, index) => ({ record: JSON.parse(lines[index]), observation: job.observation }))));
  assert.equal(validated.status, 0, validated.stderr.toString('utf8'));
  const results = validated.stdout.toString('utf8').split('\n'); results.pop();
  assert.equal(results.length, 110);
  results.forEach((line, index) => assert.deepEqual(JSON.parse(line), { record_id: JSON.parse(lines[index]).id, presence: JSON.parse(lines[index]).presence, delivery_authority: 'structure_only' }));
});

retiredTest('correction round: 256-scalar caps, wait+noCancel, canonical string cap, non-null rqid positive path', async () => {
  const cases = await captured;
  const c = cases.ordinary_slots; const base = observationOf(c, 'p1');
  // battle_id and canonical string caps (raw_request alone may be long).
  assert.equal(codeOf(() => buildRequestKnowledge('p1', c.raw.p1.json, reseal({ ...clone(base), battle_id: 'b'.repeat(257) }), FRESH)), 'observation-mismatch');
  assert.equal(buildRequestKnowledge('p1', c.raw.p1.json, reseal({ ...clone(base), battle_id: 'b'.repeat(256) }), FRESH).battle_id.length, 256);
  assert.equal(codeOf(() => canonicalRequestKnowledgeJson({ battle_id: 'x'.repeat(257) })), 'wire-size');
  assert.equal(codeOf(() => canonicalRequestKnowledgeJson({ id: 'x'.repeat(257) })), 'wire-size');
  assert.equal(canonicalRequestKnowledgeJson({ raw_request: 'x'.repeat(300) }).length > 300, true);
  // Move id/name/target over 256 scalars never builds (raw parser or row grammar rejects).
  for (const key of ['move', 'id', 'target']) {
    const raw = JSON.parse(c.raw.p1.json); raw.active[0].moves[0][key] = 'm'.repeat(257);
    assert.ok(['raw-json', 'raw-grammar'].includes(codeOf(() => buildRequestKnowledge('p1', JSON.stringify(raw), base, FRESH))), key);
  }
  // noCancel is only legal with forceSwitch.
  const wf = cases.waiting_and_forced_switch;
  const waiting = JSON.parse(wf.raw.p1.json); waiting.noCancel = true;
  assert.equal(codeOf(() => buildRequestKnowledge('p1', JSON.stringify(waiting), observationOf(wf, 'p1'), FRESH)), 'raw-grammar');
  const active = JSON.parse(c.raw.p1.json); active.noCancel = true;
  assert.equal(codeOf(() => buildRequestKnowledge('p1', JSON.stringify(active), base, FRESH)), 'raw-grammar');
  assert.equal(buildRequestKnowledge('p2', wf.raw.p2.json, observationOf(wf, 'p2'), FRESH).presence, 'forced_switch'); // real forceSwitch carries noCancel
  // The pinned stream emits no rqid; hand-audited literal positive: rqid 7 in the text, in the normalized observation, in the record.
  const raw = JSON.parse(c.raw.p1.json); raw.rqid = 7;
  const text = JSON.stringify(raw);
  const { raw: _raw, ...request } = normalizeRequest('p1', raw);
  assert.equal(request.rqid, 7);
  const observation = reseal({ ...clone(base), request: clone(request) });
  const record = buildRequestKnowledge('p1', text, observation, FRESH);
  assert.equal(record.rqid, 7);
  assert.equal(codeOf(() => buildRequestKnowledge('p1', text, base, FRESH)), 'observation-mismatch'); // observation says rqid null
  raw.rqid = '7';
  assert.equal(codeOf(() => buildRequestKnowledge('p1', JSON.stringify(raw), observation, FRESH)), 'raw-grammar');
  assert.notEqual(record.id, buildRequestKnowledge('p1', c.raw.p1.json, base, FRESH).id);
});
