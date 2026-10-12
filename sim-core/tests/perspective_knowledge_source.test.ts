import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { canonicalKnowledgeJson, checkKnowledgeStructure, knowledgeIdentity } from '../src/perspective_knowledge';
import * as sourceModule from '../src/perspective_knowledge_source';
import {
  KnowledgeSourceError, LegacyContext, LegacyContextBuilder, SourceRegistry, SourceRegistryBuilder,
  checkKnowledgeSourceBinding, legacyDataRecordId, type LegacyEnvelopeAdapter,
} from '../src/perspective_knowledge_source';

type Row = Record<string, any>;
const root = path.resolve(__dirname, '../../..');
const fixtures = path.join(root, 'docs/contracts/fixtures/perspective-knowledge-v1');
const load = (name: string): any => JSON.parse(readFileSync(path.join(fixtures, name), 'utf8'));
// Test-owned witness: real pinned BattleStream harness + real PipelineIntegrationSession (see script header).
// eslint-disable-next-line @typescript-eslint/no-var-requires
const witnessModule = require(path.join(root, 'docs/planning/perspective-fidelity-prompt12-witness.cjs'));
const FORMS = ['ordinary', 'full', 'compact'] as const;
const VERSIONS = ['observable-battle-state/v1', 'observable-battle-state/v2'] as const;
const OWNERS = ['p1', 'p2'];

// ---- independent literal oracle (same approach as perspective_knowledge.test.ts) ----
function literalCanonical(value: any): string {
  if (Array.isArray(value)) return '[' + value.map(literalCanonical).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + literalCanonical(value[k])).join(',') + '}';
  }
  return JSON.stringify(value);
}
function literalIdentity(row: Row): string {
  const payload = Object.fromEntries(Object.entries(row).filter(([key]) => key !== 'id'));
  return 'sha256:' + createHash('sha256').update('pk/v1/' + row.kind + '\n' + literalCanonical(payload), 'utf8').digest('hex');
}
function tables(audit: Row): Record<string, Row[]> {
  return Object.fromEntries(Object.entries(audit.tables).map(([kind, rows]) => [kind,
    (Array.isArray(rows) ? rows : Object.values(rows as Row)).slice().sort((a: Row, b: Row) => a.id.localeCompare(b.id)),
  ]));
}
const singleEdges: Record<string, string[]> = {
  origin: [], source: ['origin'], prefix: ['origin'], evidence: ['origin', 'source', 'prefix'],
  certificate: ['source'], fact: ['certificate'], starting: ['origin', 'source', 'parent'],
  current: ['origin', 'prefix', 'parent'], request: ['origin', 'source', 'prefix'],
  knowledge: ['origin', 'starting', 'current', 'request'], profile: [],
  verdict: ['knowledge', 'profile'], boundary: ['origin', 'parent', 'restored_from'],
  binding: ['origin', 'input_knowledge', 'successor_knowledge'],
};
const listEdges: Record<string, string[]> = { certificate: ['witnesses'], fact: ['evidence'], starting: ['facts'], current: ['facts'], request: ['facts'] };
function reseal(audit: Row): Row {
  const expanded = tables(audit);
  const byOldId = new Map<string, Row>();
  for (const rows of Object.values(expanded)) for (const row of rows) byOldId.set(row.id, row);
  const completed = new Map<string, string>();
  function replace(id: string | null): string | null {
    if (id === null || !byOldId.has(id)) return id;
    if (completed.has(id)) return completed.get(id)!;
    const row = byOldId.get(id)!;
    for (const field of singleEdges[row.kind]) row[field] = replace(row[field]);
    for (const field of listEdges[row.kind] ?? []) row[field] = row[field].map(replace).sort();
    if (row.kind === 'starting') for (const crosswalk of row.crosswalk) crosswalk.certificate = replace(crosswalk.certificate);
    if (row.kind === 'boundary') for (const binding of row.bindings) { binding.knowledge = replace(binding.knowledge); binding.verdict = replace(binding.verdict); }
    row.id = literalIdentity(row);
    completed.set(id, row.id);
    return row.id;
  }
  for (const id of byOldId.keys()) replace(id);
  for (const field of ['origin', 'required_profile', 'target_boundary']) audit[field] = replace(audit[field]);
  audit.tables = Object.fromEntries(Object.entries(expanded).map(([kind, rows]) => [kind,
    audit.form === 'compact' ? Object.fromEntries(rows.sort((a, b) => a.id.localeCompare(b.id)).map(row => [row.id, row])) : rows.sort((a, b) => a.id.localeCompare(b.id)),
  ]));
  audit.id = literalIdentity(audit);
  return audit;
}
/** Deep-copies the audit, applies an in-place mutation to its rows and reseals every identity. */
function mutated(audit: Row, change: (rows: Record<string, Row[]>) => void): Row {
  const copy = structuredClone(audit);
  change(tables(copy));
  return reseal(copy);
}

// ---- trusted local creation owner helpers ----
interface Witness { version: string; battle_id: string; origin: Row; team_sets: Row; ledger: string[]; requests: Row; bundles: Row; python_record_ids: Row; cursors: number[]; audits: Row; nonactor_audit: Row; sourceless_audit: Row; }
const witnesses: Promise<Record<string, Witness>> = (async () => {
  const result: Record<string, Witness> = {};
  for (const version of VERSIONS) {
    const w = await witnessModule.capture(version);
    w.audits = Object.fromEntries(FORMS.map(form => [form, witnessModule.buildAudit(w, form)]));
    w.nonactor_audit = witnessModule.buildAudit(w, 'ordinary', { nonactor: ['p2'] });
    w.sourceless_audit = witnessModule.buildAudit(w, 'ordinary', { sourceless: true });
    result[version] = w;
  }
  return result;
})();

