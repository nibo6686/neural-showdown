import { assertAuthoritativeEnvironment } from './env_manager';
import { interpretOriginalValues } from './original_owner_values';
import { OwnedRequestHealthHost } from './owned_request_health';
import { OriginalOwnerCreation, type OriginalOwnerEvidence } from './original_owner_provider';
import { checkNativeOwnerMovesProjection, nativeOwnerMovesContext, checkNativeOwnerProjection, nativeOwnerDetailsContext, checkNativeOwnerDetailsProjection, nativeOwnerLoadoutContext, checkNativeOwnerLoadoutProjection, knowledgeIdentity, nativeOwnerProjectionContext, nativeOwnerHealthProjectionContext, checkNativeOwnerHealthProjection, nativeOwnerActiveOptionsContext, checkNativeOwnerActiveOptionsProjection, nativeOwnerIdentifiersContext, checkNativeOwnerIdentifiersProjection } from './perspective_knowledge';
import { assertNativeRuntimeProfile, NATIVE_ENGINE_COMMIT, NATIVE_ENGINE_INTEGRITY, type NativeRuntimeProfile } from './version_profile';
import type { PipelineBoundary } from './pipeline_integration';
import type { PlayerID } from './types';

export type OwnerKnowledgeHandle = Readonly<object>;
export interface OwnerKnowledgeRead {
  readonly projection: Readonly<Record<string, any>>;
  readonly binding: Readonly<{ observation_id: string; prefix_cursor: number; request_adaptation: 'not_adopted' | 'owned_health/v1'; request_descriptor?: 'not_adopted' | 'owned-active-options/v1'; request_state?: string }>;
}
const owners = ['p1', 'p2'] as const;
const token = (): object => Object.freeze(Object.create(null));
function fail(reason: string): never { throw new Error('native-owner-knowledge/v1/' + reason); }
function freeze<T>(value: T): T {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value;
}
type Frame = { environment: object; occurrence: object; rows: readonly OriginalOwnerEvidence[] };
type State = { parent: PipelineBoundary; source: Frame; starting: Record<PlayerID, readonly Record<string, any>[]>; interpretations?: Record<PlayerID, readonly Record<string, any>[]>;
  reads: Record<PlayerID, OwnerKnowledgeRead>; handles: Record<PlayerID, OwnerKnowledgeHandle> };
type Preparation = { environment: object; parent: PipelineBoundary | null; state: State; health?: { host: OwnedRequestHealthHost; token: object } };

