import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, BattleStream, Side, Teams } from 'pokemon-showdown';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

type Row = Record<string, any>;
const owners = ['p1', 'p2'] as const;
const format = 'gen9randombattle';
const seed = [1, 2, 3, 4];
const options = { battle_id: 'prompt26', format, seed, observation_schema_version: 'observable-battle-state/v2' as const };
const other = (owner: PlayerID): PlayerID => owner === 'p1' ? 'p2' : 'p1';
const env = (session: PipelineIntegrationSession): LocalBattleEnv => (session as any).environment;
const native = (environment: LocalBattleEnv): Battle => (environment as any).battleStream.battle;
const own = (session: PipelineIntegrationSession, owner: PlayerID) => session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner);
const history = (session: PipelineIntegrationSession, owner: PlayerID) => session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner);
const witness = (id: string, level: string, value: Row) => console.log('P26_WITNESS ' + JSON.stringify({ id, level, ...value }));

interface Birth { owner: PlayerID; submitted: string; sets: any[]; before: any[]; sideAbsent: boolean; started: boolean }
interface ActorEvent { command: string; actor: any; token: string; first: number; end: number }
interface Indexed { internal: number; public: number; normalized: number | null; record: string }

// Test-owned references and positional routing oracle. No production capability is created.
class Probe {
  births: Birth[] = [];
  events: ActorEvent[] = [];
  indexed: Indexed[] = [];
  requests: Array<{ owner: PlayerID; json: string; objects: any[]; order: number[]; active: string[] }> = [];
  timeline: string[] = ['installed-after-start'];
  private restore: (() => void)[] = [];
  private submitting: PlayerID | null = null;
  private adding = false;
  constructor(readonly battle: Battle, readonly mode: 'birth' | 'restored') {
    const b = battle as any;
    const tap = (key: string, wrap: (original: any) => any) => {
      const descriptor = Object.getOwnPropertyDescriptor(b, key), original = b[key];
      b[key] = wrap(original);
      this.restore.push(() => descriptor ? Object.defineProperty(b, key, descriptor) : delete b[key]);
    };
    if (mode === 'birth') {
      assert.ok(!battle.started && battle.sides.every(side => !side));
      tap('setPlayer', original => (owner: PlayerID, input: Row) => {
        this.timeline.push('player:' + owner); this.submitting = owner;
        try { return original.call(battle, owner, input); } finally { this.submitting = null; }
      });
      tap('getTeam', original => (input: Row) => {
        assert.ok(this.submitting); const owner = this.submitting!;
        const sets = original.call(battle, input);
        this.births.push({ owner, submitted: input.team, sets: [...sets], before: structuredClone(sets),
          sideAbsent: !battle.sides[owner === 'p1' ? 0 : 1], started: battle.started });
        this.timeline.push('unpacked:' + owner); return sets;
      });
    }
    tap('add', original => (...parts: any[]) => {
      const command = String(parts[0]);
      const actor = ['switch', 'drag', 'replace', '-transform'].includes(command) ? parts[1] : null;
      const event = !this.adding && actor?.set ? { command, actor, token: this.token(actor), first: battle.log.length, end: -1 } : null;
      // Capture the actor before join()/visibility callbacks in Battle.add.
      const nested = this.adding; this.adding = true;
      try {
        const value = original.apply(battle, parts);
        if (event) { event.end = battle.log.length; this.events.push(event); }
        return value;
      } finally { this.adding = nested; }
    });
    tap('sendUpdates', original => () => {
      const start = battle.sentLogPos, end = battle.log.length;
      const selected: Array<{ internal: number; record: string }> = [];
      // Independent pinned spectator oracle: split marker + secret + shared.
      for (let i = start; i < end; i++) {
        if (battle.log[i].startsWith('|split|')) {
          assert.ok(i + 2 < end); i += 2;
          if (battle.log[i]) selected.push({ internal: i, record: battle.log[i] });
        } else if (battle.log[i]) selected.push({ internal: i, record: battle.log[i] });
      }
      for (const row of selected) {
        const publicIndex = this.indexed.length;
        const projected = projectPipelineProtocolPrefix([row.record]);
        this.indexed.push({ ...row, public: publicIndex,
          normalized: projected.length ? this.indexed.filter(x => x.normalized !== null).length : null });
      }
      return original.call(battle);
    });
  }
  token(pokemon: any): string {
    const owner = pokemon.side.id as PlayerID;
    const sets = this.mode === 'birth' ? this.births.find(x => x.owner === owner)?.sets : pokemon.side.team;
    const index = sets?.indexOf(pokemon.set) ?? -1;
    assert.ok(index >= 0, 'exact held set reference required');
    return owner + ':slot:' + (index + 1);
  }
  order(owner: PlayerID): number[] {
    return this.battle[owner]!.pokemon.map(pokemon => Number(this.token(pokemon).split(':').at(-1)));
  }
  mappedEvents() {
    return this.events.map(event => ({ command: event.command, token: event.token,
      first_internal: event.first, end_internal: event.end,
      rows: this.indexed.filter(row => row.internal >= event.first && row.internal < event.end) }));
  }
  close() { for (const restore of this.restore.reverse()) restore(); }
}

