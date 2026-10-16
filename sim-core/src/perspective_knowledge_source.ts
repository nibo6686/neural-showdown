import { guardHistoricalKnowledgeSource } from './version_profile';
/**
 * PK-02B-Source: non-publishing source and legacy verification seam.
 *
 * A trusted local creation owner builds a registry capability and a legacy
 * context capability inside this process; `checkKnowledgeSourceBinding` then
 * joins an already structurally valid audit to them. Capabilities live in
 * module-private WeakMaps keyed by the capability object, so plain objects,
 * copies, serialized handles and audit fields cannot stand in for them. This is
 * a trusted-caller boundary, not authentication against code already controlling
 * the process. Source presence never certifies fact values: fact semantics,
 * original attribution, obligation completeness and aggregate completeness stay
 * unverified/not_established, and nothing here publishes or emits a projection.
 */
import { createHash } from 'node:crypto';
import {
  canonicalKnowledgeJson, checkKnowledgeStructure, knowledgeIdentity, parseKnowledgeJson,
} from './perspective_knowledge';
import { serializeBeliefState, validateObservableBattleState } from './belief_state';
import { validatePipelineLinkedRecordBundle, type PipelineLinkedRecordBundle } from './pipeline_integration';

type Row = Record<string, any>;
const LIVE_POLICY = 'simulator-causal/v1';
const OWNERS = ['p1', 'p2'];
const ORIGIN_CONSTANTS: Row = { format: 'gen9randombattle', engine: 'pokemon-showdown@0.11.10', rule_version: 'pk-rules/v1' };
const NATIVE: Record<string, RegExp> = {
  observation: /^obs-[0-9a-f]{64}$/, belief: /^belief-[0-9a-f]{64}$/, transition: /^transition-[0-9a-f]{64}$/, actor_record: /^datarec-[0-9a-f]{64}$/,
};
const REGISTRY_TOKEN = Symbol('registry');
const LEGACY_TOKEN = Symbol('legacy');

/** Payload-independent failure: `code` is a fixed string, never audit or source content. */
export class KnowledgeSourceError extends Error {
  readonly code: string;
  constructor(code: string) { super(code); this.code = code; }
}
function fail(code: string): never { throw new KnowledgeSourceError(code); }
function need(condition: unknown, code: string): asserts condition { if (!condition) fail(code); }
function same(a: unknown, b: unknown): boolean { return canonicalKnowledgeJson(a).equals(canonicalKnowledgeJson(b)); }
function snapshot<T>(value: T, code: string): T {
  try { return parseKnowledgeJson(canonicalKnowledgeJson(value)) as T; } catch { return fail(code); }
}
function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object') { for (const item of Object.values(value)) deepFreeze(item); Object.freeze(value); }
  return value;
}
function isPrefix(shorter: readonly string[], longer: readonly string[]): boolean {
  return shorter.length <= longer.length && shorter.every((line, index) => line === longer[index]);
}

// ---------------------------------------------------------------- registry

interface RegistryData {
  origin: Row | null;
  initialization: Map<string, Row[]>;
  requests: Map<string, { cursor: number; json: string }>;
  ledger: string[] | null;
  replay: string[] | null;
}
const registries = new WeakMap<object, RegistryData>();

export interface RegistryAvailability {
  readonly origin: boolean;
  /** Test-owned initialization witnesses only. No production original provider is adopted. */
  readonly initialization_witness_owners: readonly string[];
  readonly original_provider: 'not_adopted';
  readonly request_deliveries: number;
  readonly public_ledger: boolean;
  readonly replay_source: boolean;
}

/** Opaque frozen registry capability. Only `SourceRegistryBuilder.freeze` creates one. */
export class SourceRegistry {
  readonly availability: RegistryAvailability;
  constructor(token: symbol, data: RegistryData) {
    guardHistoricalKnowledgeSource();
    if (token !== REGISTRY_TOKEN) fail('capability/registry');
    registries.set(this, data);
    this.availability = deepFreeze({
      origin: data.origin !== null,
      initialization_witness_owners: [...data.initialization.keys()].sort(),
      original_provider: 'not_adopted' as const,
      request_deliveries: data.requests.size,
      public_ledger: data.ledger !== null,
      replay_source: data.replay !== null,
    });
    Object.freeze(this);
  }
}

