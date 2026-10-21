/** Fixed decoder selection only; no engine or source authority. */
export const HISTORICAL10_REVISION = 'sim-core@0.1.0+pokemon-showdown@0.11.10' as const;
// native11 now names pinned commit b8f23c99; the npm version alone is ambiguous.
export const NATIVE11_REVISION = 'sim-core@0.1.0+pokemon-showdown@0.11.11+b8f23c99' as const;
export const HISTORICAL10 = Object.freeze({ id: 'historical10', revision: HISTORICAL10_REVISION, adopted: true });
export const NATIVE11 = Object.freeze({ id: 'native11', revision: NATIVE11_REVISION, adopted: false });
export type ReaderSelection = 'historical10' | 'native11' | 'auto';
function fail(reason: string): never { throw new Error('reader-profile/v1/' + reason); }
const record = (v: unknown): v is Record<string, any> => !!v && typeof v === 'object' && !Array.isArray(v);
const bundles = new Set(['pipeline-linked-record/v1', 'pipeline-forced-switch-record/v1', 'pipeline-revival-record/v1']);
const envelopes = new Set(['pipeline-episode-evidence/v1', 'pipeline-episode-evidence/v2']);
/** Only recognized schema paths, including predecessor and compact sweep beliefs. */
export function recognizedReaderRevisions(value: unknown): readonly unknown[] {
  const revisions: unknown[] = [], active = new Set<object>();
  const revision = (v: unknown) => { if (record(v) && Object.hasOwn(v, 'simulator_revision')) revisions.push(v.simulator_revision); };
  const evidence = (v: unknown) => { if (record(v) && record(v.provenance) && v.provenance.kind === 'simulator_only_truth') revision(v.provenance); };
  const belief = (v: unknown) => {
    if (!record(v)) return;
    revision(v.transition_lineage);
    if (Array.isArray(v.transition_history)) v.transition_history.forEach(revision);
    if (Array.isArray(v.evidence)) v.evidence.forEach(evidence);
  };
  const actor = (v: unknown) => {
    if (!record(v)) return;
    revision(v.transition); belief(v.input_belief); belief(v.successor_belief);
  };
  const actors = (v: unknown) => { if (record(v)) for (const owner of ['p1', 'p2']) if (Array.isArray(v[owner])) v[owner].forEach(actor); };
  const visit = (v: unknown, depth = 0): void => {
    if (!record(v)) return;
    if (depth > 64 || active.has(v)) fail('invalid-predecessor-chain');
    active.add(v);
    if (bundles.has(v.schema_version)) actor(v);
    else if (envelopes.has(v.schema_version)) {
      if (Array.isArray(v.commits)) v.commits.forEach((c: unknown) => { if (record(c)) revision(c.transition); });
      if (v.schema_version === 'pipeline-episode-evidence/v2' && record(v.closure)) visit(v.closure.predecessor, depth + 1);
    } else if (v.schema_version === 'pipeline-episode/v1') { actors(v.records); visit(v.evidence_envelope, depth); }
    else if (v.schema_version === 'pipeline-episode-publication-sweep/v1') {
      actors(v.records); visit(v.evidence_envelope, depth);
      if (Array.isArray(v.beliefs)) v.beliefs.forEach((b: unknown) => { if (record(b)) { belief(b.fields); if (record(b.arrays)) {
        if (record(b.arrays.transition_history) && Array.isArray(b.arrays.transition_history.items)) b.arrays.transition_history.items.forEach(revision);
        if (record(b.arrays.evidence) && Array.isArray(b.arrays.evidence.items)) b.arrays.evidence.items.forEach(evidence);
      } } });
    }
    active.delete(v);
  };
  visit(value); return Object.freeze(revisions);
}
export function selectReaderProfile(value: unknown, selection: ReaderSelection = 'auto'): typeof HISTORICAL10 | typeof NATIVE11 {
  if (!['historical10','native11','auto'].includes(selection)) fail('unknown-profile');
  const revisions = recognizedReaderRevisions(value);
  if (revisions.some(r => typeof r !== 'string')) fail('unknown-revision');
  const distinct = new Set(revisions);
  if (distinct.size > 1) fail('conflicting-revisions');
  if (!distinct.size && selection === 'auto') fail('ambiguous-revision');
  const target = selection === 'native11' || selection === 'auto' && distinct.has(NATIVE11_REVISION);
  if (distinct.size && !distinct.has(target ? NATIVE11_REVISION : HISTORICAL10_REVISION)) fail('unknown-revision');
  if (target) readerContext(NATIVE11_CONTEXT);
  return target ? NATIVE11 : HISTORICAL10;
}
export function assertHistoricalReaderInput(value: unknown): void { selectReaderProfile(value, 'historical10'); }