interface RegistryOptions { omitInitialization?: string[]; omitRequests?: string[]; cursorShift?: Record<string, number>; ledger?: string[] | null; origin?: Row | null; replay?: string[] }
function makeRegistry(w: Witness, options: RegistryOptions = {}): SourceRegistry {
  const builder = new SourceRegistryBuilder();
  if (options.origin !== null) builder.setOrigin(options.origin ?? w.origin);
  const ledger = options.ledger === undefined ? w.ledger : options.ledger;
  for (const owner of OWNERS) {
    if (!options.omitInitialization?.includes(owner)) builder.addInitializationWitness(owner, w.team_sets[owner]);
    for (const r of w.requests[owner]) {
      if (options.omitRequests?.includes(`${owner}:${r.sequence}`)) continue;
      if (ledger !== null && r.cursor > ledger.length) continue;
      builder.addRequestDelivery(owner, r.sequence, r.cursor + (options.cursorShift?.[`${owner}:${r.sequence}`] ?? 0), r.json);
    }
  }
  if (ledger !== null) builder.setPublicLedger(ledger);
  if (options.replay) builder.setReplaySource(options.replay);
  return builder.freeze();
}
function makeLegacy(w: Witness, nonactor: string[] = [], extra: LegacyEnvelopeAdapter[] = []): LegacyContext {
  const builder = new LegacyContextBuilder(extra);
  for (const owner of OWNERS) {
    if (nonactor.includes(owner)) {
      const b = w.bundles[owner];
      builder.addNonactorEvidence({ owner, input: { observation: b.input_observation, belief: b.input_belief }, successor: { observation: b.successor_observation, belief: b.successor_belief } });
    } else builder.addEnvelope(w.bundles[owner]);
  }
  return builder.freeze();
}
const profileOf = (audit: Row): string => audit.required_profile;
function code(run: () => unknown): string {
  try { run(); } catch (error) {
    assert.ok(error instanceof KnowledgeSourceError, 'rejections are typed payload-independent errors');
    assert.equal(error.message, error.code);
    return error.code;
  }
  return assert.fail('expected rejection');
}
const sourceRow = (rows: Record<string, Row[]>, type: string, owner: string | null, seq?: number): Row =>
  rows.source.find(s => s.source_type === type && s.owner === owner && (seq === undefined || s.delivery_seq === seq))!;

// ======================================================================= witness
test('witness: independent harness ledger/cursors equal legacy observations; python IDs are native', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version];
    assert.deepEqual(w.cursors.length, 2);
    for (const owner of OWNERS) {
      const bundle = w.bundles[owner];
      assert.equal(bundle.input_observation.event_cursor, w.requests[owner][0].cursor);
      assert.equal(bundle.successor_observation.event_cursor, w.requests[owner][1].cursor);
      assert.deepEqual(bundle.successor_observation.protocol_prefix, w.ledger.slice(0, w.requests[owner][1].cursor));
      assert.match(w.python_record_ids[owner], /^datarec-[0-9a-f]{64}$/);
      assert.equal(JSON.parse(w.requests[owner][1].json).side.id, owner, 'raw addressed request stays owner-specific');
    }
    assert.notDeepEqual(w.team_sets.p1, w.team_sets.p2);
    assert.equal(w.bundles.p1.transition.transition_id, w.bundles.p2.transition.transition_id);
  }
});

// ============================================================ positives, all forms
test('actual source and legacy positives: both schemas, both owners, ordinary/full/compact, structure first', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
    assert.deepEqual(registry.availability, { origin: true, initialization_witness_owners: ['p1', 'p2'], original_provider: 'not_adopted', request_deliveries: 4, public_ledger: true, replay_source: false });
    assert.deepEqual(legacy.availability, { pairs: 2, nonactor_pairs: 0, envelope_kinds: ['pipeline-linked-record/v1'] });
    for (const form of FORMS) {
      const audit = w.audits[form];
      const before = literalCanonical(audit);
      const result = checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit));
      assert.equal(literalCanonical(audit), before, 'caller audit is not mutated');
      // Expected counts are derived from the independent capture, not from the audit.
      assert.deepEqual(result, {
        structure_valid: true,
        source_verification: { scope: 'declared_source_rows_exact_match', verified: true, sources: 2 + 4 + 2, prefixes: 2, request_deliveries: 4, original_delivery: 'test_only_unverified', replay_source: false },
        legacy_verification: { scope: 'declared_external_positions', verified: true, boundaries: 2, bindings: 2, envelope_kinds: ['pipeline-linked-record/v1'] },
        fact_semantics: 'unverified', original_attribution: 'unverified', obligation_completeness: 'not_established', completeness: 'not_established',
        missing_capabilities: ['original_provider'], unsupported_capabilities: ['original_provider', 'fact_semantics', 'original_attribution', 'family_obligations'], published: false,
      });
      assert.ok(Object.isFrozen(result));
      // Accepted structure alone stays unchanged and still claims nothing about source/legacy.
      assert.deepEqual(checkKnowledgeStructure(audit), { structure_valid: true, source_semantics_verified: false, completeness: 'not_established', legacy_envelope_verified: false });
    }
  }
});