function checkedRecords(records: unknown, code: string): string[] {
  need(Array.isArray(records), code);
  return snapshot(records as string[], code);
}

/**
 * Trusted-owner construction. Every method deep-copies its inputs; the builder
 * becomes unusable after `freeze`. There is no audit-scanning factory.
 */
export class SourceRegistryBuilder {
  constructor() { guardHistoricalKnowledgeSource(); }
  #data: RegistryData | null = { origin: null, initialization: new Map(), requests: new Map(), ledger: null, replay: null };

  #open(): RegistryData { need(this.#data, 'registry/frozen'); return this.#data; }

  setOrigin(origin: Record<string, unknown>): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); need(data.origin === null, 'registry/duplicate');
    const copy = snapshot(origin, 'registry/origin') as Row;
    need(Object.keys(copy).sort().join() === 'battle_key,engine,format,rule_version' && typeof copy.battle_key === 'string' && copy.battle_key.length > 0, 'registry/origin');
    for (const [key, value] of Object.entries(ORIGIN_CONSTANTS)) need(copy[key] === value, 'registry/origin');
    data.origin = deepFreeze(copy);
  }

  /** Test-owned initialization witness: never evidence that a production provider exists. */
  addInitializationWitness(owner: string, team: readonly Row[]): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); need(OWNERS.includes(owner) && !data.initialization.has(owner), 'registry/initialization');
    const copy = snapshot(team as Row[], 'registry/initialization');
    need(Array.isArray(copy) && copy.length >= 1 && copy.length <= 6 && copy.every((set, i) => set !== null && typeof set === 'object' && set.slot === i + 1), 'registry/initialization');
    data.initialization.set(owner, deepFreeze(copy));
  }

  addRequestDelivery(owner: string, sequence: number, cursor: number, json: string): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); const key = `${owner}:${sequence}`;
    need(OWNERS.includes(owner) && Number.isInteger(sequence) && sequence >= 0 && Number.isInteger(cursor) && cursor >= 0 && typeof json === 'string' && !data.requests.has(key), 'registry/request');
    snapshot({ raw_request: { json } }, 'registry/request'); // exact text must obey the raw-request limits
    data.requests.set(key, { cursor, json });
  }

  setPublicLedger(records: readonly string[]): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); need(data.ledger === null, 'registry/duplicate');
    data.ledger = deepFreeze(checkedRecords(records, 'registry/ledger'));
  }

  /** Explicit owner-selected local replay source evidence; no external loading. */
  setReplaySource(records: readonly string[]): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); need(data.replay === null, 'registry/duplicate');
    data.replay = deepFreeze(checkedRecords(records, 'registry/replay'));
  }

  freeze(): SourceRegistry {
    guardHistoricalKnowledgeSource();
    const data = this.#open();
    for (const owner of OWNERS) {
      const cursors = [...data.requests].filter(([key]) => key.startsWith(owner + ':')).map(([key, v]) => [Number(key.slice(3)), v.cursor]).sort((a, b) => a[0] - b[0]);
      need(cursors.every(([seq, cursor], i) => seq === i && (i === 0 || cursor >= cursors[i - 1][1]) && (data.ledger === null || cursor <= data.ledger.length)), 'registry/request-order');
    }
    this.#data = null; // builder cannot mutate the frozen capability
    for (const value of data.requests.values()) Object.freeze(value);
    return new SourceRegistry(REGISTRY_TOKEN, Object.freeze(data) as RegistryData);
  }
}

// ----------------------------------------------------------- legacy context

/** Normalized facts an adapter extracts from a locally validated legacy object. */
export interface LegacyPairEvidence {
  owner: string;
  battle_id: string;
  input_observation: string;
  successor_observation: string;
  input_belief: string;
  successor_belief: string;
  /** Null together with actor_record for nonactor evidence. */
  transition: string | null;
  actor_record: string | null;
  input_prefix: string[];
  successor_prefix: string[];
}
/** Later envelope kinds plug in here; `verify` must call the actual existing validators. */
export interface LegacyEnvelopeAdapter {
  readonly schema_version: string;
  verify(envelope: unknown): LegacyPairEvidence;
}