import fs from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import type { ProtocolContract } from './protocol_contract';
/** Fixed semantic assets; no engine/source authority and no caller asset injection. */
export interface ReaderContext {
  readonly profile: typeof HISTORICAL10 | typeof REPLAY_COMPAT | typeof NATIVE11;
  readonly protocol: ProtocolContract;
  readonly inventory: any;
  readonly effects: Readonly<Record<string, any>>;
  readonly lifecycle: Readonly<Record<string, any>>;
}
function freezeTree<T>(value: T): T {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freezeTree); Object.freeze(value);
  }
  return value;
}
function projectRoot(): string {
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth++) {
    if (fs.existsSync(path.join(directory, 'sim-core/package.json'))) return directory;
    const parent = path.dirname(directory); if (parent === directory) break; directory = parent;
  }
  return fail('missing-historical-assets');
}
const root = projectRoot();
const protocol = JSON.parse(fs.readFileSync(path.join(root, 'trainer/src/neural/protocol_contract.json'), 'utf8'));
const inventory = JSON.parse(fs.readFileSync(path.join(root, 'sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json'), 'utf8'));
if (protocol.simulator.version !== '0.11.10' || inventory.simulator.version !== '0.11.10'
  || inventory.public_typed_state_lifecycle.schema_version !== 'public-typed-state-lifecycle/v1') fail('historical-asset-mismatch');
const effects: Record<string, any> = {};
for (const entry of [...inventory.condition_inventory, ...inventory.effect_discovery.additional_entries]) {
  if (effects[entry.id]) fail('duplicate-effect'); effects[entry.id] = entry;
}
export const HISTORICAL10_CONTEXT: ReaderContext = freezeTree({ profile: HISTORICAL10, protocol, inventory, effects,
  lifecycle: Object.fromEntries(inventory.public_typed_state_lifecycle.entries.map((e: any) => [`${e.family}:${e.id}`, e])) });