async function taps<T>(body: (probes: Probe[]) => Promise<T>): Promise<T> {
  const prototype = BattleStream.prototype as any, write = prototype._writeLine;
  const fromJSON = Battle.fromJSON, probes: Probe[] = [];
  const emit = Side.prototype.emitRequest;
  Side.prototype.emitRequest = function(update) {
    const probe = probes.find(p => p.battle === this.battle);
    if (probe) probe.requests.push({ owner: this.id as PlayerID, json: JSON.stringify(update), objects: [...this.pokemon],
      order: probe.order(this.id as PlayerID), active: this.active.filter(Boolean).map(p => probe.token(p)) });
    return emit.call(this, update);
  };
  prototype._writeLine = function(type: string, message: string) {
    const value = write.call(this, type, message);
    if (type === 'start') probes.push(new Probe(this.battle, 'birth'));
    return value;
  };
  Battle.fromJSON = function(...args: Parameters<typeof fromJSON>) {
    const battle = fromJSON.apply(this, args); probes.push(new Probe(battle, 'restored')); return battle;
  };
  try { return await body(probes); }
  finally { prototype._writeLine = write; Battle.fromJSON = fromJSON; Side.prototype.emitRequest = emit; for (const probe of probes) probe.close(); }
}

async function lower(ownText: string, foeText: string, owner: PlayerID, body: (probe: Probe, stream: BattleStream, raw: any[]) => Promise<void>) {
  return taps(async probes => {
    const stream = new BattleStream({ keepAlive: true });
    const raw = Teams.import(ownText)!;
    const teams = { [owner]: Teams.pack(structuredClone(raw)), [other(owner)]: Teams.pack(Teams.import(foeText)) };
    try {
      await stream.write(['>start ' + JSON.stringify({ formatid: format, seed }),
        ...owners.map(p => '>player ' + p + ' ' + JSON.stringify({ name: p, team: teams[p] }))].join('\n'));
      await body(probes[0], stream, structuredClone(raw));
    } finally { stream.destroy(); }
  });
}

function assertBirth(probe: Probe, owner: PlayerID) {
  const birth = probe.births.find(x => x.owner === owner)!;
  assert.ok(birth.sideAbsent && !birth.started);
  const side = probe.battle[owner]!;
  for (const [i, set] of birth.sets.entries()) {
    assert.equal(side.team[i], set);
    assert.equal(side.pokemon.find(p => p.set === set)!.set, set);
  }
}

function assertCommittedIndices(probe: Probe, session: PipelineIntegrationSession) {
  const publicRows = probe.indexed.map(row => row.record);
  assert.deepEqual((env(session) as any).logLines, publicRows, 'actual spectator positional ledger');
  const projected = projectPipelineProtocolPrefix(publicRows);
  for (const owner of owners) {
    assert.deepEqual(session.boundary.perspectives[owner].observation.protocol_prefix, projected);
    assert.deepEqual(history(session, owner).boundaries.at(-1)!.prefix, projected);
  }
  for (const event of probe.mappedEvents()) {
    assert.equal(event.rows.length, 1, 'split private row must not enter spectator event');
    assert.equal(event.rows[0].record.split('|')[1], event.command);
    assert.equal(projected[event.rows[0].normalized!], event.rows[0].record);
  }
}