test('nonactor row uses actual validated observation/belief evidence; fabricated DATA and mislabeled actors reject', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w);
    const mixed = makeLegacy(w, ['p2']);
    assert.deepEqual(mixed.availability, { pairs: 2, nonactor_pairs: 1, envelope_kinds: ['nonactor-observation-belief', 'pipeline-linked-record/v1'] });
    const ok = checkKnowledgeSourceBinding(w.nonactor_audit, registry, mixed, profileOf(w.nonactor_audit));
    assert.equal(ok.legacy_verification.verified, true);
    assert.equal(ok.completeness, 'not_established');
    // Audit asserts an actor DATA row for p2 but only nonactor evidence exists: fabricated DATA.
    for (const form of FORMS) assert.equal(code(() => checkKnowledgeSourceBinding(w.audits[form], registry, mixed, profileOf(w.audits[form]))), 'legacy/transition');
    // Audit says nonactor while the context holds a real actor bundle for that pair.
    assert.equal(code(() => checkKnowledgeSourceBinding(w.nonactor_audit, registry, makeLegacy(w), profileOf(w.nonactor_audit))), 'legacy/transition');
  }
});

test('requestless/source-less incomplete canary remains incomplete and names the missing capability', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const audit = w.sourceless_audit;
    for (const registry of [makeRegistry(w), makeRegistry(w, { omitInitialization: OWNERS })]) {
      const result = checkKnowledgeSourceBinding(audit, registry, makeLegacy(w), profileOf(audit));
      assert.equal(result.source_verification.original_delivery, 'absent');
      assert.deepEqual(result.missing_capabilities, ['original_delivery_authority', 'original_provider']);
      assert.equal(result.completeness, 'not_established'); assert.equal(result.original_attribution, 'unverified');
    }
  }
});

test('legacy context may be omitted: source join alone is partial and says so', async () => {
  const w = (await witnesses)[VERSIONS[0]]; const audit = w.audits.full;
  const result = checkKnowledgeSourceBinding(audit, makeRegistry(w), null, profileOf(audit));
  assert.deepEqual(result.legacy_verification, { scope: 'not_checked', verified: false, boundaries: 0, bindings: 0, envelope_kinds: [] });
  assert.deepEqual(result.missing_capabilities, ['legacy_context', 'original_provider']);
  assert.equal(result.source_verification.verified, true);
});

test('false fact values with correct source joins stay fact-semantics-unverified', async () => {
  const w = (await witnesses)[VERSIONS[0]]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
  for (const form of FORMS) {
    const lie = mutated(w.audits[form], rows => { rows.fact.find(f => f.property === 'roster_species' && f.owner === 'p1')!.value.data = 'Missingno'; });
    assert.notEqual(lie.id, w.audits[form].id);
    const result = checkKnowledgeSourceBinding(lie, registry, legacy, profileOf(lie));
    assert.equal(result.fact_semantics, 'unverified'); assert.equal(result.completeness, 'not_established');
    assert.equal(result.source_verification.verified, true, 'source presence is not a certificate of values');
  }
});

// ================================================================ source negatives
test('resealed source negatives reject in every form for both schemas', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
    const cases: [string, string, (rows: Record<string, Row[]>) => void][] = [
      ['source/request-text', 'pretty-printed (normalized) request', rows => { const s = sourceRow(rows, 'owner_request', 'p1', 1); s.raw_request.json = JSON.stringify(JSON.parse(s.raw_request.json), null, 1); }],
      ['source/request-text', 'key-sorted (normalized) request', rows => { const s = sourceRow(rows, 'owner_request', 'p2', 1); const parsed = JSON.parse(s.raw_request.json); s.raw_request.json = JSON.stringify(Object.fromEntries(Object.entries(parsed).reverse())); }],
      ['source/request-text', 'trailing whitespace changes exact text', rows => { sourceRow(rows, 'owner_request', 'p1', 0).raw_request.json += ' '; }],
      ['source/request-text', 'foreign owner request text', rows => {
        const a = sourceRow(rows, 'owner_request', 'p1', 0), b = sourceRow(rows, 'owner_request', 'p2', 0);
        [a.raw_request.json, b.raw_request.json] = [b.raw_request.json, a.raw_request.json];
      }],
      ['source/missing-request-delivery', 'changed delivery sequence', rows => {
        const s = sourceRow(rows, 'owner_request', 'p1', 1); s.delivery_seq = 7;
        rows.request.find(r => r.source === s.id)!.sequence = 7;
      }],
      ['source/original-team', 'altered submitted team', rows => { sourceRow(rows, 'owner_initialization', 'p1').team[0].species = 'Forged'; }],
      ['source/original-team', 'foreign owner team', rows => {
        const a = sourceRow(rows, 'owner_initialization', 'p1'), b = sourceRow(rows, 'owner_initialization', 'p2');
        [a.team, b.team] = [b.team, a.team];
      }],
      ['source/public-prefix', 'wrong public record', rows => {
        const longest = [...rows.prefix].sort((a, b) => b.records.length - a.records.length)[0];
        const source = rows.source.find(s => s.source_type === 'public_prefix' && s.records.length === longest.records.length)!;
        longest.records[longest.records.length - 1] = '|forged'; source.records[source.records.length - 1] = '|forged';
      }],
    ];
    for (const form of FORMS) for (const [expected, label, change] of cases) {
      const audit = mutated(w.audits[form], change);
      assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit))), expected, `${form}: ${label}`);
    }
  }
});