function pythonCanonicalJson(value: unknown): string {
  const visit = (item: any): string => {
    if (Array.isArray(item)) return '[' + item.map(visit).join(',') + ']';
    if (item !== null && typeof item === 'object') return '{' + Object.keys(item).sort().map((k) => JSON.stringify(k) + ':' + visit(item[k])).join(',') + '}';
    return JSON.stringify(item);
  };
  // Python json.dumps(ensure_ascii=True): everything outside space..~ becomes lower-case \uXXXX per UTF-16 unit.
  return visit(value).replace(/[^ -~]/g, (char) => '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0'));
}
const sha256Hex = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');

/**
 * DATA-001 `record_id` of an actor record, computed with the existing Python
 * identity payload and ensure_ascii canonical bytes. Identity only: no DATA
 * object is built or emitted and hashing grants no authority.
 */
export function legacyDataRecordId(fields: {
  battle_id: string; perspective: string; protocol_prefix: readonly string[];
  observation_id: string; action_id: string; belief_id: string; transition_id: string;
}): string {
  return 'datarec-' + sha256Hex(pythonCanonicalJson({
    schema_version: 'dataset-record/v1', battle_id: fields.battle_id, replay_id: `sim:${fields.battle_id}`, source_kind: 'sim_core',
    perspective: fields.perspective, observation_cursor: fields.protocol_prefix.length,
    observation_prefix_hash: sha256Hex(pythonCanonicalJson([...fields.protocol_prefix])),
    observation_id: fields.observation_id, action_id: fields.action_id, belief_id: fields.belief_id, transition_id: fields.transition_id,
  }));
}

const ordinaryBundleAdapter: LegacyEnvelopeAdapter = {
  schema_version: 'pipeline-linked-record/v1',
  verify(envelope: unknown): LegacyPairEvidence {
    const bundle = structuredClone(envelope) as PipelineLinkedRecordBundle;
    validatePipelineLinkedRecordBundle(bundle); // actual existing validator; throws on any defect
    return {
      owner: bundle.perspective, battle_id: bundle.battle_id,
      input_observation: bundle.input_observation.observation_id, successor_observation: bundle.successor_observation.observation_id,
      input_belief: bundle.input_belief.belief_id, successor_belief: bundle.successor_belief.belief_id,
      transition: bundle.transition.transition_id,
      actor_record: legacyDataRecordId({
        battle_id: bundle.battle_id, perspective: bundle.perspective, protocol_prefix: bundle.input_observation.protocol_prefix,
        observation_id: bundle.input_observation.observation_id, action_id: bundle.action.action_id,
        belief_id: bundle.input_belief.belief_id, transition_id: bundle.transition.transition_id,
      }),
      input_prefix: [...bundle.input_observation.protocol_prefix], successor_prefix: [...bundle.successor_observation.protocol_prefix],
    };
  },
};

interface ContextData {
  pairs: Map<string, LegacyPairEvidence>;
  observations: Map<string, { owner: string; battle_id: string; belief: string; prefix: string[] }>;
  kinds: Set<string>;
}
const contexts = new WeakMap<object, ContextData>();

export interface LegacyAvailability {
  readonly pairs: number;
  readonly nonactor_pairs: number;
  readonly envelope_kinds: readonly string[];
}
/** Opaque frozen locally verified legacy-context capability. */
export class LegacyContext {
  readonly availability: LegacyAvailability;
  constructor(token: symbol, data: ContextData) {
    guardHistoricalKnowledgeSource();
    if (token !== LEGACY_TOKEN) fail('capability/legacy');
    contexts.set(this, data);
    this.availability = deepFreeze({
      pairs: data.pairs.size, nonactor_pairs: [...data.pairs.values()].filter((p) => p.transition === null).length,
      envelope_kinds: [...data.kinds].sort(),
    });
    Object.freeze(this);
  }
}

const pairKey = (owner: string, input: string, successor: string): string => `${owner}|${input}|${successor}`;