test('P26 generated birth timing', async () => taps(async probes => {
  let session: PipelineIntegrationSession | undefined;
  const reset = LocalBattleEnv.prototype.resetWithOptions; const staged: Row = {};
  LocalBattleEnv.prototype.resetWithOptions = async function(...args) {
    const result = await reset.apply(this, args);
    for (const owner of owners) staged[owner] = this.inspectStagedOriginalOwner(owner);
    return result;
  };
  try {
    session = await PipelineIntegrationSession.create(options);
    const probe = probes.find(p => p.battle === native(env(session!)))!;
    assert.deepEqual(probe.timeline, ['installed-after-start', 'player:p1', 'unpacked:p1', 'player:p2', 'unpacked:p2']);
    for (const owner of owners) {
      assertBirth(probe, owner); const birth = probe.births.find(x => x.owner === owner)!;
      const held = own(session, owner);
      assert.equal(held, staged[owner]); assert.equal(birth.submitted, held.packed_team);
      assert.equal(birth.sets.length, 6); assert.equal(held.raw_team.length, 6);
      // Order comparison corroborates actual owner submission; reference enrollment is supplied by the tapped call path.
      assert.deepEqual(birth.before.map(set => set.moves), Teams.unpack(held.packed_team)!.map(set => set.moves));
      assert.deepEqual(probe.order(owner), [1, 2, 3, 4, 5, 6]);
      assert.deepEqual(probe.battle[owner]!.getRequestData().pokemon, (probe.battle[owner]!.activeRequest as any).side.pokemon);
      assert.ok(Object.isFrozen(held.raw_team));
      const emitted = probe.requests.filter(row => row.owner === owner);
      const receipts = env(session).inspectRequestEmissionTrace(env(session).getRequestEmissionTraceHandle(owner), owner);
      assert.deepEqual(emitted.map(row => row.json), receipts.map(row => row.request_json));
      assert.deepEqual(emitted[0].order, [1, 2, 3, 4, 5, 6]);
      assert.ok(emitted[0].objects.every((p, i) => p.set === birth.sets[i]));
    }
    assertCommittedIndices(probe, session);
    witness('birth', 'actual-generated-session', { timeline: probe.timeline, owners: owners.map(owner => ({ owner,
      retained_count: own(session!, owner).raw_team.length, object_order: probe.order(owner),
      set_references_captured_before_construction: true, request_emission_order: probe.requests.filter(r => r.owner === owner).map(r => r.order) })), events: probe.mappedEvents(), authority: 'test-only' });
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; await session?.close(); }
}));

test('P26 initial effects', async () => {
  const controls = [
    { label: 'Trace', own: 'Alakazam\nAbility: Trace\n- Splash', species: 'Alakazam', ability: 'naturalcure', move: 'splash' },
    { label: 'Imposter', own: 'Ditto\nAbility: Imposter\n- Transform', species: 'Blissey', ability: 'naturalcure', move: 'softboiled' },
    { label: 'Schooling', own: 'Wishiwashi\nAbility: Schooling\nLevel: 100\n- Splash', species: 'Wishiwashi-School', ability: 'schooling', move: 'splash' },
    { label: 'Crowned', own: 'Zacian @ Rusted Sword\nAbility: Intrepid Sword\n- Iron Head', species: 'Zacian-Crowned', ability: 'intrepidsword', move: 'behemothblade' },
  ];
  for (const owner of owners) for (const control of controls) {
    await lower(control.own, 'Blissey\nAbility: Natural Cure\n- Soft-Boiled', owner, async probe => {
      assertBirth(probe, owner); const pokemon = probe.battle[owner]!.active[0];
      assert.equal(pokemon.species.name, control.species); assert.equal(pokemon.ability, control.ability);
      assert.equal((probe.battle[owner]!.activeRequest as any).active[0].moves[0].id, control.move);
      assert.equal(probe.token(pokemon), owner + ':slot:1');
      const birth = probe.births.find(x => x.owner === owner)!;
      assert.notEqual(birth.sets[0], birth.before[0]);
      witness('initial-' + control.label + '-' + owner, 'constructed-native-mechanic', { owner,
        pre_constructor_species: birth.before[0].species, pre_constructor_moves: birth.before[0].moves,
        current_species: pokemon.species.name, current_move: control.move, token: probe.token(pokemon),
        events: probe.mappedEvents(), generated_reachability: 'not-proved' });
    });
    await taps(async probes => {
      const generate = Teams.generate; let count = 0, session: PipelineIntegrationSession | undefined, rejection: string | null = null;
      Teams.generate = function() {
        const p = owners[count++];
        return Teams.import(p === owner ? control.own : 'Blissey\nAbility: Natural Cure\n- Soft-Boiled')!;
      };
      try {
        try { session = await PipelineIntegrationSession.create(options); }
        catch (error) {
          rejection = (error as Error).message;
          assert.match(rejection, /Public health evidence mismatch|unsupported-observable-protocol|unsupported-protocol-record/);
        }
        if (session) {
          const probe = probes.find(p => p.battle === native(env(session!)))!;
          assertBirth(probe, owner);
          assert.equal(probe.battle[owner]!.active[0].species.name, control.species);
          assert.deepEqual((own(session, owner).raw_team[0] as Row).moves, Teams.import(control.own)![0].moves);
          assertCommittedIndices(probe, session);
        }
        witness('initial-integration-' + control.label + '-' + owner, session ? 'actual-session-constructed-input' : 'actual-session-validator-rejection', {
          owner, control: control.label, accepted: !!session, rejection, generated_reachability: 'not-proved' });
      } finally { Teams.generate = generate; await session?.close(); }
    });
  }
});