/** Fixed addressed private consumer; never an import factory or native actor resolver. */
export class NativeOwnerKnowledgeController {
  readonly #creation: OriginalOwnerCreation;
  readonly #runtime: NativeRuntimeProfile;
  readonly #dex: any;
  readonly #recipients: Record<PlayerID, object>;
  #frame: Frame | null = null;
  #current: State | null = null;
  #prepared = new Map<object, Preparation>();
  #ready: Preparation | null = null;
  #closed = false;
  constructor(creation: OriginalOwnerCreation, runtime: NativeRuntimeProfile, recipients: Readonly<Record<PlayerID, object>>) {
    assertNativeRuntimeProfile(runtime);
    const profile = nativeOwnerProjectionContext().profile;
    if (runtime.package_version !== '0.11.11' || runtime.engine_commit !== NATIVE_ENGINE_COMMIT || profile.engine !== 'pokemon-showdown@' + runtime.package_version + '+b8f23c99' || profile.engine_commit !== runtime.engine_commit || profile.engine_integrity !== NATIVE_ENGINE_INTEGRITY) fail('runtime-profile');
    if (!recipients || ![Object.prototype, null].includes(Object.getPrototypeOf(recipients))
      || Object.keys(recipients).sort().join(',') !== 'p1,p2'
      || owners.some(owner => !Object.hasOwn(Object.getOwnPropertyDescriptor(recipients, owner) ?? {}, 'value'))
      || owners.some(owner => !recipients[owner] || typeof recipients[owner] !== 'object' || Array.isArray(recipients[owner]))
      || recipients.p1 === recipients.p2) fail('recipient-registration');
    this.#creation = creation; this.#runtime = runtime;
    this.#dex = require(runtime.entry).Dex.forFormat(profile.format);
    this.#recipients = Object.freeze({ p1: recipients.p1, p2: recipients.p2 });
    creation.registerKnowledgeReceiver((environment, occurrence, rows) => {
      if (this.#closed || this.#frame) fail('duplicate-or-late-enrollment');
      creation.assertKnowledgeEnrollment(environment, occurrence, rows);
      for (const [i, owner] of owners.entries()) {
        const row = rows[i];
        if (row.owner !== owner || row.labels.format !== profile.format || row.labels.simulator_revision !== runtime.reader.profile.revision
          || row.creation_sequence !== 0 || row.creation_cursor !== 0) fail('source-profile');
      }
      this.#frame = Object.freeze({ environment, occurrence, rows });
    });
  }
  private open(): void { if (this.#closed) fail('revoked'); }
  private source(): Frame {
    this.open(); assertNativeRuntimeProfile(this.#runtime);
    if (!this.#frame) fail('missing-enrollment');
    this.#creation.assertKnowledgeEnrollment(this.#frame.environment, this.#frame.occurrence, this.#frame.rows);
    return this.#frame;
  }
  prepare(environment: object, boundary: PipelineBoundary, parent: PipelineBoundary | null, healthHost?: OwnedRequestHealthHost, healthToken?: object): object {
    assertAuthoritativeEnvironment(environment);
    const source = this.source(), prior = this.#current, health = healthHost && healthToken ? { host: healthHost, token: healthToken } : undefined;
    if (parent !== (prior?.parent ?? null) || (parent ? boundary.step_index !== parent.step_index + 1 : boundary.step_index !== 0 || environment !== source.environment)) fail('parent');
    health?.host.assertPreparedBinding(health.token, environment, boundary, source.rows);
    const moves = !!health?.host.readPrepared(health.token, 'p1').moves, profile = (moves ? nativeOwnerMovesContext() : health ? nativeOwnerDetailsContext() : nativeOwnerProjectionContext()).profile;
    const starting = prior?.starting ?? Object.freeze({ p1: nativeOwnerStartingFacts(source.rows[0], this.#runtime, this.#dex, !!health), p2: nativeOwnerStartingFacts(source.rows[1], this.#runtime, this.#dex, !!health) });
    const interpret = (owner: PlayerID, index: number) => Object.freeze(source.rows[index].raw_team.map((set: any, slot) =>
      freeze({ subject: owner + ':roster:' + (slot + 1), ...interpretOriginalValues(set, this.#dex, require(this.#runtime.entry)).interpretation })));
    const interpretations = prior?.interpretations ?? (health ? Object.freeze({ p1: interpret('p1', 0), p2: interpret('p2', 1) }) : undefined);
    const reads = {} as Record<PlayerID, OwnerKnowledgeRead>;
    for (const owner of owners) {
      const obs = boundary.perspectives[owner].observation;
      if (obs.perspective !== owner || obs.battle_id !== source.rows[0].labels.battle_id
        || obs.event_cursor !== obs.protocol_prefix.length || boundary.battle_id !== obs.battle_id) fail('boundary');
      const count = source.rows[owners.indexOf(owner)].raw_team.length;
      const current = profile.rules.filter((r: any) => r.context === 'current' && !(health ? ['K05','K18','K19','K03','K04'] : ['K05']).includes(r.family)).flatMap((rule: any) => {
        const subjects = rule.subject === 'side' ? [owner + ':side'] : Array.from({ length: count }, (_, i) => owner + ':roster:' + (i + 1));
        return subjects.map(subject => freeze({ owner, subject, family: rule.family, property: rule.property, effect_key: null,
          state: 'unknown', value: null, reason: 'unimplemented_family', freshness: 'current', precision: 'not_applicable', observed_at: null }));
      });
      const adapted = health?.host.readPrepared(health.token, owner);
      if (adapted) current.push(...adapted.facts);
      if(adapted?.moves)for(const row of adapted.moves.roster){
        const index=current.findIndex((f:any)=>f.property==='current_moves'&&f.subject===row.subject),fact=row.current_moves;
        current[index]=freeze({owner,subject:row.subject,family:'K02',property:'current_moves',effect_key:null,state:fact.state,value:fact.state==='known'?{type:'texts',data:fact.value}:null,reason:fact.reason,freshness:'current',precision:fact.state==='known'?'exact':'not_applicable',observed_at:fact.observed_at});
      }
      const projection: Record<string, any> = { kind: 'projection', id: '', schema: moves ? 'perspective-knowledge-consumer/native11-moves-v1' : health ? 'perspective-knowledge-consumer/native11-details-v1' : 'perspective-knowledge-consumer/v1', owner,
        policy: profile.policy, boundary: boundary.step_index, required_profile: profile.id, result: 'incomplete',
        starting: starting[owner], ...(health ? { original_interpretation: interpretations![owner], current_stats_semantics: 'request-declared-baseStoredStats/v1' } : {}), ...(adapted?.moves ? {owned_moves:adapted.moves} : {}), starting_crosswalk: [], current, request: adapted?.descriptor ?? null };
      projection.id = knowledgeIdentity(projection); (moves ? checkNativeOwnerMovesProjection : health ? checkNativeOwnerDetailsProjection : checkNativeOwnerProjection)(projection);
      reads[owner] = freeze({ projection, binding: { observation_id: obs.observation_id,
        prefix_cursor: obs.event_cursor, ...(adapted ? { request_adaptation: 'owned_health/v1' as const, request_descriptor: 'owned-active-options/v1' as const, request_state: adapted.state } : { request_adaptation: 'not_adopted' as const }) } });
    }
    const prepared = token();
    this.#prepared.set(prepared, { environment, parent, health, state: { parent: boundary, source, starting, interpretations, reads,
      handles: { p1: token(), p2: token() } } }); return prepared;
  }
  preflight(prepared: object): void {
    const source = this.source(), entry = this.#prepared.get(prepared);
    if (!entry || entry.parent !== (this.#current?.parent ?? null) || entry.state.source !== source) fail('foreign-or-stale-preparation');
    entry.health?.host.assertPreparedBinding(entry.health.token, entry.environment, entry.state.parent, source.rows);
    entry.health?.host.preflight(entry.health.token);
    for (const owner of owners) {
      (entry.state.reads[owner].projection.owned_moves ? checkNativeOwnerMovesProjection : entry.health ? checkNativeOwnerDetailsProjection : checkNativeOwnerProjection)(entry.state.reads[owner].projection);
      if (this.#current && entry.state.starting[owner] !== this.#current.starting[owner]) fail('starting-lineage');
    }
    this.#ready = entry;
  }
  /** Trusted session barrier only: preflight precedes assignment-only installation. */
  installReady(): void { this.#current = this.#ready!.state; this.#ready = null; this.#prepared.clear(); }
  private owner(recipient: object): PlayerID {
    this.open(); const owner = owners.find(owner => this.#recipients[owner] === recipient);
    if (!owner || !this.#current) fail('foreign-recipient'); return owner;
  }
  handle(recipient: object): OwnerKnowledgeHandle { const owner = this.owner(recipient); return this.#current!.handles[owner]; }
  read(handle: OwnerKnowledgeHandle, recipient: object): OwnerKnowledgeRead {
    const owner = this.owner(recipient);
    if (handle !== this.#current!.handles[owner]) fail('foreign-copied-or-stale-handle');
    return this.#current!.reads[owner];
  }
  discard(environment: object): void {
    if (this.#ready?.environment === environment) this.#ready = null;
    for (const [key, value] of this.#prepared) if (value.environment === environment) this.#prepared.delete(key);
  }
  revoke(): void { this.#closed = true; this.#frame = null; this.#current = null; this.#ready = null; this.#prepared.clear(); }
}

function need(condition: unknown, code: string): asserts condition { if (!condition) throw new Error(code); }

/** Finite value interpreter only. Its output has no enrollment/consumer authority. */
function nativeOwnerStartingFacts(evidence: OriginalOwnerEvidence, runtime: NativeRuntimeProfile, dex: any, loadout = false): readonly Record<string, any>[] {
  assertNativeRuntimeProfile(runtime);
  need(runtime.engine_commit === NATIVE_ENGINE_COMMIT, 'native-original/runtime');
  const owner = evidence.owner;
  need(owners.includes(owner) && evidence.raw_team.length >= 1 && evidence.raw_team.length <= 6, 'native-original/roster');
  const rules = (loadout ? nativeOwnerLoadoutContext() : nativeOwnerProjectionContext()).profile.rules;
  const facts: Record<string, any>[] = [];
  const fact = (subject: string, property: string, value: any, tag: string) => {
    const rule = rules.find((r: Record<string, any>) => r.context === 'starting' && r.property === property);
    need(rule, 'native-original/property');
    facts.push(freeze({ owner, subject, family: rule.family, property, effect_key: null,
      state: value === null ? 'known_absent' : 'known', value: value === null ? null : { type: tag, data: value },
      reason: 'none', freshness: 'immutable', precision: value === null ? 'not_applicable' : 'exact', observed_at: 0 }));
  };
  fact(owner + ':side', 'roster_size', evidence.raw_team.length, 'integer');
  for (let i = 0; i < evidence.raw_team.length; i++) {
    const set = evidence.raw_team[i] as Record<string, any>, presence = evidence.field_presence[i], extra = evidence.non_submitted_fields[i];
    need(set && presence && extra && extra.unsupported.every(key => key === 'speciesId'), 'native-original/unsupported-field');
    // randomSet writes speciesId before getForme selects a cosmetic submission.
    // Enumerate that pinned method's sample domain without drawing or changing RNG.
    if (Object.hasOwn(set, 'speciesId')) {
      const source = dex.species.get(set.speciesId);
      const getForme = require(runtime.package_root + '/dist/data/random-battles/gen9/teams').default.prototype.getForme;
      const forms = new Set<string>(); let count = 1;
      for (let index = 0; index < count; index++) forms.add(getForme.call({gen: 9,
        format: dex.formats.get('gen9randombattle'), sample: (values: string[]) => {
          count = Math.max(count, values.length); return values[index % values.length];
        }}, source));
      need(typeof set.speciesId === 'string' && source.exists && forms.has(set.species), 'native-original/generator-species-id');
    }
    need(extra.generator_metadata.length === (Object.hasOwn(set, 'role') ? 1 : 0)
      && extra.generator_metadata.every(key => key === 'role') && (!Object.hasOwn(set, 'role') || typeof set.role === 'string' && set.role.length > 0), 'native-original/generator-metadata');
    for (const field of ['species', 'ability', 'item', 'moves']) need(presence[field] === 'present' && Object.hasOwn(set, field), 'native-original/missing-required-field');
    need(typeof set.species === 'string' && set.species.length > 0 && typeof set.ability === 'string' && set.ability.length > 0
      && typeof set.item === 'string' && Array.isArray(set.moves) && set.moves.length >= 1 && set.moves.length <= 4
      && set.moves.every((move: unknown) => typeof move === 'string' && move.length > 0)
      && Array.from({length: set.moves.length}, (_, n) => n).every(n => Object.hasOwn(set.moves, n)), 'native-original/required-value');
    need(dex.species.get(set.species).exists === true && dex.abilities.get(set.ability).exists === true
      && (set.item === '' || dex.items.get(set.item).exists === true)
      && set.moves.every((move: string) => dex.moves.get(move).exists === true), 'native-original/unknown-submitted-value');
    const subject = owner + ':roster:' + (i + 1);
    fact(subject, 'roster_order', i + 1, 'integer'); fact(subject, 'roster_species', set.species, 'text');
    fact(subject, 'ability', set.ability, 'text'); fact(subject, 'item', set.item === '' ? null : set.item, 'text');
    fact(subject, 'starting_moves', [...set.moves], 'texts');
    if (loadout) for (const original of interpretOriginalValues(set, dex, require(runtime.entry)).facts) {
      const rule = rules.find((r: Record<string, any>) => r.context === 'starting' && r.property === original.property);
      need(rule, 'native-original/property');
      facts.push(freeze({ owner, subject, family: rule.family, property: original.property, effect_key: null,
        state: original.state, value: original.value === null ? null : { type: original.tag, data: original.value }, reason: original.reason,
        freshness: 'immutable', precision: original.state === 'known' ? 'exact' : 'not_applicable', observed_at: 0 }));
    }
  }
  return Object.freeze(facts);
}