test('foreign battle origin, missing authority, changed cursor and future prefix reject', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const audit = w.audits.ordinary; const legacy = makeLegacy(w);
    const foreign = witnessModule.buildAudit(w, 'ordinary', { origin: { ...w.origin, battle_key: 'someone-else' } });
    assert.equal(code(() => checkKnowledgeSourceBinding(foreign, makeRegistry(w), legacy, profileOf(foreign))), 'source/foreign-origin');
    const expectations: [string, RegistryOptions][] = [
      ['source/missing-origin', { origin: null }],
      ['source/missing-original-authority', { omitInitialization: ['p2'] }],
      ['source/missing-request-delivery', { omitRequests: ['p1:1'] }],
      ['source/missing-public-ledger', { ledger: null }],
      ['source/request-cursor', { cursorShift: { 'p2:1': -1 } }],
      ['source/request-cursor', { cursorShift: { 'p2:0': 1 } }],
      ['source/foreign-origin', { origin: { ...w.origin, battle_key: 'someone-else' } }],
    ];
    for (const [expected, options] of expectations) assert.equal(code(() => checkKnowledgeSourceBinding(audit, makeRegistry(w, options), legacy, profileOf(audit))), expected, JSON.stringify(Object.keys(options)));
    // Registry holds only the first causal prefix: deliveries and prefixes beyond it are future evidence.
    const early = makeRegistry(w, { ledger: w.ledger.slice(0, w.cursors[0]) });
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, early, legacy, profileOf(audit))), 'source/missing-request-delivery');
    // A ledger with one different earlier record is not the delivered spectator ledger.
    const wrong = w.ledger.slice(); wrong[3] = '|forged';
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, makeRegistry(w, { ledger: wrong }), legacy, profileOf(audit))), 'source/public-prefix');
  }
});

// ============================================================ legacy negatives
test('resealed wrong legacy joins reject in every form', async () => {
  const all = await witnesses;
  const fake = (prefix: string, digit: string) => prefix + digit.repeat(64);
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
    for (const owner of OWNERS) {
    const other = owner === 'p1' ? 'p2' : 'p1';
    const cases: [string, string, (rows: Record<string, Row[]>) => void][] = [
      ['legacy/observation', 'fabricated observation', rows => {
        const binding = rows.binding.find(b => b.owner === owner)!; const old = binding.input_observation; binding.input_observation = fake('obs-', 'b');
        for (const boundary of rows.boundary) for (const row of boundary.bindings) if (row.observation_id === old) row.observation_id = binding.input_observation;
      }],
      ['legacy/belief', 'fabricated belief', rows => {
        const binding = rows.binding.find(b => b.owner === owner)!; const old = binding.successor_belief; binding.successor_belief = fake('belief-', 'c');
        for (const boundary of rows.boundary) for (const row of boundary.bindings) if (row.belief_id === old) row.belief_id = binding.successor_belief;
      }],
      ['legacy/transition', 'fabricated transition', rows => { rows.binding.find(b => b.owner === owner)!.transition = fake('transition-', 'a'); }],
      ['legacy/actor-record', 'wrong actor DATA record', rows => {
        const binding = rows.binding.find(b => b.owner === owner)!; binding.actor_record = w.python_record_ids[other];
        for (const boundary of rows.boundary) for (const row of boundary.bindings) if (row.owner === owner && row.actor_record_id !== null) row.actor_record_id = binding.actor_record;
      }],
      ['legacy/observation', 'sha256 placeholder never joins a native object', rows => {
        const binding = rows.binding.find(b => b.owner === owner)!; const old = binding.input_observation; binding.input_observation = fake('sha256:', 'd');
        for (const boundary of rows.boundary) for (const row of boundary.bindings) if (row.observation_id === old) row.observation_id = binding.input_observation;
      }],
      ['legacy/initial-actor', 'DATA row claimed at the origin boundary', rows => {
        const first = rows.boundary.find(b => b.index === 0)!; first.bindings.find((r: Row) => r.owner === owner)!.actor_record_id = w.python_record_ids[owner];
      }],
    ];
    for (const form of FORMS) for (const [expected, label, change] of cases) {
      const audit = mutated(w.audits[form], change);
      assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit))), expected, `${owner} ${form}: ${label}`);
    }
    }
    // Cross-schema/other-battle legacy objects never satisfy this origin.
    const foreign = all[VERSIONS[version === VERSIONS[0] ? 1 : 0]];
    assert.equal(code(() => checkKnowledgeSourceBinding(w.audits.ordinary, registry, makeLegacy(foreign), profileOf(w.audits.ordinary))), 'legacy/observation');
  }
});