test('P26 duplicates switch drag reentry', async () => {
  for (const owner of owners) {
    await lower('Same (Snorlax)\nAbility: Immunity\n- Splash\n\nSame (Snorlax)\nAbility: Thick Fat\n- Splash',
      'Target (Blissey)\nAbility: Natural Cure\n- Splash\n- Roar', owner, async (probe, stream) => {
        const side = probe.battle[owner]!, first = side.active[0], second = side.pokemon[1];
        const idents = (side.activeRequest as any).side.pokemon.map((p: Row) => p.ident); assert.equal(idents[0], idents[1]);
        const orders = [probe.order(owner)];
        await stream.write(`>${owner} switch 2\n>${other(owner)} move 1`); orders.push(probe.order(owner)); assert.equal(side.active[0], second);
        await stream.write(`>${owner} switch 2\n>${other(owner)} move 1`); orders.push(probe.order(owner)); assert.equal(side.active[0], first);
        await stream.write(`>${owner} move 1\n>${other(owner)} move 2`); orders.push(probe.order(owner)); assert.equal(side.active[0], second);
        assert.deepEqual(orders, [[1, 2], [2, 1], [1, 2], [2, 1]]);
        assert.ok(probe.events.some(e => e.command === 'drag' && e.actor === second && e.token === owner + ':slot:2'));
        witness('duplicate-order-' + owner, 'constructed-native-mechanic', { owner, equal_idents: idents,
          orders, events: probe.mappedEvents(), association_basis: 'held unpacked set references, never ident/position' });
      });
  }
  const generate = Teams.generate; let session: PipelineIntegrationSession | undefined;
  Teams.generate = function() { return Teams.import('Same (Snorlax)\nAbility: Immunity\n- Splash\n\nSame (Snorlax)\nAbility: Thick Fat\n- Splash')!; };
  try {
    await assert.rejects(async () => { session = await PipelineIntegrationSession.create(options); }, /Public health evidence mismatch: p1: Same requires exactly one self_team row/);
    witness('duplicate-integration', 'actual-session-validator-rejection', { rejection: 'p1: Same requires exactly one self_team row', integration: 'unproved; validator preserved' });
  } finally { Teams.generate = generate; await session?.close(); }
});

