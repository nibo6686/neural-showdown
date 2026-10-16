import assert from 'node:assert/strict';
import test from 'node:test';
import { BattleStream, Teams } from 'pokemon-showdown';
import { NativeBirthEnrollment } from '../src/owner_identity_crosswalk';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { LocalBattleEnv } from '../src/env_manager';
import type { PlayerID } from '../src/types';

const owners = ['p1', 'p2'] as const;
const options = { battle_id: 'B1', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
const env = (s: PipelineIntegrationSession): LocalBattleEnv => (s as any).environment;
const holding = (s: PipelineIntegrationSession, owner: PlayerID) => s.readNativeBirthHolding(s.getNativeBirthHolding(owner), owner);
const original = (s: PipelineIntegrationSession, owner: PlayerID) => s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(owner), owner);
const evidence = (name: string, data: object) => console.log('B1_WITNESS ' + JSON.stringify({ name, ...data }));
type EnrollmentArgs = Parameters<NativeBirthEnrollment['enroll']>;

async function observe<T>(body: (rows: Array<{ controller: NativeBirthEnrollment; args: EnrollmentArgs; before: unknown[] }>) => Promise<T>) {
  const enroll = NativeBirthEnrollment.prototype.enroll;
  const rows: Array<{ controller: NativeBirthEnrollment; args: EnrollmentArgs; before: unknown[] }> = [];
  NativeBirthEnrollment.prototype.enroll = function(...args) {
    assert.ok(!args[1].started && !args[1].sides[args[3] === 'p1' ? 0 : 1]);
    for (const owner of owners) assert.throws(() => this.holding(owner), /unavailable/);
    rows.push({ controller: this, args, before: structuredClone([...args[5]]) });
    return enroll.apply(this, args);
  };
  try { return await body(rows); } finally { NativeBirthEnrollment.prototype.enroll = enroll; }
}

test('B1 generated creation', async () => observe(async rows => {
  let session: PipelineIntegrationSession | undefined;
  try {
    session = await PipelineIntegrationSession.create(options);
    assert.equal(rows.length, 2); assert.equal(rows[0].controller, rows[1].controller);
    assert.notEqual(rows[0].args[2], rows[1].args[2], 'distinct submitted owner occurrences');
    for (const [i, owner] of owners.entries()) {
      const row = rows[i], born = holding(session, owner), held = original(session, owner);
      assert.equal(row.args[3], owner); assert.equal(born.original, held); assert.equal(born.slot_count, 6);
      assert.equal((row.args[4] as { team: string }).team, held.packed_team);
      assert.deepEqual(row.before, Teams.unpack(held.packed_team));
      const side = row.args[1][owner]!;
      for (const [j, set] of row.args[5].entries()) assert.equal(side.team[j], set);
      assert.ok(side.pokemon.every(p => row.args[5].includes(p.set)));
      assert.ok(Object.isFrozen(born) && Object.isFrozen(held.raw_team));
      assert.deepEqual(Object.keys(born), ['owner', 'original', 'slot_count']);
    }
    evidence('generated', { level: 'actual-generated-session', owners: owners.map(owner => ({ owner, slots: holding(session!, owner).slot_count })),
      before_construction: true, original_reference_binding: true, separate_occurrences: true });
  } finally { await session?.close(); }
}));