test('wrong history prefix is caught through the adapter seam; arbitrary booleans and digests are not evidence', async () => {
  const w = (await witnesses)[VERSIONS[0]]; const registry = makeRegistry(w); const audit = w.audits.ordinary;
  const ordinary = (envelope: any) => {
    const b = new LegacyContextBuilder(); b.addEnvelope(envelope); return b;
  };
  // Test-only adapter wrapping the actual validator and then tampering the history prefix.
  const tamper: LegacyEnvelopeAdapter = {
    schema_version: 'test-tampered-history/v1',
    verify(envelope: any) {
      const probe = ordinary(envelope.bundle); assert.ok(probe);
      const b = envelope.bundle;
      return { owner: b.perspective, battle_id: b.battle_id, input_observation: b.input_observation.observation_id, successor_observation: b.successor_observation.observation_id,
        input_belief: b.input_belief.belief_id, successor_belief: b.successor_belief.belief_id, transition: b.transition.transition_id, actor_record: w.python_record_ids[b.perspective],
        input_prefix: [...b.input_observation.protocol_prefix.slice(0, -1), '|forged'], successor_prefix: [...b.input_observation.protocol_prefix.slice(0, -1), '|forged', ...b.successor_observation.protocol_prefix.slice(b.input_observation.protocol_prefix.length)] };
    },
  };
  const builder = new LegacyContextBuilder([tamper]);
  for (const owner of OWNERS) builder.addEnvelope({ schema_version: 'test-tampered-history/v1', bundle: w.bundles[owner] });
  assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, builder.freeze(), profileOf(audit))), 'legacy/prefix');
  // A real extension adapter that calls the existing validators is accepted through the same seam.
  const wrap: LegacyEnvelopeAdapter = {
    schema_version: 'test-wrapper/v1',
    verify(envelope: any) {
      const inner = new LegacyContextBuilder(); inner.addEnvelope(envelope.bundle);
      const b = envelope.bundle;
      return { owner: b.perspective, battle_id: b.battle_id, input_observation: b.input_observation.observation_id, successor_observation: b.successor_observation.observation_id,
        input_belief: b.input_belief.belief_id, successor_belief: b.successor_belief.belief_id, transition: b.transition.transition_id, actor_record: w.python_record_ids[b.perspective],
        input_prefix: [...b.input_observation.protocol_prefix], successor_prefix: [...b.successor_observation.protocol_prefix] };
    },
  };
  const wrapped = new LegacyContextBuilder([wrap]);
  for (const owner of OWNERS) wrapped.addEnvelope({ schema_version: 'test-wrapper/v1', bundle: w.bundles[owner] });
  assert.equal(checkKnowledgeSourceBinding(audit, registry, wrapped.freeze(), profileOf(audit)).legacy_verification.verified, true);
  // Digest-shaped placeholders or booleans returned by an adapter are not legacy evidence.
  const forged: LegacyEnvelopeAdapter = { schema_version: 'test-forged/v1', verify: () => ({ owner: 'p1', battle_id: w.battle_id, input_observation: 'sha256:' + '1'.repeat(64), successor_observation: 'sha256:' + '2'.repeat(64),
    input_belief: 'sha256:' + '3'.repeat(64), successor_belief: 'sha256:' + '4'.repeat(64), transition: null, actor_record: null, input_prefix: [], successor_prefix: [] }) };
  assert.equal(code(() => new LegacyContextBuilder([forged]).addEnvelope({ schema_version: 'test-forged/v1' })), 'legacy/adapter-result');
  assert.equal(code(() => new LegacyContextBuilder().addEnvelope({ schema_version: 'pipeline-linked-record/v1', verified: true })), 'legacy/validator-rejected');
  assert.equal(code(() => new LegacyContextBuilder().addEnvelope(true as any)), 'legacy/unsupported-envelope-kind');
  assert.equal(code(() => new LegacyContextBuilder([{ schema_version: 'pipeline-linked-record/v1', verify: () => { throw new Error('x'); } }])), 'legacy/adapter');
});

test('unsupported legacy envelope kinds fail explicitly; tampered ordinary bundles fail the real validator', async () => {
  const w = (await witnesses)[VERSIONS[1]];
  for (const kind of ['pipeline-forced-switch-record/v1', 'pipeline-revival-record/v1', 'pipeline-episode-evidence/v2', 'pipeline-episode-evidence/v1', 'pipeline-episode-publication-sweep/v1', 'unknown/v9']) {
    const envelope = { ...structuredClone(w.bundles.p1), schema_version: kind };
    assert.equal(code(() => new LegacyContextBuilder().addEnvelope(envelope)), 'legacy/unsupported-envelope-kind', kind);
  }
  const tamper = (change: (b: any) => void) => { const b = structuredClone(w.bundles.p1); change(b); return b; };
  for (const bad of [
    tamper(b => { b.battle_id = 'other'; }), tamper(b => { b.transition.transition_id = 'transition-' + 'e'.repeat(64); }),
    tamper(b => { b.successor_belief.parent_belief_id = 'belief-' + 'f'.repeat(64); }), tamper(b => { b.input_observation.protocol_prefix.push('|forged'); }),
    tamper(b => { b.action.action_id = 'act-' + '0'.repeat(64); }),
  ]) assert.equal(code(() => new LegacyContextBuilder().addEnvelope(bad)), 'legacy/validator-rejected');
  // Nonactor evidence also needs genuinely validated objects.
  const b = w.bundles.p2; const pair = (side: 'input' | 'successor') => ({ observation: b[side + '_observation'], belief: b[side + '_belief'] });
  const swapped = { owner: 'p1', input: pair('input'), successor: pair('successor') };
  assert.equal(code(() => new LegacyContextBuilder().addNonactorEvidence(swapped)), 'legacy/validator-rejected');
  const forgedBelief = structuredClone(pair('successor')); forgedBelief.belief.belief_id = 'belief-' + '9'.repeat(64);
  assert.equal(code(() => new LegacyContextBuilder().addNonactorEvidence({ owner: 'p2', input: pair('input'), successor: forgedBelief })), 'legacy/validator-rejected');
  assert.equal(code(() => new LegacyContextBuilder().addNonactorEvidence({ owner: 'p2', input: pair('successor'), successor: pair('input') })), 'legacy/validator-rejected');
});