test('P26 Illusion Transform', async () => {
  for (const owner of owners) {
    await lower('Fox (Zoroark)\nAbility: Illusion\n- Splash\n\nMask (Pikachu)\nAbility: Static\n- Splash',
      'Target (Snorlax)\nAbility: Immunity\n- Tackle', owner, async (probe, stream) => {
        const side = probe.battle[owner]!, actor = side.active[0]; const before = probe.token(actor);
        assert.ok(probe.battle.log.some(line => line.startsWith(`|switch|${owner}a: Mask|Pikachu`)));
        await stream.write(`>${owner} move 1\n>${other(owner)} move 1`);
        assert.equal(side.active[0], actor); assert.equal(probe.token(actor), before);
        const replace = probe.events.find(e => e.command === 'replace' && e.actor === actor)!; assert.ok(replace);
        assert.equal(replace.token, owner + ':slot:1');
        witness('illusion-' + owner, 'constructed-native-mechanic', { owner, same_stint_actor: true, token: before,
          events: probe.mappedEvents(), appearance_rule: 'replace discloses same actor, no new birth' });
      });
    await lower('Copy (Ditto)\nAbility: Limber\n- Transform\n\nBench (Snorlax)\nAbility: Immunity\n- Splash',
      'Target (Blissey)\nAbility: Natural Cure\n- Soft-Boiled', owner, async (probe, stream) => {
        const side = probe.battle[owner]!, actor = side.active[0];
        const birth = probe.births.find(row => row.owner === owner)!;
        const actualSet = actor.set, startingMoves = [...actualSet.moves];
        assert.equal(actualSet, birth.sets[0]);
        assert.deepEqual(birth.before[0].moves, ['Transform']);
        await stream.write(`>${owner} move 1\n>${other(owner)} move 1`);
        assert.equal(side.active[0], actor); assert.equal(probe.token(actor), owner + ':slot:1');
        assert.equal(actor.transformed, true); assert.equal(actor.moveSlots[0].id, 'softboiled');
        await stream.write(`>${owner} switch 2\n>${other(owner)} move 1`);
        await stream.write(`>${owner} switch 2\n>${other(owner)} move 1`);
        assert.equal(side.active[0], actor); assert.equal(actor.transformed, false); assert.equal(actor.moveSlots[0].id, 'transform');
        assert.equal(actor.set, actualSet); assert.deepEqual(actualSet.moves, startingMoves);
        assert.deepEqual(birth.before[0].moves, ['Transform']);
        witness('transform-' + owner, 'constructed-native-mechanic', { owner, object_continuity: true,
          captured_birth_moves: birth.before[0].moves, actual_set_moves: actualSet.moves, actual_set_reference_preserved: true, reentry_moves: actor.moveSlots.map(m => m.id), events: probe.mappedEvents() });
      });
  }
});

test('P26 indexed events', async () => taps(async probes => {
  let session: PipelineIntegrationSession | undefined;
  try {
    session = await PipelineIntegrationSession.create(options);
    const probe = probes.find(p => p.battle === native(env(session!)))!;
    assertCommittedIndices(probe, session);
    // Labeled direct native writers: the eval command emits unsupported diagnostic framing.
    probe.battle.add('message', 'equal'); probe.battle.add('message', 'equal'); probe.battle.add('');
    probe.battle.add('tier', 'Gen 9 Random Battle'); probe.battle.add('t:', 123);
    probe.battle.sendUpdates();
    await env(session).stepWithOptions({}, { include_log_delta: true, include_wait_requests: true });
    const publicRows = probe.indexed.map(row => row.record);
    assert.deepEqual((env(session) as any).logLines, publicRows);
    const equal = probe.indexed.filter(row => row.record === '|message|equal');
    assert.equal(equal.length, 2); assert.notEqual(equal[0].internal, equal[1].internal);
    assert.notEqual(equal[0].public, equal[1].public); assert.notEqual(equal[0].normalized, equal[1].normalized);
    assert.ok(probe.indexed.some(row => row.record === '|' && row.normalized === null));
    assert.deepEqual(projectPipelineProtocolPrefix(['|']), []);
    assert.throws(() => projectPipelineProtocolPrefix(['||>>> diagnostic']), /Unsupported raw protocol event: <empty>/); 
    assert.ok(probe.indexed.some(row => row.record.startsWith('|tier|') && row.normalized === null));
    const timestamp = probe.indexed.find(row => row.record === '|t:|123')!;
    assert.equal(projectPipelineProtocolPrefix(publicRows)[timestamp.normalized!], '|t:|0');
    const openings = probe.mappedEvents().filter(e => e.command === 'switch'); assert.equal(openings.length, 2);
    assert.deepEqual(openings.map(e => [e.token, e.first_internal, e.end_internal, e.rows[0].public, e.rows[0].normalized]),
      [['p1:slot:1', 15, 18, 15, 13], ['p2:slot:1', 18, 21, 16, 14]]);
    for (const event of openings) {
      assert.equal(event.end_internal - event.first_internal, 3); assert.equal(event.rows.length, 1);
      assert.equal(event.rows[0].internal, event.first_internal + 2);
    }
    witness('indexed', 'actual-generated-initial-commit-plus-synthetic-writers', { committed_initial_events: openings,
      duplicate_occurrences: equal, filtered: probe.indexed.filter(row => row.normalized === null),
      timestamp, bare_pipe_framing: 'admitted and filtered', eval_diagnostic: 'actual projector rejection; not admissible public evidence', synthetic_suffix_committed: false, missing: 'no adopted runtime event/source index sidecar' });
  } finally { await session?.close(); }
}));