test('B1 initial effects', async () => {
  const controls = [
    ['Trace', 'Alakazam\nAbility: Trace\n- Splash', 'Alakazam', 'naturalcure', 'splash'],
    ['Imposter', 'Ditto\nAbility: Imposter\n- Transform', 'Blissey', 'naturalcure', 'softboiled'],
    ['Schooling', 'Wishiwashi\nAbility: Schooling\nLevel: 100\n- Splash', 'Wishiwashi-School', 'schooling', 'splash'],
    ['Crowned', 'Zacian @ Rusted Sword\nAbility: Intrepid Sword\n- Iron Head', 'Zacian-Crowned', 'intrepidsword', 'behemothblade'],
  ];
  for (const owner of owners) for (const [label, text, species, ability, move] of controls) {
    await observe(async rows => {
      const generate = Teams.generate; let calls = 0, session: PipelineIntegrationSession | undefined;
      const raw = Teams.import(text)!;
      Teams.generate = function() { return structuredClone(owners[calls++] === owner ? raw : Teams.import('Blissey\nAbility: Natural Cure\n- Soft-Boiled')!); };
      try {
        session = await PipelineIntegrationSession.create(options);
        const row = rows.find(r => r.args[3] === owner)!; const native = row.args[1][owner]!.active[0];
        assert.equal(native.set, row.args[5][0]); assert.equal(native.species.name, species); assert.equal(native.ability, ability);
        assert.equal((row.args[1][owner]!.activeRequest as any).active[0].moves[0].id, move);
        assert.deepEqual(holding(session, owner).original.raw_team, raw);
        assert.equal(holding(session, owner).original, original(session, owner));
        assert.notEqual(row.before[0], native.set);
        evidence(label + '-' + owner, { level: 'actual-session-constructed-mechanic', owner, before_species: (row.before[0] as any).species,
          current_species: species, move, same_set_reference: true, generated_reachability: 'not-certified' });
      } finally { Teams.generate = generate; await session?.close(); }
    });
  }
});

test('B1 enrollment faults', async () => {
  const enroll = NativeBirthEnrollment.prototype.enroll, observer = NativeBirthEnrollment.prototype.observe;
  const activate = NativeBirthEnrollment.prototype.activate, pushError = BattleStream.prototype.pushError, generate = Teams.generate, close = LocalBattleEnv.prototype.close;
  const cases: Array<[string, RegExp]> = [
    ['missing-owner', /missing-enrollment/], ['duplicate', /duplicate-enrollment/], ['wrong-owner-equal-bytes', /foreign-or-late-enrollment/],
    ['submission', /submission-mismatch/], ['occurrence', /foreign-or-late-enrollment/], ['environment', /foreign-or-late-enrollment/],
    ['side-reference', /constructor-association-mismatch/], ['pokemon-reference', /constructor-association-mismatch/],
    ['late', /foreign-or-late-enrollment/], ['missing-observer', /not-staged/], ['late-observer', /late-observer/],
  ];
  for (const [fault, pattern] of cases) {
    let controller: NativeBirthEnrollment | undefined, saved: EnrollmentArgs | undefined;
    const nativeErrors: string[] = []; let cleanupChecks = 0;
    LocalBattleEnv.prototype.close = function() {
      assert.ok(controller);
      for (const owner of owners) assert.throws(() => controller!.holding(owner), /unavailable/);
      cleanupChecks++; return close.call(this);
    };
    BattleStream.prototype.pushError = function(error, recoverable) { nativeErrors.push(error.message); return pushError.call(this, error, recoverable); };
    NativeBirthEnrollment.prototype.observe = function(environment, battle) {
      controller = this;
      if (fault === 'missing-observer') return;
      if (fault === 'late-observer') battle.started = true;
      return observer.call(this, environment, battle);
    };
    if (fault === 'wrong-owner-equal-bytes') Teams.generate = function() { return Teams.import('Same (Snorlax)\nAbility: Immunity\n- Splash')!; };
    NativeBirthEnrollment.prototype.enroll = function(...args) {
      controller = this; saved = args;
      if (fault === 'missing-owner' && args[3] === 'p2') return;
      if (fault === 'wrong-owner-equal-bytes') args[3] = 'p2';
      if (fault === 'submission') (args[4] as { team: string }).team += '|foreign';
      if (fault === 'occurrence') args[2] = {};
      if (fault === 'environment') args[0] = {};
      enroll.apply(this, args);
      if (fault === 'duplicate') enroll.apply(this, args);
    };
    NativeBirthEnrollment.prototype.activate = function() {
      if (fault === 'late') return enroll.apply(this, saved!);
      const side = saved?.[1].p1;
      if (fault === 'side-reference') {
        assert.ok(side); side.team[0] = { ...side.team[0] }; // Equal values are not the enrolled reference.
      }
      if (fault === 'pokemon-reference') {
        assert.ok(side); Object.defineProperty(side.pokemon[1], 'set', { value: side.pokemon[0].set });
      }
      return activate.call(this);
    };
    try {
      let outer: Error | undefined;
      await assert.rejects(PipelineIntegrationSession.create(options), (error: Error) => { outer = error; return true; });
      assert.ok([...nativeErrors, outer!.message].some(message => pattern.test(message)), 'exact B1 semantic rejection: ' + fault);
      assert.ok(controller); assert.ok(cleanupChecks > 0, 'revocation observed before cleanup');
      for (const owner of owners) assert.throws(() => controller!.holding(owner), /unavailable/);
      evidence(fault, { level: 'actual-runtime-fault-rejection', expected: pattern.source, authority_unavailable_both_owners: true, revoked_before_cleanup: true });
    } finally {
      NativeBirthEnrollment.prototype.enroll = enroll; NativeBirthEnrollment.prototype.observe = observer;
      NativeBirthEnrollment.prototype.activate = activate; BattleStream.prototype.pushError = pushError; Teams.generate = generate; LocalBattleEnv.prototype.close = close;
    }
  }
});