export class LegacyContextBuilder {
  #data: ContextData | null = { pairs: new Map(), observations: new Map(), kinds: new Set() };
  readonly #adapters = new Map<string, LegacyEnvelopeAdapter>([[ordinaryBundleAdapter.schema_version, ordinaryBundleAdapter]]);

  constructor(extraAdapters: readonly LegacyEnvelopeAdapter[] = []) {
    guardHistoricalKnowledgeSource();
    for (const adapter of extraAdapters) {
      need(adapter && typeof adapter.schema_version === 'string' && typeof adapter.verify === 'function' && !this.#adapters.has(adapter.schema_version), 'legacy/adapter');
      this.#adapters.set(adapter.schema_version, adapter);
    }
  }
  #open(): ContextData { need(this.#data, 'legacy/frozen'); return this.#data; }

  /** Verifies a supplied envelope with its adapter; unsupported kinds fail explicitly. */
  addEnvelope(envelope: unknown): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open();
    const kind = envelope !== null && typeof envelope === 'object' ? (envelope as Row).schema_version : undefined;
    const adapter = typeof kind === 'string' ? this.#adapters.get(kind) : undefined;
    need(adapter, 'legacy/unsupported-envelope-kind');
    let evidence: LegacyPairEvidence;
    try { evidence = adapter.verify(envelope); } catch (error) {
      if (error instanceof KnowledgeSourceError) throw error;
      return fail('legacy/validator-rejected');
    }
    this.record(data, evidence, adapter.schema_version);
  }

  /** Real validated observation/belief evidence for an owner that did not act; no DATA row exists. */
  addNonactorEvidence(evidence: {
    owner: string;
    input: { observation: unknown; belief: unknown };
    successor: { observation: unknown; belief: unknown };
  }): void {
    guardHistoricalKnowledgeSource();
    const data = this.#open();
    let copy: Row;
    try { copy = structuredClone(evidence) as Row; } catch { return fail('legacy/validator-rejected'); }
    try {
      const sides = [copy.input, copy.successor];
      for (const side of sides) {
        validateObservableBattleState(side.observation); serializeBeliefState(side.belief);
        const observation = side.observation as Row, belief = side.belief as Row;
        need(belief.observation.observation_id === observation.observation_id && belief.battle_id === observation.battle_id
          && belief.perspective === observation.perspective && observation.perspective === copy.owner
          && same(belief.source_protocol_prefix, observation.protocol_prefix), 'legacy/validator-rejected');
      }
      const [before, after] = [copy.input.observation as Row, copy.successor.observation as Row];
      need(before.battle_id === after.battle_id && isPrefix(before.protocol_prefix, after.protocol_prefix)
        && copy.successor.belief.parent_belief_id === copy.input.belief.belief_id, 'legacy/validator-rejected');
      this.record(data, {
        owner: copy.owner, battle_id: before.battle_id,
        input_observation: before.observation_id, successor_observation: after.observation_id,
        input_belief: copy.input.belief.belief_id, successor_belief: copy.successor.belief.belief_id,
        transition: null, actor_record: null, input_prefix: [...before.protocol_prefix], successor_prefix: [...after.protocol_prefix],
      }, 'nonactor-observation-belief');
    } catch (error) {
      if (error instanceof KnowledgeSourceError) throw error;
      fail('legacy/validator-rejected');
    }
  }