// Explicit model for future held-parent association gates. Passing this model is never a production rejection proof.
function modelJoin(input: { owner: PlayerID; held: object; expectedHeld: object; parent: object; expectedParent: object;
  packed: string; expectedPacked: string; prefix: readonly string[]; expectedPrefix: readonly string[];
  births: Array<{ owner: PlayerID; token: object }>; expectedBirth: object; observedAt: number; cursor: number }) {
  assert.equal(input.held, input.expectedHeld, 'held originals'); assert.equal(input.parent, input.expectedParent, 'held parent');
  assert.equal(input.packed, input.expectedPacked, 'submitted association'); assert.deepEqual(input.prefix, input.expectedPrefix, 'exact causal prefix');
  assert.equal(input.births.length, 1, 'one birth'); assert.equal(input.births[0].owner, input.owner, 'addressed owner');
  assert.equal(input.births[0].token, input.expectedBirth, 'held birth'); assert.ok(input.observedAt <= input.cursor, 'causal availability');
}

test('P26 model negatives', () => {
  const held = {}, parent = {}, birth = {}, prefix = ['|message|A'];
  const good = { owner: 'p1' as PlayerID, held, expectedHeld: held, parent, expectedParent: parent,
    packed: 'held submission', expectedPacked: 'held submission', prefix, expectedPrefix: prefix,
    births: [{ owner: 'p1' as PlayerID, token: birth }], expectedBirth: birth, observedAt: 1, cursor: 1 };
  modelJoin(good);
  const failures: Array<[string, Row, RegExp]> = [
    ['missing', { births: [] }, /one birth/], ['duplicate', { births: [good.births[0], good.births[0]] }, /one birth/],
    ['misrouted', { births: [{ owner: 'p2', token: birth }] }, /addressed owner/],
    ['removed-held-originals', { held: {} }, /held originals/], ['foreign-parent', { parent: {} }, /held parent/], ['sibling-parent', { parent: { ...parent } }, /held parent/],
    ['changed-packed', { packed: 'foreign submission' }, /submitted association/],
    ['equal-length-foreign-prefix', { prefix: ['|message|B'] }, /exact causal prefix/],
    ['late-event', { observedAt: 2 }, /causal availability/], ['copied-birth', { births: [{ owner: 'p1', token: { ...birth } }] }, /held birth/],
  ];
  for (const [, delta, pattern] of failures) assert.throws(() => modelJoin({ ...good, ...delta }), pattern);
  witness('model-negatives', 'future-gate-test-model-only', { rejections: failures.map(([name]) => name), production_rejections: 'not-implemented' });
});