test('B1 owner isolation', async () => {
  let session: PipelineIntegrationSession | undefined, foreign: PipelineIntegrationSession | undefined;
  try {
    session = await PipelineIntegrationSession.create(options); foreign = await PipelineIntegrationSession.create(options);
    for (const owner of owners) {
      const handle = session.getNativeBirthHolding(owner), other = owner === 'p1' ? 'p2' : 'p1';
      assert.throws(() => session!.readNativeBirthHolding(handle, other), /foreign-or-forged-holding/);
      for (const copied of [{}, { ...handle }, structuredClone(handle), JSON.parse(JSON.stringify(handle)), foreign.getNativeBirthHolding(owner)]) {
        assert.throws(() => session!.readNativeBirthHolding(copied, owner), /foreign-or-forged-holding/);
      }
      assert.equal(session.readNativeBirthHolding(handle, owner).original.owner, owner);
      assert.equal(Reflect.ownKeys(handle).length, 0);
      const view = session.boundary.perspectives[owner].observation;
      const wire = JSON.stringify({ view, boundary: session.boundary, snapshot: env(session).serializeBattle(), diagnostics: env(session).diagnostics() });
      for (const forbidden of ['nativeBirth', 'NativeBirth', 'slot_count', 'creation_sequence', 'raw_team', 'packed_team', 'occurrence']) assert.ok(!wire.includes('"' + forbidden + '"'));
      assert.ok(!Object.keys(session).some(key => /birth|original/i.test(key)));
      assert.deepEqual(Object.keys(holding(session, owner)), ['owner', 'original', 'slot_count']);
    }
    // Existing raw native snapshots intentionally contain engine sets/seeds. B1 adds none;
    // the exact preservation control checks those historical bytes independently.
    evidence('isolation', { level: 'actual-generated-session', cross_owner_rejects: 2, forged_or_foreign_rejects: 10,
      private_controller_not_enumerable: true, no_birth_fields_in_existing_outputs: true });
  } finally { await session?.close(); await foreign?.close(); }
});