export function readerContext(context: unknown = HISTORICAL10_CONTEXT): ReaderContext {
  if (context === NATIVE11_CONTEXT) { ensureOwnedPreparedAssetValidated('native11', NATIVE11_GRAMMAR_CONTEXT); return NATIVE11_CONTEXT; }
  if (context !== HISTORICAL10_CONTEXT) fail((context as any)?.profile?.id === 'native11' ? 'native11-unadopted' : 'unsupported-context');
  return context as ReaderContext;
}
export function assertReaderInput(value: unknown, context: ReaderContext = HISTORICAL10_CONTEXT): void {
  assertPublicationReaderContext(context);
  selectReaderProfile(value, context === NATIVE11_CONTEXT ? 'native11' : 'historical10');
}
export interface NativeRuntimeProfile {
  readonly reader: ReaderContext;
  readonly package_version: '0.11.11';
  readonly engine_commit: typeof NATIVE_ENGINE_COMMIT;
  readonly package_root: string;
  readonly entry: string;
  readonly integrity: string;
}
export const NATIVE_ENGINE_COMMIT = 'b8f23c99629132611ba59e99480cb148ea8c5d3d' as const;
export const NATIVE_ENGINE_INTEGRITY = 'sha512-ihktUZgY1oy6U7TyCDmHg4lUlPeMb2jcedhqOnc/R0GIAeMgMFTlIDzmVsZ1xjBJ4ddaa/OM8dpfNsqo1dNe3Q==';
const NATIVE_ENGINE_MANIFEST_SHA256 = '806f1bf4edc35c7901902bfbc864ab1bebe6d1254b761808833a7a32b1e37ec6';
const NATIVE_ENGINE_DEPENDENCY = 'file:../vendor/pokemon-showdown-b8f23c99.tgz';
const ownedRuntimes = new WeakSet<object>();
/** Internal producer initialization: checked real installed path, declarations and both lock entries. */
export function installedNativeProfile(): NativeRuntimeProfile {
  const entry = fs.realpathSync(require.resolve('pokemon-showdown'));
  const packagePath = fs.realpathSync(require.resolve('pokemon-showdown/package.json'));
  const packageRoot = path.dirname(packagePath);
  const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  const declaration = JSON.parse(fs.readFileSync(path.join(root, 'sim-core/package.json'), 'utf8'));
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'sim-core/package-lock.json'), 'utf8'));
  const installedLock = JSON.parse(fs.readFileSync(path.join(root, 'sim-core/node_modules/.package-lock.json'), 'utf8'));
  const locked = lock.packages['node_modules/pokemon-showdown'], installed = installedLock.packages['node_modules/pokemon-showdown'];
  const expectedIntegrity = NATIVE_ENGINE_INTEGRITY;
  if (pkg.version !== '0.11.11' || pkg.engine_commit !== NATIVE_ENGINE_COMMIT || declaration.dependencies['pokemon-showdown'] !== NATIVE_ENGINE_DEPENDENCY
    || lock.packages[''].dependencies['pokemon-showdown'] !== NATIVE_ENGINE_DEPENDENCY || locked?.version !== pkg.version
    || locked?.resolved !== NATIVE_ENGINE_DEPENDENCY || installed?.resolved !== NATIVE_ENGINE_DEPENDENCY
    || installed?.version !== pkg.version || locked.integrity !== expectedIntegrity || installed.integrity !== expectedIntegrity
    || entry !== fs.realpathSync(path.join(packageRoot, pkg.main))
    || packageRoot !== fs.realpathSync(path.join(root, 'sim-core/node_modules/pokemon-showdown'))) fail('installed-runtime-mismatch');
  // Locks describe the install intent. Check every installed byte and the exact file set too.
  const manifest = pinnedAsset(path.join(packageRoot, 'engine-files.json'), NATIVE_ENGINE_MANIFEST_SHA256);
  if (manifest.engine_commit !== NATIVE_ENGINE_COMMIT) fail('installed-runtime-mismatch');
  const files: string[] = [];
  const walk = (dir: string): void => {
    for (const name of fs.readdirSync(path.join(packageRoot, dir))) {
      const relative = dir ? dir + '/' + name : name;
      const stat = fs.lstatSync(path.join(packageRoot, relative));
      if (stat.isSymbolicLink()) fail('installed-runtime-content');
      if (stat.isDirectory()) walk(relative); else files.push(relative);
    }
  };
  walk('');
  if (JSON.stringify(files.filter(name => name !== 'engine-files.json').sort()) !== JSON.stringify(Object.keys(manifest.files).sort())) fail('installed-runtime-content');
  for (const [name, expected] of Object.entries(manifest.files)) {
    if (createHash('sha256').update(fs.readFileSync(path.join(packageRoot, name))).digest('hex') !== expected) fail('installed-runtime-content');
  }
  if ('sha512-' + createHash('sha512').update(fs.readFileSync(path.join(root, 'vendor/pokemon-showdown-b8f23c99.tgz'))).digest('base64') !== expectedIntegrity) fail('installed-runtime-integrity');
  const runtime = Object.freeze({ engine_commit: NATIVE_ENGINE_COMMIT, reader: readerContext(NATIVE11_CONTEXT), package_version: '0.11.11' as const,
    package_root: packageRoot, entry, integrity: expectedIntegrity });
  ownedRuntimes.add(runtime); return runtime;
}
export function assertNativeRuntimeProfile(runtime: NativeRuntimeProfile): void {
  if (!ownedRuntimes.has(runtime)) fail('unowned-runtime-profile');
  readerContext(runtime.reader);
}
/** Pinned old normalizer. Pure syntax, equivalent to verified old Dex.toID; no native engine import. */
export function historicalToID(text: any): string {
  if (typeof text !== 'string') {
    if (text) text = text.id || text.userid || text.roomid || text;
    if (typeof text === 'number') text = `${text}`;
    else if (typeof text !== 'string') return '';
  }
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '');
}
const HISTORICAL_LOOKUP_SHA256 = '21250d247e77879d0f7135a12baeee0ffadc7e00c5456a71dd07c066cd06b921';
const INACTIVE_TARGET_INVENTORY_SHA256 = '3d5760e2cc189617499cb9ab7e505ecebfeb6a3a6175f7e854c13fc7ba32dab2';
function pinnedAsset(assetPath: string, expected: string): any {
  let bytes: Buffer;
  try { bytes = fs.readFileSync(assetPath); } catch { return fail('missing-version-asset'); }
  if (createHash('sha256').update(bytes).digest('hex') !== expected) fail('version-asset-integrity');
  return freezeTree(JSON.parse(bytes.toString('utf8')));
}
/** Fixed local replay decoder, not a native profile or portable publication contract. */
export const REPLAY_COMPAT = Object.freeze({id: 'replay-compat-v1', revision: 'importer-replay-compatibility/v1', adopted: false} as const);
export interface ProtocolRulesContext { readonly protocol: ProtocolContract; }
const targetProtocolAsset = pinnedAsset(path.join(root, 'trainer/src/neural/protocol_contract_b8f23c99.json'), '6b822f2fed433e507543f30dc71c3b26762d9ae674c86d2237ce202d03c9c802');
const replayProtocolAsset = pinnedAsset(path.join(root, 'trainer/src/neural/protocol_contract_replay_compat_v1.json'), 'e8e8dcee5aa9952749047c3e87d70a16da8c04f6e4f480a81568e4bcd9fe02f4');
export const NATIVE11_GRAMMAR_CONTEXT: ProtocolRulesContext = freezeTree({protocol: targetProtocolAsset.protocol});
export const REPLAY_COMPAT_CONTEXT: ReaderContext = freezeTree({...HISTORICAL10_CONTEXT, profile: REPLAY_COMPAT, protocol: replayProtocolAsset.protocol});
const targetInventory = pinnedAsset(path.join(root, 'sim-core/simulator_coverage/pokemon-showdown-b8f23c99-gen9randombattle.json'), 'fffced361d9b1a5be8c7cc0c073409b46a73ad852178ed62df89e29e9258e19b');
const targetEffects = Object.fromEntries([...targetInventory.condition_inventory, ...targetInventory.effect_discovery.additional_entries].map((e: any) => [e.id, e]));
export const NATIVE11_CONTEXT: ReaderContext = freezeTree({profile: NATIVE11, protocol: targetProtocolAsset.protocol,
  inventory: targetInventory, effects: targetEffects,
  lifecycle: Object.fromEntries(targetInventory.public_typed_state_lifecycle.entries.map((e: any) => [`${e.family}:${e.id}`, e]))});