test('forged labels, legacy-normalized request text and complete claims never succeed', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
    const audit = w.audits.ordinary;
    // The session's normalized request object is not the delivered addressed text.
    const delivered = w.requests.p1[0].json;
    const normalized = JSON.stringify(w.bundles.p1.input_observation.request);
    assert.notEqual(normalized, delivered);
    const swapped = mutated(audit, rows => { sourceRow(rows, 'owner_request', 'p1', 0).raw_request.json = normalized; });
    assert.equal(code(() => checkKnowledgeSourceBinding(swapped, registry, legacy, profileOf(swapped))), 'source/request-text');
    // Forged source labels are rejected by structure or by the source join; never accepted.
    const labels: ((rows: Record<string, Row[]>) => void)[] = [
      rows => { sourceRow(rows, 'owner_initialization', 'p1').phase = 'chronological'; },
      rows => { sourceRow(rows, 'owner_initialization', 'p1').provider = 'addressed-request/v1'; },
      rows => { sourceRow(rows, 'owner_request', 'p2', 1).owner = 'p1'; },
      rows => { sourceRow(rows, 'owner_request', 'p1', 1).delivery_cursor = 3; },
      rows => { sourceRow(rows, 'owner_initialization', 'p2').team[0].extra = 'x'; },
    ];
    for (const change of labels) {
      const forged = mutated(audit, change);
      const failure = code(() => checkKnowledgeSourceBinding(forged, registry, legacy, profileOf(forged)));
      assert.equal(failure, 'structure'); // closed schema/addressing rules reject every forged label before the source join
    }
    // A producer-claimed complete verdict cannot turn missing/unsupported authority into completeness.
    const claim = mutated(audit, rows => { for (const v of rows.verdict) v.result = 'strong_complete'; });
    assert.equal(checkKnowledgeSourceBinding(claim, registry, legacy, profileOf(claim)).completeness, 'not_established');
    // A failed check leaves both capabilities usable and unchanged.
    const again = checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit));
    assert.equal(again.source_verification.verified, true);
    assert.deepEqual(registry.availability.initialization_witness_owners, ['p1', 'p2']);
  }
});

test('boundary-row-only mutations are rejected by the accepted structure check, not by the new joins', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) {
    const w = all[version]; const registry = makeRegistry(w); const legacy = makeLegacy(w);
    const second = (rows: Record<string, Row[]>, owner: string) => rows.boundary.find(b => b.index === 1)!.bindings.find((r: Row) => r.owner === owner)!;
    const changes: ((rows: Record<string, Row[]>) => void)[] = [
      rows => { second(rows, 'p1').actor_record_id = w.python_record_ids.p2; },
      rows => { second(rows, 'p1').observation_id = 'obs-' + 'b'.repeat(64); },
      rows => { const b = rows.boundary.find(x => x.index === 1)!; [b.bindings[0].owner, b.bindings[1].owner] = [b.bindings[1].owner, b.bindings[0].owner]; },
    ];
    for (const form of FORMS) for (const change of changes) {
      const audit = mutated(w.audits[form], change);
      assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit))), 'structure');
    }
  }
});

// ======================================================= capability and privacy
test('plain, copied, serialized or audit-supplied capabilities cannot stand in; builders are not capabilities', async () => {
  const w = (await witnesses)[VERSIONS[0]]; const audit = w.audits.full; const registry = makeRegistry(w); const legacy = makeLegacy(w);
  const forgedRegistries: any[] = [
    {}, { ...registry }, Object.create(registry), Object.assign(Object.create(Object.getPrototypeOf(registry)), registry),
    JSON.parse(JSON.stringify(registry)), structuredClone(registry), registry.availability, null, undefined, 'registry', new SourceRegistryBuilder(),
    { origin: w.origin, initialization: w.team_sets, requests: w.requests, ledger: w.ledger },
  ];
  for (const fake of forgedRegistries) assert.equal(code(() => checkKnowledgeSourceBinding(audit, fake, legacy, profileOf(audit))), 'capability/registry');
  for (const fake of [{}, { ...legacy }, Object.create(legacy), JSON.parse(JSON.stringify(legacy)), legacy.availability, new LegacyContextBuilder(), { pairs: [] }, true, 0] as any[]) {
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, fake, profileOf(audit))), 'capability/legacy');
  }
  assert.equal(code(() => new SourceRegistry(Symbol('forged'), {} as any)), 'capability/registry');
  assert.equal(code(() => new LegacyContext(Symbol('forged'), {} as any)), 'capability/legacy');
  // Audit-supplied registry/provider/receipt fields are closed-schema extra keys and reject in the accepted structure check.
  for (const form of FORMS) {
    const withRegistry = structuredClone(w.audits[form]); withRegistry.registry = { origin: w.origin }; withRegistry.id = knowledgeIdentity(withRegistry);
    assert.equal(code(() => checkKnowledgeSourceBinding(withRegistry, registry, legacy, profileOf(withRegistry))), 'structure');
  }
  // Structure comes first: a forged capability does not change the structural decision for a malformed audit.
  assert.equal(code(() => checkKnowledgeSourceBinding({ kind: 'audit' }, {} as any, {} as any, 'x')), 'structure');
  assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, legacy, 'sha256:' + '0'.repeat(64))), 'structure');
  assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, legacy, 7 as any)), 'profile');
});