test('B1 activation failure', async () => {
  const activate = NativeBirthEnrollment.prototype.activate, close = LocalBattleEnv.prototype.close, enroll = NativeBirthEnrollment.prototype.enroll;
  let enrollments = 0;
  NativeBirthEnrollment.prototype.enroll = function(...args) { const value = enroll.apply(this, args); enrollments++; return value; };
  let controller: NativeBirthEnrollment | undefined;
  let release!: () => void, reached!: () => void;
  const cleanupGate = new Promise<void>(resolve => { release = resolve; });
  const cleanupReached = new Promise<void>(resolve => { reached = resolve; });
  NativeBirthEnrollment.prototype.activate = function() {
    controller = this; assert.equal(enrollments, 2);
    for (const owner of owners) assert.throws(() => this.holding(owner), /unavailable/);
    throw new Error('B1-after-tentative-before-activation');
  };
  LocalBattleEnv.prototype.close = async function() {
    if (controller) for (const owner of owners) assert.throws(() => controller!.holding(owner), /unavailable/);
    reached(); await cleanupGate; return close.call(this);
  };
  const creation = PipelineIntegrationSession.create(options);
  // Attach rejection handling before waiting so the harness has no unhandled promise.
  const rejected = assert.rejects(creation, /B1-after-tentative-before-activation/);
  try {
    await cleanupReached; assert.ok(controller);
    for (const owner of owners) assert.throws(() => controller!.holding(owner), /unavailable/);
    release(); await rejected;
    evidence('activation-failure', { level: 'actual-session-fault-after-enrollment', revoked_before_async_cleanup: true });
  } finally { release(); NativeBirthEnrollment.prototype.activate = activate; LocalBattleEnv.prototype.close = close; NativeBirthEnrollment.prototype.enroll = enroll; }
});

test('B1 close and restore', async () => {
  const observer = NativeBirthEnrollment.prototype.observe, reset = LocalBattleEnv.prototype.resetWithOptions, diagnostics = LocalBattleEnv.prototype.diagnostics;
  let observations = 0, session: PipelineIntegrationSession | undefined, legacy: PipelineIntegrationSession | undefined;
  const donor = new LocalBattleEnv('B1-legacy', options.format, options.seed);
  NativeBirthEnrollment.prototype.observe = function(...args) { observations++; return observer.apply(this, args); };
  try {
    session = await PipelineIntegrationSession.create(options);
    const handles = owners.map(owner => session!.getNativeBirthHolding(owner));
    const rows = owners.map(owner => holding(session!, owner)); const initial = observations;
    const boundary = session.boundary;
    LocalBattleEnv.prototype.diagnostics = function() { const value = diagnostics.call(this); return this.id.includes('step-') ? { ...value, last_error: 'B1-candidate-rejection' } : value; };
    await assert.rejects(session.step(), /rejected-action/);
    assert.equal(session.boundary, boundary);
    for (const [i, owner] of owners.entries()) {
      assert.equal(session.getNativeBirthHolding(owner), handles[i]);
      assert.equal(session.readNativeBirthHolding(handles[i], owner), rows[i]);
    }
    LocalBattleEnv.prototype.diagnostics = diagnostics;
    await session.step(); assert.equal(observations, initial, 'actual candidate restore never calls birth observer');
    for (const [i, owner] of owners.entries()) assert.equal(session.readNativeBirthHolding(handles[i], owner), rows[i]);
    const closing = session.close();
    for (const [i, owner] of owners.entries()) assert.throws(() => session!.readNativeBirthHolding(handles[i], owner), /closed/);
    await closing;
    await donor.reset(); const snapshot = donor.serializeBattle();
    LocalBattleEnv.prototype.resetWithOptions = function(opts) { return this.resetFromSerialized(structuredClone(snapshot), opts); };
    legacy = await PipelineIntegrationSession.create(options);
    for (const owner of owners) assert.throws(() => legacy!.getNativeBirthHolding(owner), /unavailable/);
    await legacy.step();
    for (const owner of owners) assert.throws(() => legacy!.getNativeBirthHolding(owner), /unavailable/);
    evidence('lifetime-restore', { level: 'actual-generated-session-and-legacy-restore', no_restore_observer_calls: true,
      rejected_candidate_preserves_exact_handles_and_rows: true, historical_holding_survives_retirement: true, synchronous_close_denial: true, legacy_birth_unavailable: true,
      restored_object_mapping: 'unsupported B2' });
  } finally { NativeBirthEnrollment.prototype.observe = observer; LocalBattleEnv.prototype.resetWithOptions = reset; LocalBattleEnv.prototype.diagnostics = diagnostics;
    await session?.close(); await legacy?.close(); await donor.close(); }
});