  private record(data: ContextData, e: LegacyPairEvidence, kind: string): void {
    const shaped = e && OWNERS.includes(e.owner) && typeof e.battle_id === 'string' && NATIVE.observation.test(e.input_observation)
      && NATIVE.observation.test(e.successor_observation) && NATIVE.belief.test(e.input_belief) && NATIVE.belief.test(e.successor_belief)
      && (e.transition === null) === (e.actor_record === null)
      && (e.transition === null || NATIVE.transition.test(e.transition) && NATIVE.actor_record.test(e.actor_record!))
      && Array.isArray(e.input_prefix) && Array.isArray(e.successor_prefix) && isPrefix(e.input_prefix, e.successor_prefix);
    need(shaped, 'legacy/adapter-result');
    let pair: LegacyPairEvidence;
    try { pair = deepFreeze(structuredClone(e)); } catch { return fail('legacy/adapter-result'); }
    const key = pairKey(pair.owner, pair.input_observation, pair.successor_observation);
    need(!data.pairs.has(key), 'legacy/duplicate');
    for (const [observation, belief, prefix] of [[pair.input_observation, pair.input_belief, pair.input_prefix], [pair.successor_observation, pair.successor_belief, pair.successor_prefix]] as const) {
      const known = data.observations.get(observation);
      need(!known || known.owner === pair.owner && known.belief === belief && known.battle_id === pair.battle_id && same(known.prefix, prefix), 'legacy/inconsistent');
      data.observations.set(observation, { owner: pair.owner, battle_id: pair.battle_id, belief, prefix: [...prefix] });
    }
    data.pairs.set(key, pair); data.kinds.add(kind);
  }

  freeze(): LegacyContext {
    guardHistoricalKnowledgeSource();
    const data = this.#open(); this.#data = null;
    return new LegacyContext(LEGACY_TOKEN, data);
  }
}

// -------------------------------------------------------------------- check

export interface KnowledgeSourceDiagnostic {
  readonly structure_valid: true;
  readonly source_verification: {
    readonly scope: 'declared_source_rows_exact_match';
    readonly verified: true;
    readonly sources: number;
    readonly prefixes: number;
    readonly request_deliveries: number;
    readonly original_delivery: 'test_only_unverified' | 'partial' | 'absent';
    readonly replay_source: boolean;
  };
  readonly legacy_verification: {
    readonly scope: 'declared_external_positions' | 'not_checked';
    readonly verified: boolean;
    readonly boundaries: number;
    readonly bindings: number;
    readonly envelope_kinds: readonly string[];
  };
  readonly fact_semantics: 'unverified';
  readonly original_attribution: 'unverified';
  readonly obligation_completeness: 'not_established';
  readonly completeness: 'not_established';
  readonly missing_capabilities: readonly string[];
  readonly unsupported_capabilities: readonly string[];
  readonly published: false;
}

function expand(audit: Row): Record<string, Row[]> {
  return Object.fromEntries(Object.entries(audit.tables).map(([kind, rows]) => [kind,
    audit.form === 'compact' ? (Object.values(rows as Row) as Row[]) : (rows as Row[])]));
}

function joinSources(tables: Record<string, Row[]>, audit: Row, data: RegistryData, policy: string) {
  const origin = tables.origin.find((row) => row.id === audit.origin)!;
  need(data.origin !== null, 'source/missing-origin');
  const expected: Row = { kind: 'origin', ...data.origin };
  const { id: _held, ...heldBody } = origin;
  need(origin.id === knowledgeIdentity(expected) && same(heldBody, expected), 'source/foreign-origin');
  const ledger = policy === LIVE_POLICY ? data.ledger : data.replay;
  const initOwners = new Set<string>(); let deliveries = 0, replay = false;
  // Fixed type order keeps the first reported code deterministic.
  const rank: Record<string, number> = { owner_initialization: 0, owner_request: 1, public_replay: 2, public_prefix: 3 };
  for (const source of [...tables.source].sort((a, b) => rank[a.source_type] - rank[b.source_type])) {
    switch (source.source_type) {
      case 'owner_initialization': {
        const held = data.initialization.get(source.owner);
        need(held, 'source/missing-original-authority');
        need(same(source.team, held) && source.raw_request === null && source.records.length === 0, 'source/original-team');
        initOwners.add(source.owner); break;
      }
      case 'owner_request': {
        const held = data.requests.get(`${source.owner}:${source.delivery_seq}`);
        need(held, 'source/missing-request-delivery');
        need(held.cursor === source.delivery_cursor, 'source/request-cursor');
        need(source.raw_request !== null && held.json === source.raw_request.json && source.records.length === 0, 'source/request-text');
        deliveries++; break;
      }
      case 'public_prefix':
        need(ledger, 'source/missing-public-ledger');
        need(isPrefix(source.records, ledger), 'source/public-prefix'); break;
      default: // public_replay
        need(data.replay, 'source/missing-replay-source');
        need(same(source.records, data.replay), 'source/replay-source');
        replay = true;
    }
  }
  for (const prefix of tables.prefix) { need(ledger, 'source/missing-public-ledger'); need(isPrefix(prefix.records, ledger), 'source/prefix'); }
  return { initOwners, deliveries, replay };
}