test('builders are one-shot and freeze authority; caller input mutation after registration changes nothing', async () => {
  const w = structuredClone((await witnesses)[VERSIONS[0]]) as Witness; const audit = JSON.parse(JSON.stringify(w.audits.ordinary)); // detach shared references from the mutated caller objects
  const rb = new SourceRegistryBuilder(); rb.setOrigin(w.origin);
  for (const owner of OWNERS) { rb.addInitializationWitness(owner, w.team_sets[owner]); for (const r of w.requests[owner]) rb.addRequestDelivery(owner, r.sequence, r.cursor, r.json); }
  rb.setPublicLedger(w.ledger);
  assert.equal(code(() => rb.setPublicLedger(w.ledger)), 'registry/duplicate');
  assert.equal(code(() => rb.addInitializationWitness('p1', w.team_sets.p1)), 'registry/initialization');
  assert.equal(code(() => rb.addRequestDelivery('p1', 0, 1, '{}')), 'registry/request');
  assert.equal(code(() => rb.addRequestDelivery('p3', 9, 1, '{}')), 'registry/request');
  assert.equal(code(() => rb.addRequestDelivery('p1', 9, 1, '{"a":1,"a":2}')), 'registry/request');
  const registry = rb.freeze();
  assert.equal(code(() => rb.setReplaySource([])), 'registry/frozen');
  assert.equal(code(() => rb.freeze()), 'registry/frozen');
  const lb = new LegacyContextBuilder(); for (const owner of OWNERS) lb.addEnvelope(w.bundles[owner]);
  assert.equal(code(() => lb.addEnvelope(w.bundles.p1)), 'legacy/duplicate');
  const legacy = lb.freeze();
  assert.equal(code(() => lb.addEnvelope(w.bundles.p2)), 'legacy/frozen');
  const bundleBefore = literalCanonical(w.bundles);
  // Mutate every caller-owned object after registration.
  w.team_sets.p1[0].species = 'Mutated'; w.ledger[0] = '|mutated'; w.ledger.push('|extra'); w.origin.battle_key = 'mutated';
  w.bundles.p1.transition.transition_id = 'transition-' + '0'.repeat(64); w.bundles.p2.input_observation.protocol_prefix.push('|x');
  assert.equal(checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit)).source_verification.verified, true);
  // An audit crafted to agree with the mutated caller objects is still rejected.
  const crafted = mutated(audit, rows => { sourceRow(rows, 'owner_initialization', 'p1').team[0].species = 'Mutated'; });
  assert.equal(code(() => checkKnowledgeSourceBinding(crafted, registry, legacy, profileOf(crafted))), 'source/original-team');
  assert.notEqual(literalCanonical(w.bundles), bundleBefore);
});

test('capabilities expose no privileged data; diagnostics are payload-independent; module has no publication path', async () => {
  const w = (await witnesses)[VERSIONS[0]]; const registry = makeRegistry(w); const legacy = makeLegacy(w); const audit = w.audits.ordinary;
  for (const capability of [registry, legacy]) {
    assert.deepEqual(Object.keys(capability), ['availability']);
    assert.deepEqual(Object.getOwnPropertySymbols(capability), []);
    assert.ok(Object.isFrozen(capability) && Object.isFrozen((capability as any).availability));
    const text = JSON.stringify(capability);
    for (const secret of [w.team_sets.p1[0].species, w.requests.p1[0].json.slice(0, 20), w.bundles.p1.input_observation.observation_id, w.battle_id, '|switch']) assert.ok(!text.includes(secret));
  }
  const privateText = [w.team_sets.p1[0].species, w.battle_id, w.requests.p1[1].json.slice(0, 24), w.bundles.p1.input_observation.observation_id, w.ledger[3]];
  const bad = mutated(audit, rows => { sourceRow(rows, 'owner_request', 'p1', 1).raw_request.json += ' '; });
  for (const run of [() => checkKnowledgeSourceBinding(bad, registry, legacy, profileOf(bad)), () => checkKnowledgeSourceBinding(audit, {} as any, legacy, profileOf(audit)),
    () => new LegacyContextBuilder().addEnvelope({ schema_version: 'pipeline-linked-record/v1', battle_id: privateText[1] })]) {
    try { run(); assert.fail('rejection expected'); } catch (error: any) {
      assert.ok(error instanceof KnowledgeSourceError); assert.match(error.code, /^[a-z-]+\/[a-z-]+$|^structure$|^profile$/);
      assert.equal(error.message, error.code); assert.equal(Object.keys(error).join(), 'code');
      for (const secret of privateText) assert.ok(!String(error.stack).includes(secret));
    }
  }
  // No projection, publication, CLI or registry import/export surface exists.
  assert.deepEqual(Object.keys(sourceModule).sort(), ['KnowledgeSourceError', 'LegacyContext', 'LegacyContextBuilder', 'SourceRegistry', 'SourceRegistryBuilder', 'checkKnowledgeSourceBinding', 'legacyDataRecordId']);
  const result = checkKnowledgeSourceBinding(audit, registry, legacy, profileOf(audit));
  assert.equal(result.published, false);
  assert.ok(!('projection' in result) && !('registry' in result) && !('assurance' in result));
});