type PreparedValidationState = {phase: 'unvalidated' | 'checking' | 'validated' | 'failed'; error?: unknown};
const targetValidation: PreparedValidationState = {phase: 'unvalidated'}, replayValidation: PreparedValidationState = {phase: 'unvalidated'};
let checkingOwnedContext: ProtocolRulesContext | undefined;
/** Only fixed frozen JSON enters this synchronous self-check; caller data never changes this state. */
function ensureOwnedPreparedAssetValidated(profile: 'native11' | 'replay-compat-v1', context: ProtocolRulesContext): void {
  const ownedContext = profile === 'native11' ? NATIVE11_GRAMMAR_CONTEXT : REPLAY_COMPAT_CONTEXT;
  if (context !== ownedContext || checkingOwnedContext && checkingOwnedContext !== context) fail('prepared-validation-context');
  const state = profile === 'native11' ? targetValidation : replayValidation;
  if (state.phase === 'failed') throw state.error;
  if (state.phase === 'validated' || state.phase === 'checking') return;
  const asset = profile === 'native11' ? targetProtocolAsset : replayProtocolAsset;
  const validator = require('./prepared_protocol_contract') as typeof import('./prepared_protocol_contract');
  try {
    validator.validatePreparedProtocolStructure(asset, profile);
    state.phase = 'checking'; checkingOwnedContext = context;
    validator.checkPreparedProtocolRecords(asset, profile);
    state.phase = 'validated';
  } catch (error) { state.phase = 'failed'; state.error = error; throw error; }
  finally { checkingOwnedContext = undefined; }
}
/** Internal validation stages cannot lend the owned bootstrap to inspection data. */
export function assertPreparedInspectionAvailable(): void { if (checkingOwnedContext) fail('prepared-validation-context'); }
export function assertPreparedRecordCheckInput(value: unknown, profile: 'native11' | 'replay-compat-v1'): void {
  if (!checkingOwnedContext) return;
  const context = profile === 'native11' ? NATIVE11_GRAMMAR_CONTEXT : REPLAY_COMPAT_CONTEXT;
  const asset = profile === 'native11' ? targetProtocolAsset : replayProtocolAsset;
  if (context !== checkingOwnedContext || value !== asset) fail('prepared-validation-context');
}
/** PRE grammar only; never accepted as a native reader/runtime context. */
export function protocolContext(context: unknown = HISTORICAL10_CONTEXT): ProtocolRulesContext {
  if (context === NATIVE11_GRAMMAR_CONTEXT) { ensureOwnedPreparedAssetValidated('native11', NATIVE11_GRAMMAR_CONTEXT); return NATIVE11_GRAMMAR_CONTEXT; }
  return helperContext(context);
}
/** Local importer semantics only; pipeline readers still require readerContext. */
export function helperContext(context: unknown = HISTORICAL10_CONTEXT): ReaderContext {
  if (context === REPLAY_COMPAT_CONTEXT) { ensureOwnedPreparedAssetValidated('replay-compat-v1', REPLAY_COMPAT_CONTEXT); return REPLAY_COMPAT_CONTEXT; }
  return readerContext(context);
}
/** Narrow quarantine for changed families lacking a safe semantic consequence proof. */
export function assertPreparedProtocolPolicy(record: string, context: unknown): void {
  protocolContext(context);
  if (context !== NATIVE11_GRAMMAR_CONTEXT && context !== NATIVE11_CONTEXT && context !== REPLAY_COMPAT_CONTEXT) return;
  const p = record.split('|'), command = p[1];
  const stableLeftovers = command === '-heal' && p.length === 5 && p[4] === '[from] item: Leftovers';
  const revival = (context === NATIVE11_CONTEXT || context === NATIVE11_GRAMMAR_CONTEXT) && command === '-heal' && p.includes('[from] move: Revival Blessing');
  const family = context === REPLAY_COMPAT_CONTEXT && ['-heal', 'heal', 'cant'].includes(command) && !stableLeftovers && !revival ? 'heal-failure'
    : ['-swapsideconditions', 'swapsideconditions'].includes(command) || (command === '-activate' && p[3] === 'move: Court Change') ? 'court-change'
    : context === REPLAY_COMPAT_CONTEXT && command === '-prepare' && p[3] === 'Chilly Reception' ? 'chilly-reception'
    : context === REPLAY_COMPAT_CONTEXT && command === '-damage' && p.includes('[partiallytrapped]') ? 'partial-trap'
    : ['-item', 'item'].includes(command) && p.includes('[from] ability: Magician') ? 'magician'
    : command === '-activate' && ['ability: Mummy', 'ability: Lingering Aroma'].includes(p[3]) ? 'ability-setter'
    : command === '-ability' && p.length > 5 && !p.includes('[from] ability: Trace') ? 'ability-setter' : null;
  if (family) fail('prepared-family-unsupported/' + family);
}
export function replayReaderContext(profile: unknown): ReaderContext {
  if (profile === 'historical10') return HISTORICAL10_CONTEXT;
  if (profile === 'replay-compat-v1') return helperContext(REPLAY_COMPAT_CONTEXT);
  return fail(profile === 'native11' ? 'native11-unadopted' : 'explicit-replay-profile-required');
}
export function assertPublicationReaderContext(context: unknown): void {
  if (context === REPLAY_COMPAT_CONTEXT) fail('replay-publication-unsupported');
  readerContext(context);
}
/** Asset inspection seam: trusted hashes remain code-owned even for an alternate path. */
export function loadPreparedProtocolAsset(profile: 'native11' | 'replay-compat-v1', assetPath?: string): any {
  const validate = (asset: any, selected: 'native11' | 'replay-compat-v1') => require('./prepared_protocol_contract').validatePreparedProtocolAsset(asset, selected);
  if (profile === 'native11') return validate(pinnedAsset(assetPath ?? path.join(root, 'trainer/src/neural/protocol_contract_b8f23c99.json'), '6b822f2fed433e507543f30dc71c3b26762d9ae674c86d2237ce202d03c9c802'), profile);
  if (profile === 'replay-compat-v1') return validate(pinnedAsset(assetPath ?? path.join(root, 'trainer/src/neural/protocol_contract_replay_compat_v1.json'), 'e8e8dcee5aa9952749047c3e87d70a16da8c04f6e4f480a81568e4bcd9fe02f4'), profile);
  return fail('unknown-grammar-profile');
}