function joinLegacy(tables: Record<string, Row[]>, audit: Row, data: ContextData) {
  const byId = new Map<string, Row>(Object.values(tables).flat().map((row) => [row.id, row]));
  const get = (id: string): Row => byId.get(id)!;
  const origin = get(audit.origin);
  for (const boundary of tables.boundary) {
    for (const row of boundary.bindings) {
      const seen = data.observations.get(row.observation_id);
      need(seen && seen.owner === row.owner && seen.battle_id === origin.battle_key, 'legacy/observation');
      need(row.belief_id === seen.belief, 'legacy/belief');
      const current = get(get(row.knowledge).current);
      need(same(get(current.prefix).records, seen.prefix), 'legacy/prefix');
      need(boundary.index > 0 || row.actor_record_id === null, 'legacy/initial-actor');
    }
  }
  for (const binding of tables.binding) {
    const pair = data.pairs.get(pairKey(binding.owner, binding.input_observation, binding.successor_observation));
    need(pair && pair.battle_id === origin.battle_key, 'legacy/missing-pair');
    need(binding.input_belief === pair.input_belief && binding.successor_belief === pair.successor_belief, 'legacy/belief');
    need(binding.transition === pair.transition, 'legacy/transition');
    need(binding.actor_record === pair.actor_record, 'legacy/actor-record');
  }
  return { boundaries: tables.boundary.length, bindings: tables.binding.length };
}

/**
 * Entry check: accepted structure first, then declared source and legacy joins.
 * `legacy` may be null to run the source join alone; that is reported as a
 * missing capability, never as success of the legacy scope.
 */
export function checkKnowledgeSourceBinding(
  audit: unknown, registry: SourceRegistry, legacy: LegacyContext | null, requiredProfile: string,
): KnowledgeSourceDiagnostic {
  guardHistoricalKnowledgeSource();
  need(typeof requiredProfile === 'string', 'profile');
  const copy = snapshot(audit, 'structure') as Row; // one immutable view for every later step
  try { checkKnowledgeStructure(copy, requiredProfile); }
  catch { return fail('structure'); }
  const registryData = typeof registry === 'object' && registry !== null ? registries.get(registry) : undefined;
  need(registryData, 'capability/registry');
  const legacyData = legacy === null ? null : (typeof legacy === 'object' ? contexts.get(legacy) : undefined);
  need(legacy === null || legacyData, 'capability/legacy');
  const tables = expand(copy);
  const policy = tables.profile.find((row) => row.id === copy.required_profile)!.policy as string;
  const source = joinSources(tables, copy, registryData, policy);
  const joined = legacyData ? joinLegacy(tables, copy, legacyData) : null;
  return deepFreeze({
    structure_valid: true,
    source_verification: {
      scope: 'declared_source_rows_exact_match', verified: true, sources: tables.source.length, prefixes: tables.prefix.length,
      request_deliveries: source.deliveries, original_delivery: source.initOwners.size === 2 ? 'test_only_unverified' : source.initOwners.size === 1 ? 'partial' : 'absent', replay_source: source.replay,
    },
    legacy_verification: {
      scope: joined ? 'declared_external_positions' : 'not_checked', verified: joined !== null,
      boundaries: joined?.boundaries ?? 0, bindings: joined?.bindings ?? 0, envelope_kinds: legacyData ? [...legacyData.kinds].sort() : [],
    },
    fact_semantics: 'unverified', original_attribution: 'unverified',
    obligation_completeness: 'not_established', completeness: 'not_established',
    missing_capabilities: [...(joined ? [] : ['legacy_context']), ...(source.initOwners.size === 2 ? [] : ['original_delivery_authority']), 'original_provider'],
    unsupported_capabilities: ['original_provider', 'fact_semantics', 'original_attribution', 'family_obligations'],
    published: false,
  }) as KnowledgeSourceDiagnostic;
}