// ========================================================== replay (distinct regime)
test('replay: explicit hand-audited local source held in memory; no attribution or legacy authority follows', () => {
  // Hand-audited oracle metadata for the checked-in replay fixtures (literal U+00C9 and U+1F600).
  const oracleOrigin = { battle_key: 'fixture-\u00c9clair-\u{1F600}', format: 'gen9randombattle', engine: 'pokemon-showdown@0.11.10', rule_version: 'pk-rules/v1' };
  const oracleReplay = ['|start', '|switch|p1a: \u00c9clair|Pikachu, L80|100/100', '|switch|p2a: Beta|Gengar, L80|100/100', '|-enditem|p1a: \u00c9clair|Oran Berry|[eat]',
    '|move|p2a: Beta|Tackle|p1a: \u00c9clair', '|replace|p2a: Beta|Zoroark, L80|100/100', '|win|\u00c9clair'];
  const registryFor = (records: string[] | null, origin: Row | null = oracleOrigin) => {
    const builder = new SourceRegistryBuilder(); if (origin) builder.setOrigin(origin as any);
    if (records) builder.setReplaySource(records); return builder.freeze();
  };
  const oracleSuffix = [...oracleReplay.slice(0, 6), '|win|Beta']; // hand-audited changed complete replay source
  for (const [name, replay] of [['replay-full.json', oracleReplay], ['replay-ordinary.json', oracleReplay], ['replay-compact.json', oracleReplay], ['replay-suffix-full.json', oracleSuffix], ['replay-suffix-compact.json', oracleSuffix]] as [string, string[]][]) {
    const audit = load(name);
    const other = replay === oracleReplay ? oracleSuffix : oracleReplay;
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, registryFor(other), null, profileOf(audit))), 'source/replay-source', name);
    const result = checkKnowledgeSourceBinding(audit, registryFor(replay), null, profileOf(audit));
    assert.equal(result.source_verification.replay_source, true, name);
    assert.equal(result.source_verification.original_delivery, 'absent');
    assert.equal(result.original_attribution, 'unverified'); assert.equal(result.completeness, 'not_established');
    assert.deepEqual(result.missing_capabilities, ['legacy_context', 'original_delivery_authority', 'original_provider']);
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, registryFor(null), null, profileOf(audit))), 'source/missing-replay-source');
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, registryFor(replay.slice(0, 5)), null, profileOf(audit))), 'source/replay-source');
    const changed = replay.slice(); changed[2] = '|switch|p2a: Beta|Gengar, L81|100/100';
    assert.ok(code(() => checkKnowledgeSourceBinding(audit, registryFor(changed), null, profileOf(audit))).startsWith('source/'));
    assert.equal(code(() => checkKnowledgeSourceBinding(audit, registryFor(replay, { ...oracleOrigin, battle_key: 'foreign' }), null, profileOf(audit))), 'source/foreign-origin');
  }
  // Placeholder sha256 legacy stand-ins never join real legacy objects.
  const audit = load('replay-full.json');
  assert.equal(code(() => checkKnowledgeSourceBinding(audit, registryFor(oracleReplay), new LegacyContextBuilder().freeze(), profileOf(audit))), 'legacy/observation');
});

test('hand-authored structure canaries are not source positives', () => {
  const audit = load('sim-ordinary.json');
  assert.equal(checkKnowledgeStructure(audit).structure_valid, true);
  const registry = new SourceRegistryBuilder().freeze();
  assert.equal(code(() => checkKnowledgeSourceBinding(audit, registry, null, profileOf(audit))), 'source/missing-origin');
});

// ================================================== DATA identity adapter parity
test('DATA-001 identity adapter equals the Python identity payload for ASCII, control, BMP and astral prefixes', () => {
  // Expected digests were produced by trainer/src/neural/dataset_lineage.expected_record_id (independent Python oracle).
  const vectors: [string, string[], string][] = [
    ['ascii', ['|start', '|switch|p1a: Alpha|Pikachu, L80|100/100'], 'datarec-7e1d02d5c7e300eaa7bc8c50a729e8e068122603341ae9b523e9f94299e9da6b'],
    ['control', ['|ctl\u0001\u001f|tab\t|nl\n|cr\r|del\u007f|bs\b|ff\f|q"|bs\\|sl/'], 'datarec-1e9742c83a45eb2a90f0ac44afa2eb837a93582a11b7d122765432a4614a1dc0'],
    ['bmp', ['|bmp \u00c9\u00e9\u3042 \u20ac|\ufffd\uffff'], 'datarec-9bca5bf6f8789057cae374f712b27047b14b9c397cf545b0eb174746a99a5420'],
    ['astral', ['|astral \u{1F600} \u{1D11E}|end'], 'datarec-78d4b16002a4794496e5b4d65f2bf70dc41a6907cf54d763283db90faa2556e3'],
    ['empty', [], 'datarec-62c8c45e54ac375c8ebb40f844d478f47f81c4d4351baa0d43308d74b04ea083'],
  ];
  const h = (c: string) => c.repeat(64);
  for (const [name, prefix, expected] of vectors) {
    assert.equal(legacyDataRecordId({ battle_id: 'vec-' + name, perspective: 'p1', protocol_prefix: prefix, observation_id: 'obs-' + h('1'), action_id: 'act-' + h('2'), belief_id: 'belief-' + h('3'), transition_id: 'transition-' + h('4') }), expected, name);
  }
});

test('real bundles: TypeScript adapter DATA IDs equal the independent Python validator IDs', async () => {
  const all = await witnesses;
  for (const version of VERSIONS) for (const owner of OWNERS) {
    const b = all[version].bundles[owner];
    assert.equal(legacyDataRecordId({ battle_id: b.battle_id, perspective: owner, protocol_prefix: b.input_observation.protocol_prefix, observation_id: b.input_observation.observation_id,
      action_id: b.action.action_id, belief_id: b.input_belief.belief_id, transition_id: b.transition.transition_id }), all[version].python_record_ids[owner]);
  }
});

test('old identities and the existing Python --check-structure output are unchanged', async () => {
  const vectors = load('identity-vectors.json');
  for (const vector of vectors) assert.equal(knowledgeIdentity(vector.object), vector.id);
  const w = (await witnesses)[VERSIONS[0]];
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase()))) as NodeJS.ProcessEnv;
  env.PYTHONPATH = path.join(root, 'trainer/src');
  const py = spawnSync(process.env.PYTHON || 'D:/Anaconda/envs/neuralgpu/python.exe', ['-m', 'neural.perspective_knowledge', '--check-structure'], { cwd: root, env, input: canonicalKnowledgeJson(w.audits.ordinary), encoding: 'utf8', timeout: 60000 });
  assert.equal(py.status, 0, py.stderr);
  assert.equal(py.stdout, '{"structure_valid":true,"source_semantics_verified":false,"completeness":"not_established","legacy_envelope_verified":false}\n');
});