let historicalData: any;
export function historicalLookupData(): any {
  if (!historicalData) historicalData = pinnedAsset(path.join(root, 'sim-core/simulator_coverage/lookups/pokemon-showdown-0.11.10.json'), HISTORICAL_LOOKUP_SHA256).data;
  return historicalData;
}
/** Inspection only; never returns an adopted context or runtime profile. */
export function loadInactiveTargetInventory(assetPath = path.join(root, 'sim-core/simulator_coverage/pokemon-showdown-0.11.11-gen9randombattle.json')): any {
  const candidate = pinnedAsset(assetPath, INACTIVE_TARGET_INVENTORY_SHA256);
  if (candidate.manifest_schema !== 'simulator-coverage-candidate/v1' || candidate.adopted !== false
    || candidate.review_status !== 'candidate-inactive' || candidate.simulator.version !== '0.11.11'
    || candidate.runtime_evidence !== 'UNEXECUTED'
    || candidate.public_ability_effectiveness?.schema_version !== 'public-ability-effectiveness/v1'
    || candidate.public_ability_effectiveness?.adopted !== false
    || candidate.effect_discovery?.package_wide_dynamic_callback_closure !== false
    || candidate.public_typed_state_lifecycle?.prior_projection_only !== true) fail('invalid-inactive-inventory');
  return candidate;
}
let nativeData: any;
let targetData: any;
const TARGET_LOOKUP_SHA256 = 'a5ab25417c4c7de524caec386ed8cb54eb2f023708cc4b0405358dac4b5880d9';
/** Compatibility API name; immutable historical tables, independent of installed native engine. */
export function runtimeData(context: ReaderContext = HISTORICAL10_CONTEXT): any {
  helperContext(context);
  if (context === NATIVE11_CONTEXT) {
  if (!targetData) {
    const {species, moves, types, aliases} = pinnedAsset(path.join(root, 'sim-core/simulator_coverage/lookups/pokemon-showdown-b8f23c99.json'), TARGET_LOOKUP_SHA256).data;
    const toID = historicalToID;
    const missingSpecies = Object.freeze({exists: false, types: Object.freeze([])}), missingMove = Object.freeze({exists: false});
    const id = (value: any) => { const key = toID(value); return toID(aliases[key] || key); };
    targetData = freezeTree({species: {get: (v: any) => species[id(v)] || missingSpecies},
      moves: {get: (v: any) => moves[id(v)] || missingMove},
      getImmunity: (attack: string, defenders: string[]) => defenders.every(d => types[toID(d)]?.damageTaken[attack] !== 3),
      getEffectiveness: (attack: string, defenders: string[]) => defenders.reduce((n, d) => n + (types[toID(d)]?.damageTaken[attack] === 1 ? 1 : types[toID(d)]?.damageTaken[attack] === 2 ? -1 : 0), 0)});
  }
    return targetData;
  }
  if (!nativeData) {
    const {species, moves, types, aliases} = historicalLookupData();
    const toID = historicalToID;
    const missingSpecies = Object.freeze({exists: false, types: Object.freeze([])}), missingMove = Object.freeze({exists: false});
    const id = (value: any) => { const key = toID(value); return toID(aliases[key] || key); };
    nativeData = freezeTree({species: {get: (v: any) => species[id(v)] || missingSpecies},
      moves: {get: (v: any) => moves[id(v)] || missingMove},
      getImmunity: (attack: string, defenders: string[]) => defenders.every(d => types[toID(d)]?.damageTaken[attack] !== 3),
      getEffectiveness: (attack: string, defenders: string[]) => defenders.reduce((n, d) => n + (types[toID(d)]?.damageTaken[attack] === 1 ? 1 : types[toID(d)]?.damageTaken[attack] === 2 ? -1 : 0), 0)});
  }
  return nativeData;
}