test('P26 restore continuity', async () => taps(async probes => {
  let session: PipelineIntegrationSession | undefined, foreign: PipelineIntegrationSession | undefined;
  const bare = new LocalBattleEnv('prompt26-bare', format, seed);
  let uninterrupted: Battle | undefined;
  try {
    session = await PipelineIntegrationSession.create(options); foreign = await PipelineIntegrationSession.create(options);
    const original = Object.fromEntries(owners.map(owner => [owner, own(session!, owner)]));
    const originalBattle = native(env(session)); const oldObjects: Record<PlayerID, any[]> = { p1: originalBattle.p1!.pokemon.slice(), p2: originalBattle.p2!.pokemon.slice() };
    const oldParent = history(session, 'p1').boundaries.at(-1)!;
    const snapshot = env(session).serializeBattle() as Row;
    // Separately started generated-input native control: it continues without serialize/restore.
    uninterrupted = new Battle({ formatid: format, seed: '1,2,3,4' });
    uninterrupted.setPlayer('p1', { name: 'Agent-1', team: original.p1.packed_team });
    uninterrupted.setPlayer('p2', { name: 'Agent-2', team: original.p2.packed_team });
    const result = await session.step(); const continued = native(env(session));
    const commandLines = (continued.toJSON() as Row).inputLog.slice(snapshot.inputLog.length);
    const commands = commandLines.filter((line: string) => /^>p[12] /.test(line)); assert.equal(commands.length, 2);
    await (uninterrupted as any).choose('p1', commands.find((line: string) => line.startsWith('>p1 ')).slice(4));
    await (uninterrupted as any).choose('p2', commands.find((line: string) => line.startsWith('>p2 ')).slice(4));
    for (const owner of owners) {
      assert.equal(own(session, owner), original[owner]);
      const side: Side = continued[owner]!;
      const control: Side = uninterrupted[owner]!;
      assert.deepEqual(side.pokemon.map(p => side.team.indexOf(p.set) + 1), control.pokemon.map(p => control.team.indexOf(p.set) + 1));
      assert.deepEqual(side.activeRequest, control.activeRequest);
    }
    for (const owner of owners) assert.ok(continued[owner]!.pokemon.every(p => !oldObjects[owner].includes(p)),
      'all reconstructed native object references are fresh for both owners');
    assert.equal(probes.find(p => p.battle === continued)!.mode, 'restored');
    const handle = session.getRequestDeliveryHandle('p1');
    assert.equal(history(session, 'p1').boundaries[0], oldParent);
    assert.throws(() => session!.readRequestDeliveryHistory(handle, 'p1', { ...oldParent }), /foreign-boundary/);
    assert.throws(() => session!.readRequestDeliveryHistory(handle, 'p1', history(foreign!, 'p1').boundaries[0]), /foreign-boundary/);
    await bare.resetFromSerialized(structuredClone(snapshot), { include_wait_requests: true });
    assert.throws(() => bare.inspectStagedOriginalOwner('p1'), /no-creation/);
    witness('restore', 'actual-generated-session-plus-uninterrupted-native-control', { committed_step: result.boundary.step_index,
      all_both_owner_objects_fresh: true, reconstruction_callbacks: 'unobserved: tap installed after fromJSON', held_originals_same_reference: true,
      order: owners.map(owner => ({ owner, slots: continued[owner]!.pokemon.map(p => continued[owner]!.team.indexOf(p.set) + 1) })),
      copied_parent: 'existing-ledger-rejection', same_label_foreign_parent: 'existing-ledger-rejection',
      bare_snapshot: 'usable native state; no originals', missing: 'trusted original-slot↔restored-object capability and event replay sidecar' });
  } finally { uninterrupted?.destroy(); await bare.close(); await session?.close(); await foreign?.close(); }
}));

test('P26 rejection terminal cleanup', async () => taps(async () => {
  let session: PipelineIntegrationSession | undefined;
  const diagnostics = LocalBattleEnv.prototype.diagnostics;
  try {
    session = await PipelineIntegrationSession.create(options);
    const held = own(session, 'p1'), handle = session.getOriginalOwnerHolding('p1');
    const before = { p1: history(session, 'p1'), p2: history(session, 'p2') }, boundary = session.boundary;
    LocalBattleEnv.prototype.diagnostics = function() { const value = diagnostics.call(this); return this.id.includes('step-') ? { ...value, last_error: 'prompt26 test fault' } : value; };
    await assert.rejects(session.step(), /rejected-action/);
    assert.equal(session.boundary, boundary);
    for (const owner of owners) assert.equal(history(session, owner), before[owner]);
    assert.equal(own(session, 'p1'), held);
    LocalBattleEnv.prototype.diagnostics = diagnostics;
    await session.step();
    const current = env(session), battle = native(current);
    battle.win('p1'); battle.sendUpdates();
    const terminal = await current.stepWithOptions({}, { include_wait_requests: true });
    assert.equal(terminal.requests.p1, null); assert.equal(terminal.requests.p2, null);
    assert.ok(battle.ended);
    const deliveryHandle = session.getRequestDeliveryHandle('p1');
    const closing = session.close();
    assert.throws(() => session!.readOriginalOwnerHolding(handle, 'p1'), /foreign-or-forged-holding/);
    assert.throws(() => session!.readRequestDeliveryHistory(deliveryHandle, 'p1'), /closed/);
    await closing;
    witness('rollback-close', 'actual-generated-session-with-test-fault-and-native-terminal-stimulus', {
      parent_histories_preserved: true, valid_continuation: true, terminal_requests: [null, null], synchronous_close_revocation: true,
      terminal_session_commit: 'not-proved; direct native terminal stimulus only' });
  } finally { LocalBattleEnv.prototype.diagnostics = diagnostics; await session?.close(); }
}));