/** Local reviewed capture policy only; caller data/digests never create positive eligibility. */
export function positiveFidelityScope(profile: string, ruleset: string): boolean {
  if (profile === 'historical10') return ruleset === 'gen9randombattle';
  if (profile === 'native11') return false;
  return fail('unknown-fidelity-profile');
}
export function assertPositiveFidelityClaim(profile: string, ruleset: string, claimed: boolean): void {
  if (claimed && !positiveFidelityScope(profile, ruleset)) throw new Error('fidelity-policy/v1/positive-unaccepted');
}
export function historicalKnowledgeSourceScope(packageVersion: string): boolean {
  if (packageVersion === '0.11.10') return true;
  if (packageVersion === '0.11.11') return false;
  return fail('unknown-source-runtime');
}
/** Fail-only entry gate. Decoder selection and held B1/B2 data cannot select this runtime. */
export function guardHistoricalKnowledgeSource(): void {
  if (!historicalKnowledgeSourceScope(installedNativeProfile().package_version)) throw new Error('k-source-policy/v1/historical-origin-quarantined');
}


/** Existing finite result metadata rules; called only after target evidence validation. */
export function assertTargetEpisodeStatus(status: unknown, stop: unknown, terminal: boolean): void {
  const codes: Readonly<Record<string, string>> = Object.freeze({terminal: 'completed',
    ...Object.fromEntries(['transition-budget','attempt-budget','rejection-limit','action-exhausted','cancelled','unsupported-format',
      'unsupported-boundary','unsupported-revival-blessing','unsupported-protocol'].map(code => [code, 'truncated'])),
    ...Object.fromEntries(['invalid-options','execution-failed','settling-failed','cleanup-failed','evidence-invalid'].map(code => [code, 'failed']))});
  if (!record(stop) || typeof stop.code !== 'string' || typeof stop.reason !== 'string'
    || !stop.code.startsWith('episode/v1/') || codes[stop.code.slice('episode/v1/'.length)] !== status
    || !['completed','truncated','failed'].includes(String(status))
    || (status === 'completed') !== (stop.code === 'episode/v1/terminal')
    || status === 'completed' && !terminal || status === 'truncated' && terminal) throw new Error('fidelity-policy/v1/episode-status');
}
