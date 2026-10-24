import { declaredRequestValues, DECLARED_PROPERTIES } from './owned_request_values';
/** Opt-in knowledge wire structure checks; no source truth or publication. */
import { interpretOriginalValues, ORIGINAL_FIELDS, ORIGINAL_STATS } from './original_owner_values';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { TextDecoder } from 'node:util';

type Row = Record<string, any>;
const MAX_BYTES = 16 * 1024 * 1024;
const MAX_DEPTH = 32;
const MAX_INTEGER = 2147483647;
const CONTRACT_HASHES: Record<string, string> = {
  'schema.json': '5e555304407609cc2f717a083dfe7213a4a53a911a0b65a17992e29fbd26acce',
  'profiles.json': '4311d5c78136ad5ffa43eaed07b38c1ae5f60de6495a3ebb75a94ef30bff48e2',
  'property-types.json': '85c7b3f94a69dad7b5105d475cc62681ab1e591bf2f8cdf9c43ee3f11ee86537',
  'property-contexts.json': '3cd45e33eda64255e7cc9e8dd9f8b9208fe2b28ddfdbbcc1b6df143cbb2fbbfe',
  'typed-references.json': 'eb8809992e2cdd4033287bf319a4dd126c94d73e07c99a4552f695c59d06c7da',
};
const KINDS = ['origin','source','prefix','evidence','certificate','fact','starting','current',
  'request','knowledge','profile','verdict','boundary','binding','audit','projection'];

export class KnowledgeStructureError extends Error {}
function requireStructure(condition: unknown, code: string): asserts condition {
  if (!condition) throw new KnowledgeStructureError(code);
}
function scalar(value: string): boolean {
  for (const char of value) {
    const n = char.codePointAt(0)!;
    if (n >= 0xd800 && n <= 0xdfff) return false;
  }
  return true;
}

function parse(data: Uint8Array | string, raw = false): unknown {
  requireStructure(typeof data === 'string' || data instanceof Uint8Array, 'json input type');
  let text: string;
  try { text = typeof data === 'string' ? data : new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(data); }
  catch { throw new KnowledgeStructureError('invalid JSON/UTF-8'); }
  requireStructure(Buffer.byteLength(text, 'utf8') <= MAX_BYTES, 'wire size');
  requireStructure(text[0] !== '\ufeff', 'json BOM');
  let at = 0;
  const space = () => { while (at < text.length && /[ \t\r\n]/.test(text[at])) at++; };
  function string(): string {
    const start = at++;
    let escaped = false;
    while (at < text.length) {
      const char = text[at++];
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') {
        try { return JSON.parse(text.slice(start, at)) as string; }
        catch { throw new KnowledgeStructureError('invalid JSON/UTF-8'); }
      }
    }
    throw new KnowledgeStructureError('invalid JSON/UTF-8');
  }
  function item(depth: number): unknown {
    requireStructure(depth <= MAX_DEPTH, 'depth'); space();
    const char = text[at];
    if (char === '"') return string();
    if (char === '[' || char === '{') {
      requireStructure(depth < MAX_DEPTH, 'depth');
      at++; space();
      const close = char === '[' ? ']' : '}';
      const array: unknown[] = []; const object: Row = {};
      const keys = new Set<string>();
      if (text[at] === close) { at++; return char === '[' ? array : object; }
      for (;;) {
        if (char === '[') array.push(item(depth + 1));
        else {
          requireStructure(text[at] === '"', 'invalid JSON/UTF-8');
          const key = string(); requireStructure(!keys.has(key), 'duplicate JSON key'); keys.add(key);
          space(); requireStructure(text[at++] === ':', 'invalid JSON/UTF-8');
          Object.defineProperty(object, key, { value: item(depth + 1), enumerable: true, configurable: true, writable: true });
        }
        requireStructure(char === '[' ? array.length <= 4096 : keys.size <= 4096, 'container bound');
        space();
        if (text[at] === close) { at++; return char === '[' ? array : object; }
        requireStructure(text[at++] === ',', 'invalid JSON/UTF-8'); space();
      }
    }
    for (const [lexeme, value] of [['true',true],['false',false],['null',null]] as const) {
      if (text.startsWith(lexeme,at)) { at += lexeme.length; return value; }
    }
    const match = /^-?(?:0|[1-9][0-9]*)/.exec(text.slice(at));
    requireStructure(match, 'invalid JSON/UTF-8');
    const lexeme = match[0]; at += lexeme.length;
    requireStructure(lexeme !== '-0' && !/[.eE]/.test(text[at] ?? ''), 'numeric lexeme');
    const value = Number(lexeme);
    requireStructure(Number.isInteger(value) && value >= -6 && value <= MAX_INTEGER, 'integer range');
    return value;
  }
  const value = item(0); space(); requireStructure(at === text.length, 'invalid JSON/UTF-8');
  canonical(value,raw); return value;
}

export function parseKnowledgeJson(data: Uint8Array | string): unknown { return parse(data); }

function canonical(value: unknown, raw = false): Buffer {
  const chunks: Buffer[] = []; let size = 0; const active = new Set<object>();
  function emit(text: string) {
    const block = Buffer.from(text,'utf8'); size += block.length;
    requireStructure(size <= MAX_BYTES,'wire size'); chunks.push(block);
  }
  function visit(item: unknown, depth: number, parts: string[]) {
    requireStructure(depth <= MAX_DEPTH,'depth');
    if (item === null) emit('null');
    else if (typeof item === 'boolean') emit(item ? 'true' : 'false');
    else if (typeof item === 'number') {
      requireStructure(Number.isInteger(item) && !Object.is(item,-0) && item >= -6 && item <= MAX_INTEGER,'integer range');
      emit(String(item));
    } else if (typeof item === 'string') {
      const special = !raw && parts.length >= 2 && parts.at(-2) === 'raw_request' && parts.at(-1) === 'json';
      requireStructure([...item].length <= (raw || special ? 65536 : 256),'string length');
      requireStructure(scalar(item),'surrogate');
      if (special) parse(item,true);
      emit(JSON.stringify(item));
    } else {
      requireStructure(typeof item === 'object' && item !== null,'JSON object type');
      requireStructure(depth < MAX_DEPTH,'depth');
      requireStructure(!active.has(item),'object cycle');
      const proto = Object.getPrototypeOf(item);
      requireStructure(Array.isArray(item) ? proto === Array.prototype : proto === Object.prototype || proto === null,'JSON object type');
      requireStructure(Object.getOwnPropertySymbols(item).length === 0,'object keys');
      const descriptors = Object.getOwnPropertyDescriptors(item);
      requireStructure(Object.values(descriptors).every(d => 'value' in d),'JSON object type');
      active.add(item);
      if (Array.isArray(item)) {
        requireStructure(item.length <= 4096 && Object.getOwnPropertyNames(item).length === item.length + 1,'container bound');
        emit('[');
        for (let index = 0; index < item.length; index++) {
          const descriptor = descriptors[String(index)];
          requireStructure(descriptor && descriptor.enumerable && 'value' in descriptor,'JSON array type');
          if (index) emit(','); visit(descriptor.value,depth+1,[...parts,'*']);
        }
        emit(']');
      } else {
        const keys = Object.keys(item).sort();
        requireStructure(keys.length <= 4096 && Object.getOwnPropertyNames(item).length === keys.length,'container bound');
        emit('{');
        keys.forEach((key,index) => {
          requireStructure([...key].length <= 256 && scalar(key) && (raw || /^[\x00-\x7f]*$/.test(key)),'object keys');
          if (index) emit(','); emit(JSON.stringify(key)); emit(':'); visit((item as Row)[key],depth+1,[...parts,key]);
        }); emit('}');
      }
      active.delete(item);
    }
  }
  visit(value,0,[]); return Buffer.concat(chunks);
}
export function canonicalKnowledgeJson(value: unknown): Buffer { return canonical(value); }
export function knowledgeIdentity(value: Row): string {
  canonicalKnowledgeJson(value);
  requireStructure(value && KINDS.includes(value.kind),'identity kind');
  const payload = Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'id'));
  return 'sha256:' + createHash('sha256').update('pk/v1/' + value.kind + '\n','ascii').update(canonicalKnowledgeJson(payload)).digest('hex');
}

let frozenContract: Row | undefined;
function contract(): Row {
  if (frozenContract) return frozenContract;
  // Source and compiled module locations are explicit; never search cwd.
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist','src')) ? '../../..' : '../..', 'docs/contracts/fixtures/perspective-knowledge-v1');
  const data: Row = {};
  for (const [name,expected] of Object.entries(CONTRACT_HASHES)) {
    let bytes: Buffer;
    try { bytes = readFileSync(path.join(folder,name)); } catch { throw new KnowledgeStructureError('contract unavailable'); }
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected,'contract content');
    data[name] = JSON.parse(bytes.toString('utf8'));
  }
  frozenContract = data; return data;
}

function equal(a: unknown,b: unknown): boolean { return canonicalKnowledgeJson(a).equals(canonicalKnowledgeJson(b)); }
function shape(value: any,schema: Row,defs: Row): void {
  if (schema.$ref) return shape(value,defs[schema.$ref.split('/').at(-1)],defs);
  if (schema.anyOf) {
    for (const choice of schema.anyOf) { try { shape(value,choice,defs); return; } catch (error) { if (!(error instanceof KnowledgeStructureError)) throw error; } }
    throw new KnowledgeStructureError('schema union');
  }
  if ('const' in schema) requireStructure(value === schema.const,'schema const');
  if (schema.enum) requireStructure(schema.enum.includes(value),'schema enum');
  switch (schema.type) {
    case 'null': requireStructure(value === null,'schema null'); break;
    case 'boolean': requireStructure(typeof value === 'boolean','schema boolean'); break;
    case 'integer': requireStructure(typeof value === 'number' && Number.isInteger(value) && value >= (schema.minimum ?? 0) && value <= (schema.maximum ?? MAX_INTEGER),'schema integer'); break;
    case 'string':
      requireStructure(typeof value === 'string' && [...value].length <= (schema.maxLength ?? 256),'schema string');
      if (schema.pattern) { const match = new RegExp(schema.pattern).exec(value); requireStructure(match && match[0] === value,'schema pattern'); } break;
    case 'array':
      requireStructure(Array.isArray(value) && value.length <= schema.maxItems,'schema array');
      for (const entry of value) shape(entry,schema.items,defs); break;
    case 'object':
      requireStructure(typeof value === 'object' && value !== null && !Array.isArray(value),'schema object');
      if (schema.additionalProperties === false) {
        requireStructure(Object.keys(value).length === schema.required.length && schema.required.every((k: string) => Object.hasOwn(value,k)),'schema keys');
        for (const [key,entry] of Object.entries(value)) shape(entry,schema.properties[key],defs);
      } else {
        requireStructure(Object.keys(value).length <= schema.maxProperties,'schema dictionary');
        for (const [key,entry] of Object.entries(value)) { shape(key,schema.propertyNames,defs); shape(entry,schema.additionalProperties,defs); }
      } break;
  }
}

function edges(row: Row,refs: Row): [string,string][] {
  const result: [string,string][] = [];
  function descend(value: any,parts: string[],kind: string) {
    if (!parts.length) { if (value !== null) result.push([value,kind]); }
    else if (parts[0] === '*') for (const item of value) descend(item,parts.slice(1),kind);
    else descend(value[parts[0]],parts.slice(1),kind);
  }
  for (const [field,kind] of Object.entries(refs[row.kind])) descend(row,field.split('.'),kind as string);
  return result;
}
function ordered(values: (string | number)[],code: string) {
  const sorted = [...new Set(values)].sort((a,b) => typeof a === 'number' && typeof b === 'number' ? a-b : a < b ? -1 : a > b ? 1 : 0);
  requireStructure(equal(values,sorted),code);
}
function applies(fact: Row,context: string,rules: Row): boolean {
  const own = fact.subject.startsWith(fact.owner + ':'); const tail = fact.subject.slice(3);
  for (const rule of rules[fact.property]) {
    if (rule.context !== context || rule.scope !== 'both' && (rule.scope === 'owner') !== own) continue;
    const selector = rule.subject; const key = fact.effect_key;
    const roster = (tail.startsWith('roster:') || tail.startsWith('appearance:')) && !tail.includes(':move:');
    if (selector === 'side' && tail === 'side' && key === null) return true;
    if (selector === 'roster' && tail.startsWith('roster:') && !tail.includes(':move:') && key === null) return true;
    if (selector === 'roster_or_appearance' && roster && key === null) return true;
    if (selector === 'move' && tail.includes(':move:') && key === null) return true;
    if (['side','roster','roster_or_appearance','move'].includes(selector)) continue;
    if (key === null && (selector === 'field_effect' || fact.state === 'known')) continue;
    if (['persistent_effect_member','single_turn_effect_member','single_move_effect_member'].includes(selector)) { if (roster) return true; }
    else if (tail === 'side') return true;
  }
  return false;
}
function factShape(fact: Row,c: Row,properties: Row,proofs = true) {
  requireStructure(properties[fact.family].includes(fact.property),'family property');
  if (fact.state === 'known') {
    requireStructure(fact.value !== null && c['property-types.json'][fact.property].includes(fact.value.type),'property value tag');
    requireStructure(fact.reason === 'none' && (!proofs || fact.evidence.length) && fact.precision !== 'not_applicable','known fact shape');
  } else {
    requireStructure(fact.value === null,'nonknown value');
    if (fact.state === 'unknown') {
      requireStructure(fact.reason !== 'none' && fact.precision === 'not_applicable','unknown shape');
      requireStructure(fact.reason !== 'hidden_opponent' || !fact.subject.startsWith(fact.owner + ':'),'unknown owner scope');
    }
    else requireStructure((!proofs || fact.evidence.length) && fact.reason === (fact.state === 'known_absent' ? 'none' : 'proved_rule_inapplicable'),'nonknown proof shape');
  }
  if (proofs) ordered(fact.evidence,'fact proof order');
  const value = fact.value, key = fact.effect_key, prop = fact.property;
  const effect = c['property-types.json'][prop].includes('effect');
  const named = ['side_condition_layers','pending_power','field_remaining','weather','weather_effective','terrain'].includes(prop);
  requireStructure(effect || named || key === null,'effect key scope');
  if (value !== null) {
    const tag = value.type, data = value.data;
    if (tag === 'interval') requireStructure(data.min <= data.max,'interval order');
    if (tag === 'effect') {
      requireStructure(key === data.name,'effect identity');
      if (data.remaining !== null) requireStructure(data.remaining.data.min <= data.remaining.data.max,'interval order');
    }
    if (prop === 'side_condition_layers') requireStructure(['Spikes','ToxicSpikes'].includes(key) && data >= 1 && data <= (key === 'Spikes' ? 3 : 2),'layer bounds');
    if (effect || named) requireStructure(key !== null,'named effect');
  }
  if (prop === 'field_remaining') {
    requireStructure(key !== null,'timer target');
    if (value !== null) {
      const data = value.data; requireStructure(key === data.target_kind + ':' + data.name,'timer target');
      requireStructure(data.remaining.min <= data.remaining.max,'interval order');
    }
  }
}
function diagnostic() {
  return { structure_valid: true, source_semantics_verified: false, completeness: 'not_established', legacy_envelope_verified: false } as const;
}
function logicalFacts(facts: Row[]) {
  const keys = facts.map(f => JSON.stringify([f.owner,f.subject,f.family,f.property,f.effect_key]));
  requireStructure(new Set(keys).size === keys.length,'logical fact conflict');
  for (const f of facts) if (f.effect_key === null && f.state === 'known_absent') requireStructure(!facts.some(g => g.subject === f.subject && g.property === f.property && g.effect_key !== null && g.state === 'known'),'collection absence conflict');
}
function originalCertificate(cert: Row) {
  requireStructure(cert.continuity === 'original_unmodified' && equal(cert.exclusions,['acquisition','called','copy','identity_ambiguity','transfer','transform']),'original certificate qualification');
}

/** Frozen structure/identity/joins only, never a trusted receipt or source registry. */
export function checkKnowledgeStructure(input: unknown,requiredProfile?: string): ReturnType<typeof diagnostic> {
  canonicalKnowledgeJson(input);
  const c = contract(), schema = c['schema.json']; shape(input,schema,schema.$defs);
  const value = input as Row;
  requireStructure(value.id === knowledgeIdentity(value),'root identity');
  const profile = c['profiles.json'].find((p: Row) => p.id === value.required_profile);
  requireStructure(profile,'profile manifest');
  if (requiredProfile !== undefined) requireStructure(value.required_profile === requiredProfile,'required profile');
  const properties = Object.fromEntries(profile.obligations.map((r: Row) => [r.family,r.properties]));
  const rules = c['property-contexts.json'];
  if (value.kind === 'projection') {
    requireStructure(value.policy === profile.policy,'projection policy');
    for (const context of ['starting','current']) {
      logicalFacts(value[context]);
      for (const fact of value[context]) {
        factShape(fact,c,properties,false);
        requireStructure(fact.owner === value.owner,'projection owner');
        requireStructure(applies(fact,context === 'starting' ? 'original' : 'current',rules),'property context');
        requireStructure((fact.freshness === 'immutable') === (context === 'starting'),'projection freshness');
      }
    }
    ordered(value.starting_crosswalk.map((r: Row) => r.appearance),'crosswalk order');
    for (const row of value.starting_crosswalk) requireStructure(row.appearance.startsWith(value.owner + ':') && row.roster.startsWith(value.owner + ':'),'crosswalk owner');
    if (value.policy === 'public-replay-owner-starting/v1') requireStructure(value.request === null,'replay request');
    if (value.request !== null) {
      logicalFacts(value.request.facts);
      for (const fact of value.request.facts) {
        factShape(fact,c,properties,false);
        requireStructure(fact.owner === value.owner && applies(fact,'request',rules),'request owner/context');
        requireStructure(fact.freshness === 'current' && (fact.observed_at === value.request.cursor || fact.state === 'unknown' && fact.observed_at === null),'projection request time/freshness');
      }
    }
    return diagnostic();
  }
  const tables: Record<string,Row[]> = {};
  for (const [kind,entry] of Object.entries(value.tables)) {
    const rows = entry as any;
    if (value.form === 'compact') {
      requireStructure(!Array.isArray(rows) && Object.entries(rows).every(([key,row]) => key === (row as Row).id),'compact dictionary key');
      tables[kind] = (Object.values(rows) as Row[]).sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    } else { requireStructure(Array.isArray(rows),'array encoding'); tables[kind] = rows; }
  }
  const lookup = new Map<string,Row>();
  for (const [kind,rows] of Object.entries(tables)) {
    ordered(rows.map(r => r.id),'table duplicate/order');
    for (const row of rows) {
      requireStructure(row.kind === kind && row.id === knowledgeIdentity(row),'object identity');
      requireStructure(!lookup.has(row.id),'duplicate global ID'); lookup.set(row.id,row);
    }
  }
  const get = (ident: string,kind: string): Row => { const row = lookup.get(ident); requireStructure(row && row.kind === kind,'dangling/wrong reference'); return row; };
  const adjacency = new Map<string,string[]>();
  for (const row of lookup.values()) {
    const children: string[] = [];
    for (const [ident,kind] of edges(row,c['typed-references.json'].internal)) { get(ident,kind); children.push(ident); }
    adjacency.set(row.id,children);
  }
  const colors = new Map<string,number>();
  for (const ident of lookup.keys()) {
    const stack: [string,boolean][] = [[ident,false]];
    while (stack.length) {
      const [current,done] = stack.pop()!;
      if (done) { colors.set(current,2); continue; }
      requireStructure(colors.get(current) !== 1,'reference cycle');
      if (colors.get(current) === 2) continue;
      colors.set(current,1); stack.push([current,true]);
      for (const child of [...adjacency.get(current)!].reverse()) stack.push([child,false]);
    }
  }
  const origin = get(value.origin,'origin'); requireStructure(equal(get(value.required_profile,'profile'),profile),'profile manifest');
  for (const source of tables.source) {
    requireStructure(source.origin === origin.id,'source origin'); const st = source.source_type;
    if (['owner_initialization','owner_request'].includes(st)) {
      requireStructure(['p1','p2'].includes(source.owner) && source.provider === (st === 'owner_initialization' ? 'addressed-team-provider/v1' : 'addressed-request/v1'),'source addressing');
      requireStructure(source.delivery_seq !== null && source.delivery_cursor !== null,'source delivery');
      if (st === 'owner_initialization') requireStructure(source.phase === 'before_effects' && source.delivery_seq === 0 && source.delivery_cursor === 0 && source.team.length && source.raw_request === null,'original delivery');
      else requireStructure(source.phase === 'chronological' && source.raw_request !== null && !source.team.length,'request source shape');
    } else requireStructure(source.owner === null && source.provider === 'indexed-public/v1' && !source.team.length && source.raw_request === null && source.phase === 'chronological' && source.delivery_seq === null && source.delivery_cursor === null,'public source shape');
    requireStructure(source.team.every((s: Row,i: number) => s.slot === i+1),'team slot order');
  }
  for (const prefix of tables.prefix) requireStructure(prefix.origin === origin.id,'prefix origin');
  for (const proof of tables.evidence) {
    const source = get(proof.source,'source'); requireStructure(proof.origin === origin.id,'evidence origin');
    ordered(proof.record_indices,'record order'); requireStructure(proof.record_indices.every((i: number) => i < source.records.length),'record range');
    if (proof.scope === 'original') requireStructure(['owner_initialization','public_replay'].includes(source.source_type) && ['p1','p2'].includes(proof.owner) && proof.prefix === null && [null,proof.owner].includes(source.owner),'original source owner');
    else if (proof.scope === 'public') requireStructure(source.source_type === 'public_prefix' && proof.owner === null && equal(source.records,get(proof.prefix,'prefix').records),'public future traversal');
    else requireStructure(source.source_type === 'owner_request' && source.owner === proof.owner && get(proof.prefix,'prefix').records.length === source.delivery_cursor,'request proof');
    if (proof.team_slot !== null) requireStructure(proof.team_slot >= 1 && proof.team_slot <= (source.source_type === 'owner_initialization' ? source.team.length : 6),'evidence team slot');
  }
  for (const cert of tables.certificate) {
    const source = get(cert.source,'source'); requireStructure(source.source_type === 'public_replay' && cert.scan_start === 0 && cert.scan_end === source.records.length,'certificate scan/source');
    for (const field of ['witnesses','writers','exclusions']) ordered(cert[field],'certificate list order');
    for (const ident of cert.witnesses) {
      const proof = get(ident,'evidence'); requireStructure(proof.source === source.id && proof.owner === cert.owner && proof.scope === 'original' && cert.writers.includes(proof.writer),'certificate witness');
    }
  }
  for (const fact of tables.fact) {
    factShape(fact,c,properties);
    if (fact.freshness !== 'immutable') requireStructure(fact.certificate === null,'current fact/certificate');
    for (const ident of fact.evidence) {
      const proof = get(ident,'evidence'); requireStructure([null,fact.owner].includes(proof.owner),'foreign private proof');
      if (proof.scope === 'request') requireStructure(fact.observed_at === get(proof.source,'source').delivery_cursor || fact.state === 'unknown' && fact.observed_at === null,'request observation cursor');
      else if (get(proof.source,'source').source_type === 'owner_initialization') requireStructure(fact.observed_at === get(proof.source,'source').delivery_cursor || fact.state === 'unknown' && fact.observed_at === null,'initialization observation cursor');
      else if (proof.record_indices.length && !['boundary_kind','request_presence'].includes(fact.property)) requireStructure(fact.observed_at === Math.max(...proof.record_indices)+1,'observation cursor');
    }
    if (fact.certificate !== null) {
      const cert = get(fact.certificate,'certificate'); requireStructure(cert.owner === fact.owner && cert.subject === fact.subject && cert.property === fact.property,'certificate property/subject');
    }
  }
  function contextFacts(row: Row): Row[] {
    ordered(row.facts,'context fact order'); const facts = row.facts.map((ident: string) => get(ident,'fact'));
    logicalFacts(facts);
    return facts;
  }
  for (const start of tables.starting) {
    requireStructure(start.origin === origin.id && start.policy === profile.policy,'starting origin/policy');
    if (start.source !== null) {
      const source = get(start.source,'source'); requireStructure([null,start.owner].includes(source.owner),'starting owner');
      requireStructure(source.source_type === (start.policy === 'simulator-causal/v1' ? 'owner_initialization' : 'public_replay'),'starting source policy');
    }
    if (start.parent === null) requireStructure(start.revision === 0,'revision origin');
    else {
      const parent = get(start.parent,'starting'); requireStructure(parent.origin === start.origin && parent.owner === start.owner && parent.policy === start.policy && start.revision === parent.revision+1,'revision join');
      requireStructure(parent.source === start.source,'revision source');
      const key = (f: Row) => JSON.stringify([f.subject,f.property,f.effect_key]);
      const old = new Map(contextFacts(parent).map(f => [key(f),f])); const fresh = new Map(contextFacts(start).map(f => [key(f),f]));
      requireStructure([...old.keys()].every(k => fresh.has(k)),'immutable retention');
      requireStructure([...old].every(([k,f]) => equal(f,fresh.get(k)) || f.state === 'unknown' && ['known','known_absent'].includes(fresh.get(k)!.state)),'immutable refinement');
      requireStructure(parent.crosswalk.every((cross: Row) => start.crosswalk.some((other: Row) => equal(cross,other))),'crosswalk retention');
    }
    for (const fact of contextFacts(start)) {
      requireStructure(fact.owner === start.owner && fact.subject.startsWith(start.owner + ':') && fact.freshness === 'immutable','starting fact');
      requireStructure(applies(fact,'original',rules),'property context');
      for (const ident of fact.evidence) { const proof = get(ident,'evidence'); requireStructure(proof.scope === 'original' && proof.source === start.source,'starting evidence'); }
      if (start.source !== null && get(start.source,'source').source_type === 'public_replay' && ['known','known_absent'].includes(fact.state)) requireStructure(fact.certificate !== null,'replay original certificate');
      if (fact.certificate !== null) {
        const cert = get(fact.certificate,'certificate'); requireStructure(cert.source === start.source && equal(cert.witnesses,fact.evidence),'starting certificate source/witnesses');
        if (['known','known_absent'].includes(fact.state)) originalCertificate(cert);
      }
    }
    ordered(start.crosswalk.map((r: Row) => r.appearance),'crosswalk order');
    for (const cross of start.crosswalk) {
      const cert = get(cross.certificate,'certificate'); requireStructure(cert.owner === start.owner && cross.appearance.startsWith(start.owner + ':') && cross.roster.startsWith(start.owner + ':') && cross.roster === cert.subject,'crosswalk owner');
      requireStructure(cert.source === start.source,'crosswalk certificate source');
      originalCertificate(cert);
    }
  }
  for (const current of tables.current) {
    const prefix = get(current.prefix,'prefix'); requireStructure(current.origin === origin.id && current.cursor === prefix.records.length,'current prefix/cursor');
    for (const fact of contextFacts(current)) {
      requireStructure(fact.owner === current.owner && fact.freshness !== 'immutable' && fact.certificate === null,'current fact/certificate');
      requireStructure(applies(fact,'current',rules),'property context'); requireStructure(fact.observed_at === null || fact.observed_at <= current.cursor,'future fact');
      for (const ident of fact.evidence) {
        const proof = get(ident,'evidence'); requireStructure(['public','request'].includes(proof.scope),'current future proof');
        const ancestor = get(proof.prefix,'prefix').records; requireStructure(equal(prefix.records.slice(0,ancestor.length),ancestor),'proof prefix ancestry');
      }
    }
  }
  for (const request of tables.request) {
    const source = get(request.source,'source'); requireStructure(request.origin === origin.id && source.owner === request.owner && source.source_type === 'owner_request' && source.delivery_seq === request.sequence && source.delivery_cursor === request.cursor,'request delivery join');
    requireStructure(get(request.prefix,'prefix').records.length === request.cursor,'request prefix');
    for (const fact of contextFacts(request)) {
      requireStructure(fact.owner === request.owner && applies(fact,'request',rules),'request owner/context');
      requireStructure(fact.certificate === null && fact.freshness === 'current','request fact freshness');
      requireStructure(fact.observed_at === request.cursor || fact.state === 'unknown' && fact.observed_at === null,'request observation cursor');
      for (const ident of fact.evidence) { const proof = get(ident,'evidence'); requireStructure(proof.scope === 'request' && proof.source === source.id && proof.prefix === request.prefix,'request fact proof'); }
    }
  }
  const boundaries = [...tables.boundary].sort((a,b) => a.index-b.index);
  requireStructure(boundaries.length && boundaries.every((b,i) => b.index === i),'history continuity');
  requireStructure(boundaries.at(-1)!.id === value.target_boundary,'target boundary'); const previous = new Map<string,string>(), latestRequest = new Map<string,number>();
  let terminalSeen = false;
  for (const [index,boundary] of boundaries.entries()) {
    requireStructure(!terminalSeen || boundary.boundary_type === 'restored','terminal history lifecycle');
    terminalSeen = terminalSeen || boundary.boundary_type === 'terminal';
    requireStructure(boundary.origin === origin.id && boundary.parent === (index === 0 ? null : boundaries[index-1].id),'boundary parent/origin');
    requireStructure(index === 0 && boundary.boundary_type === 'initial' || index > 0 && boundary.boundary_type !== 'initial' && boundary.cursor >= boundaries[index-1].cursor,'boundary chronology');
    requireStructure(boundary.restored_from === (boundary.boundary_type === 'restored' ? boundary.parent : null),'restore binding');
    requireStructure(equal(boundary.bindings.map((r: Row) => r.owner),['p1','p2']),'both perspectives'); const prefixes: string[] = [];
    for (const row of boundary.bindings) {
      const knowledge = get(row.knowledge,'knowledge'), current = get(knowledge.current,'current'), start = get(knowledge.starting,'starting'), verdict = get(row.verdict,'verdict');
      requireStructure(knowledge.origin === origin.id && knowledge.owner === row.owner && row.owner === current.owner && row.owner === start.owner && knowledge.boundary === index && knowledge.policy === start.policy && start.policy === profile.policy,'knowledge join');
      requireStructure(current.cursor === boundary.cursor && current.parent === (previous.get(row.owner) ?? null),'current parent/cursor');
      if (previous.has(row.owner)) {
        const old = get(previous.get(row.owner)!,'current'), records = get(old.prefix,'prefix').records;
        requireStructure(equal(get(current.prefix,'prefix').records.slice(0,records.length),records),'history prefix ancestry');
        if (boundary.boundary_type === 'restored') {
          const prev = boundaries[index-1].bindings.find((r: Row) => r.owner === row.owner);
          requireStructure(get(prev.knowledge,'knowledge').starting === knowledge.starting && old.prefix === current.prefix,'restored context retention');
          if (knowledge.request === null) {
            const retained = (context: Row) => context.facts.filter((ident: string) => get(ident,'fact').family !== 'K20');
            requireStructure(equal(retained(old),retained(current)),'restored fact retention');
          }
        }
      }
      previous.set(row.owner,current.id); prefixes.push(current.prefix);
      if (knowledge.request !== null) {
        const request = get(knowledge.request,'request'); requireStructure(request.owner === row.owner && request.prefix === current.prefix && request.cursor === current.cursor,'knowledge request');
        requireStructure(knowledge.policy === 'simulator-causal/v1' && ['initial','mid','wait','restored'].includes(boundary.boundary_type),'request lifecycle');
        requireStructure(!terminalSeen,'restored terminal request');
        if (boundary.boundary_type === 'wait') requireStructure(!request.actionable,'wait actionable');
        if (boundary.boundary_type === 'restored') requireStructure(request.sequence > (latestRequest.get(row.owner) ?? -1),'restored fresh request');
        latestRequest.set(row.owner,request.sequence);
      }
      requireStructure(verdict.knowledge === knowledge.id && verdict.profile === profile.id,'verdict join');
      requireStructure(equal(verdict.families.map((f: Row) => f.family),Array.from({length:20},(_,i) => 'K' + String(i+1).padStart(2,'0'))),'family order');
    }
    requireStructure(prefixes[0] === prefixes[1],'boundary public prefix');
  }
  requireStructure(tables.binding.length === 2*(boundaries.length-1),'binding closure'); const seen = new Set<string>();
  for (const binding of tables.binding) {
    const key = binding.owner + ':' + binding.successor_index; requireStructure(!seen.has(key),'binding duplicate'); seen.add(key);
    requireStructure(binding.origin === origin.id && binding.input_index+1 === binding.successor_index && binding.successor_index < boundaries.length,'binding indices');
    const old = boundaries[binding.input_index].bindings.find((r: Row) => r.owner === binding.owner), fresh = boundaries[binding.successor_index].bindings.find((r: Row) => r.owner === binding.owner);
    for (const [field,legacy] of [['knowledge','knowledge'],['observation','observation_id'],['belief','belief_id']]) requireStructure(binding['input_'+field] === old[legacy] && binding['successor_'+field] === fresh[legacy],'history/legacy binding join');
    requireStructure(binding.actor_record === fresh.actor_record_id && (binding.actor_record === null) === (binding.transition === null),'actor/transition join');
  }
  const visited = new Set<string>(), pending = [value.origin,value.required_profile,value.target_boundary,...tables.binding.map(r => r.id)];
  while (pending.length) { const ident = pending.pop()!; if (!visited.has(ident)) { visited.add(ident); pending.push(...adjacency.get(ident)!); } }
  requireStructure(visited.size === lookup.size,'unreachable entry'); return diagnostic();
}

export function serializeKnowledgeWire(value: unknown): Buffer {
  checkKnowledgeStructure(value); return canonicalKnowledgeJson(value);
}


const nativeOwnerPins = Object.freeze({
  'schema.json': 'b2b64fd268682d4429301b196c25ba438d3b72a95c2126ceba45344a7f4a05b7',
  'profile.json': 'e27d492980bad928cff3f888d661fe81d9d2c161a6b3cd1a36bd5a4b85d490a2',
});
let nativeOwnerContext: Readonly<{ schema: Row; profile: Row }> | undefined;
/** Fixed decoder data only; loading/validating it grants no native source capability. */
export function nativeOwnerProjectionContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeOwnerContext) return nativeOwnerContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..',
    'docs/contracts/fixtures/perspective-knowledge-native11-owner-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries(nativeOwnerPins)) {
    const bytes = readFileSync(path.join(folder, name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected, 'native projection contract content');
    data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']), 'native profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeOwnerContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeOwnerContext!;
}
/** Arbitrary data structure check. This never registers a trusted consumer pair. */
export function checkNativeOwnerProjection(input: unknown): void { checkOwnerProjection(input, nativeOwnerProjectionContext(), false); }
export function checkNativeOwnerHealthProjection(input: unknown): void { checkOwnerProjection(input, nativeOwnerHealthProjectionContext(), true); }
export function checkNativeOwnerActiveOptionsProjection(input: unknown): void { checkOwnerProjection(input, nativeOwnerActiveOptionsContext(), true, true); }
function checkOwnerProjection(input: unknown, context: Readonly<{ schema: Row; profile: Row }>, health: boolean, options = false, identifiers = false, declared = false): void {
  canonicalKnowledgeJson(input);
  const value = input as Row;
  shape(value, context.schema, context.schema.$defs);
  requireStructure(value.id === knowledgeIdentity(value), 'native projection identity');
  const old = contract();
  const size = value.starting.filter((fact: Row) => fact.property === 'roster_size');
  requireStructure(size.length === 1 && size[0].state === 'known' && size[0].value?.type === 'integer'
    && size[0].value.data >= 1 && size[0].value.data <= 6, 'native projection roster');
  const count = size[0].value.data;
  for (const rule of context.profile.rules) {
    const facts = value[rule.context].filter((fact: Row) => fact.property === rule.property);
    const subjects = rule.subject === 'side' ? [value.owner + ':side'] : Array.from({ length: count }, (_, i) => value.owner + ':roster:' + (i + 1));
    requireStructure(facts.length === subjects.length && subjects.every(subject => facts.some((fact: Row) => fact.subject === subject)), 'native projection coverage');
    if (rule.property === 'roster_order') requireStructure(facts.every((fact: Row) => fact.value?.type === 'integer' && fact.value.data === Number(fact.subject.split(':').at(-1))), 'native projection original order');
  }
  for (const section of ['starting', 'current']) {
    logicalFacts(value[section]);
    for (const fact of value[section]) {
      const rule = context.profile.rules.find((r: Row) => r.context === section && r.property === fact.property && r.family === fact.family);
      requireStructure(rule && rule.states.includes(fact.state) && (rule.reasons ? rule.reasons[fact.state]?.includes(fact.reason) : fact.reason === rule.reason), 'native projection property scope');
      requireStructure(fact.owner === value.owner && fact.subject === (rule.subject === 'side' ? value.owner + ':side' : fact.subject)
        && (rule.subject === 'side' || new RegExp('^' + value.owner + ':roster:[1-6]$').test(fact.subject)), 'native projection subject');
      const properties = { [rule.family]: [rule.property] };
      factShape(fact, old, properties, false);
      requireStructure(fact.effect_key === null && fact.freshness === (section === 'starting' ? 'immutable' : 'current'), 'native projection lifecycle');
      requireStructure(section === 'starting' ? fact.observed_at === 0 : health && (fact.family === 'K05' || identifiers && ['K18','K19'].includes(fact.family) || declared && ['K03','K04'].includes(fact.family)) && fact.state !== 'unknown' ? Number.isSafeInteger(fact.observed_at) && fact.observed_at >= 0 : fact.observed_at === null, 'native projection cursor');
      requireStructure(fact.precision === (fact.state === 'known' ? 'exact' : 'not_applicable'), 'native projection precision');
    }
  }
  if (health) {
    for (let slot = 1; slot <= count; slot++) {
      const facts = value.current.filter((f: Row) => f.subject === value.owner + ':roster:' + slot && f.family === 'K05');
      const hp = facts.find((f: Row) => f.property === 'hp'), faint = facts.find((f: Row) => f.property === 'fainted'), status = facts.find((f: Row) => f.property === 'status');
      if (hp.state === 'unknown') requireStructure(facts.every((f: Row) => f.state === 'unknown' && f.reason === hp.reason), 'native health unavailable tuple');
      else {
        requireStructure(hp.state === 'known' && hp.value.type === 'integer' && hp.value.data >= 0 && hp.value.data <= MAX_INTEGER
          && faint.state === 'known' && faint.value.data === (hp.value.data === 0) && faint.observed_at === hp.observed_at, 'native health tuple');
        if (hp.value.data === 0) requireStructure(status.state === 'unknown' && status.reason === 'not_emitted', 'native faint status omission');
        else requireStructure(status.observed_at === hp.observed_at && (status.state === 'known_absent'
          || status.state === 'known' && ['brn','par','slp','frz','psn','tox'].includes(status.value.data)), 'native health status');
      }
    }
  }

  if (identifiers) {
    for (const fact of value.current.filter((f: Row) => ['K18','K19'].includes(f.family))) {
      if (fact.state === 'known') requireStructure(fact.value.type === 'text' && /^[a-z0-9]+$/.test(fact.value.data), 'native identifier literal');
      if (fact.family === 'K19') requireStructure(fact.state !== 'known_absent', 'native ability absence unsupported');
    }
  }

  if (options) {
    const request = value.request;
    requireStructure((['terminal','requestless'].includes(request.state)) === (request.sequence === null), 'native option sequence');
    requireStructure(request.subject === null || new RegExp('^' + value.owner + ':roster:[1-6]$').test(request.subject), 'native option subject');
    if (request.state === 'ordinary_pp') {
      requireStructure(request.subject !== null && request.sequence !== null && request.reason === 'none' && Array.isArray(request.options), 'native ordinary options');
      request.options.forEach((row: Row, i: number) => requireStructure(row.option_index === i + 1 && row.pp.value <= row.max_pp.value, 'native option tuple'));
    } else {
      requireStructure(request.options === null && request.reason === (request.state === 'unsupported' ? 'unsupported_writer' : 'not_emitted'), 'native unsupported options');
      if (request.state !== 'unsupported') requireStructure(request.subject === null && request.reason === 'not_emitted', 'native unavailable options');
    }
  }

}

let nativeHealthContext: Readonly<{ schema: Row; profile: Row }> | undefined;
export function nativeOwnerHealthProjectionContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeHealthContext) return nativeHealthContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..',
    'docs/contracts/fixtures/perspective-knowledge-native11-owner-health-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries({"schema.json": "0be2ac8142fd8404dcd4f0ede002cbaaa171ea99861e28a13496969dd01bf090", "profile.json": "48537c3be21a9fd5ea0ef0a1e28e95e9f9587bb0ad156e551d307fb4609a0ec8"})) {
    const bytes = readFileSync(path.join(folder, name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected, 'native health contract content');
    data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']), 'native health profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeHealthContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeHealthContext!;
}

let nativeOptionsContext: Readonly<{ schema: Row; profile: Row }> | undefined;
export function nativeOwnerActiveOptionsContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeOptionsContext) return nativeOptionsContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..',
    'docs/contracts/fixtures/perspective-knowledge-native11-owner-active-options-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries({"schema.json": "1d03c4adbd2806dd59303030687b58e2f9013bbaa1ab64a04124c85863b31f63", "profile.json": "f713c3425585b087f219d1088d54f9dd5412b9a89718ef08b8fa24568eb392ee"})) {
    const bytes = readFileSync(path.join(folder, name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected, 'native active-options contract content');
    data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']), 'native options profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeOptionsContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeOptionsContext!;
}

/** Fixed private decoder; validation alone grants no writer/delivery authority. */
export function checkNativeOwnerIdentifiersProjection(input: unknown): void { checkOwnerProjection(input, nativeOwnerIdentifiersContext(), true, true, true); }
let nativeIdentifiersContext: Readonly<{ schema: Row; profile: Row }> | undefined;
export function nativeOwnerIdentifiersContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeIdentifiersContext) return nativeIdentifiersContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..',
    'docs/contracts/fixtures/perspective-knowledge-native11-owner-identifiers-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries({"schema.json": "e69f3d1a7a5f36a8e363cc0050b104e29d2b4c90426ba1a58024b63dbb9af32a", "profile.json": "a20b942b6af298953727c528d2b2f359a5f5391353cd6497ed0e64a524bc4da0"})) {
    const bytes = readFileSync(path.join(folder, name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected, 'native identifier contract content');
    data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']), 'native identifier profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeIdentifiersContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeIdentifiersContext!;
}

/** Additive fixed private decoder. This issues no authenticated source/consumer capability. */
let nativeLoadoutContext: Readonly<{ schema: Row; profile: Row }> | undefined;
export function nativeOwnerLoadoutContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeLoadoutContext) return nativeLoadoutContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..',
    'docs/contracts/fixtures/perspective-knowledge-native11-owner-loadout-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries({"schema.json": "23237636a8a7b83c3e9d46a1f05da9f9443856a76550e1c31fd875cfc3b1e943", "profile.json": "82614759a5787560fc33517c31e7d4b9051208f78d949c6fe11d1c1aa5d6d6d1"})) {
    const bytes = readFileSync(path.join(folder, name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected, 'native loadout contract content');
    data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']), 'native loadout profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeLoadoutContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeLoadoutContext!;
}
export function checkNativeOwnerLoadoutProjection(input: unknown): void {
  checkOwnerProjection(input, nativeOwnerLoadoutContext(), true, true, true);
  checkOriginalInterpretation(input as Row);
}
function checkOriginalInterpretation(value: Row): void {
  const simulator = require('pokemon-showdown'), dex = simulator.Dex.forFormat('gen9randombattle');
  const size = value.starting.find((f: Row) => f.property === 'roster_size').value.data;
  requireStructure(value.original_interpretation.length === size, 'native original interpretation coverage');
  value.original_interpretation.forEach((row: Row, i: number) => {
    const subject = value.owner + ':roster:' + (i + 1);
    requireStructure(row.subject === subject, 'native original interpretation order');
    const species = value.starting.find((f: Row) => f.subject === subject && f.property === 'roster_species').value.data;
    const raw: Row = { species, moves: ['Splash'] };
    for (const field of ORIGINAL_FIELDS) {
      if (row.presence[field] === 'omitted') requireStructure(row.submission[field] === null, 'native original absent submission');
      else if (row.presence[field] === 'undefined') { requireStructure(row.submission[field] === null, 'native original undefined submission'); raw[field] = undefined; }
      else {
        requireStructure(row.submission[field] !== null, 'native original present submission'); raw[field] = row.submission[field];
        if (field === 'evs' || field === 'ivs') {
          raw[field] = {};
          for (const stat of ORIGINAL_STATS) {
            const mode = row.components[field][stat], number = row.submission[field][stat];
            requireStructure((mode === 'present') === (number !== null), 'native original component presence');
            if (mode !== 'omitted') raw[field][stat] = mode === 'undefined' ? undefined : number;
          }
        }
      }
    }
    const expected = interpretOriginalValues(raw, dex, simulator);
    requireStructure(equal(row.normalized, expected.interpretation.normalized) && equal(row.presence, expected.interpretation.presence)
      && equal(row.components, expected.interpretation.components), 'native original rule interpretation');
    for (const fact of expected.facts) {
      const actual = value.starting.find((f: Row) => f.subject === subject && f.property === fact.property);
      requireStructure(actual.state === fact.state && actual.reason === fact.reason
        && equal(actual.value, fact.value === null ? null : { type: fact.tag, data: fact.value }), 'native original fact interpretation');
    }
  });
}

/** Fixed private successor decoder; it creates no source/delivery/recipient authority. */
let nativeDetailsContext: Readonly<{ schema: Row; profile: Row }> | undefined;
export function nativeOwnerDetailsContext(): Readonly<{ schema: Row; profile: Row }> {
  if (nativeDetailsContext) return nativeDetailsContext;
  const folder = path.resolve(__dirname, __dirname.endsWith(path.join('dist', 'src')) ? '../../..' : '../..', 'docs/contracts/fixtures/perspective-knowledge-native11-owner-details-v1');
  const data: Row = {};
  for (const [name, expected] of Object.entries({"schema.json": "26102a71bc7938ab0035a236935370dda132a8d060d0ac08b2e46332f4b1328e", "profile.json": "25b1fd5d2a2b3534bf8180bbb13832a65a0f773f52b9c4ff720fbe76c5d0d9a5"})) {
    const bytes = readFileSync(path.join(folder,name));
    requireStructure(createHash('sha256').update(bytes).digest('hex') === expected,'native details contract content'); data[name] = parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id === knowledgeIdentity(data['profile.json']),'native details profile identity');
  function freeze(value: any): any { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
  nativeDetailsContext = freeze({ schema: data['schema.json'], profile: data['profile.json'] }); return nativeDetailsContext!;
}
export function checkNativeOwnerDetailsProjection(input: unknown): void {
  checkOwnerProjection(input,nativeOwnerDetailsContext(),true,true,true,true); const value = input as Row;
  checkOriginalInterpretation(value);
  const count = value.starting.find((f: Row) => f.property === 'roster_size').value.data;
  for (let slot=1;slot<=count;slot++) {
    const facts = value.current.filter((f: Row) => f.subject === value.owner + ':roster:' + slot);
    const get = (property: string) => facts.find((f: Row) => f.property === property);
    for (const property of DECLARED_PROPERTIES) {
      const f = get(property);
      if (f.state === 'known' && ['hp_max','level'].includes(property)) requireStructure(Number.isSafeInteger(f.value.data) && f.value.data >= 1 && f.value.data <= (property === 'level' ? 9999 : MAX_INTEGER),'native declared scalar');
    }
    const stats = get('calculated_stats');
    if (stats.state === 'known') declaredRequestValues({stats:stats.value.data});
    const ball = get('ball'); if (ball.state === 'known') declaredRequestValues({pokeball:ball.value.data});
    const details = get('details');
    if (details.state === 'known') {
      const expected = declaredRequestValues({details:details.value.data}).filter(f => ['details','level','gender','shiny'].includes(f.property));
      for (const f of expected) { const actual = get(f.property); requireStructure(actual.state === f.state && actual.reason === f.reason
        && equal(actual.value,f.value === null ? null : {type:f.tag,data:f.value}) && actual.observed_at === details.observed_at,'native declared details tuple'); }
    } else requireStructure(['level','gender','shiny'].every(property => get(property).state === 'unknown' && get(property).reason === details.reason),'native unavailable details tuple');
    const hp = get('hp'), max = get('hp_max');
    if (max.state === 'known') requireStructure(hp.state === 'known' && hp.value.data > 0 && hp.value.data <= max.value.data && hp.observed_at === max.observed_at,'native declared health tuple');
    if (['terminal','requestless'].includes(value.request.state)) requireStructure(DECLARED_PROPERTIES.every(property => get(property).state === 'unknown' && get(property).reason === 'not_emitted'),'native declared requestless');
  }
}

let nativeMovesContext: Readonly<{schema:Row;profile:Row}> | undefined;
export function nativeOwnerMovesContext(): Readonly<{schema:Row;profile:Row}> {
  if(nativeMovesContext)return nativeMovesContext;
  const folder=path.resolve(__dirname,__dirname.endsWith(path.join('dist','src'))?'../../..':'../..','docs/contracts/fixtures/perspective-knowledge-native11-owner-moves-v1');
  const data:Row={};
  for(const [name,pin] of Object.entries({'profile.json':'f8a4205490f94949e173de8a90643b6e1bc9d41bf12f14d3e15b36779e4dfc6f','schema.json':'10a52210d38b588573baff6787576e730378b8f9d408fd1f16402e924da25124'})){
    const bytes=readFileSync(path.join(folder,name));requireStructure(createHash('sha256').update(bytes).digest('hex')===pin,'native moves contract content');data[name]=parseKnowledgeJson(bytes);
  }
  requireStructure(data['profile.json'].id===knowledgeIdentity(data['profile.json']),'native moves profile identity');
  function freeze(value:any):any{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
  return nativeMovesContext=freeze({schema:data['schema.json'],profile:data['profile.json']});
}
/** Additive decoder: validates the inherited details contract unchanged. */
export function checkNativeOwnerMovesProjection(input:unknown):void {
  canonicalKnowledgeJson(input);const value=input as Row,context=nativeOwnerMovesContext();
  shape(value,context.schema,context.schema.$defs);
  requireStructure(value.id===knowledgeIdentity(value),'native moves identity');
  const legacy=structuredClone(value),details=nativeOwnerDetailsContext();delete legacy.owned_moves;
  legacy.schema='perspective-knowledge-consumer/native11-details-v1';legacy.policy=details.profile.policy;legacy.required_profile=details.profile.id;
  for(const fact of legacy.current)if(fact.property==='current_moves')Object.assign(fact,{state:'unknown',value:null,reason:'unimplemented_family',observed_at:null,precision:'not_applicable'});
  legacy.id=knowledgeIdentity(legacy);checkNativeOwnerDetailsProjection(legacy);
  const moves=value.owned_moves,count=value.starting.find((f:Row)=>f.property==='roster_size').value.data;
  requireStructure(moves.owner===value.owner&&moves.roster.length===count,'native moves owner roster');
  const checkFact=(f:Row,quantity:boolean)=>{
    requireStructure(f.state==='known'?f.reason==='none'&&f.value!==null&&Number.isSafeInteger(f.observed_at)&&f.observed_at>=0&&Number.isSafeInteger(f.sequence)&&f.sequence>=0:
      f.reason==='not_emitted'&&f.value===null&&f.observed_at===null&&f.sequence===null&&f.freshness==='current','native moves fact tuple');
    if(f.state==='known'&&quantity)requireStructure(Number.isSafeInteger(f.value)&&f.value>=0,'native moves quantity');
    if(f.state==='known'&&f.freshness==='current')requireStructure(f.observed_at===value.request.cursor&&f.sequence===value.request.sequence,'native moves selected emission');
  };
  moves.roster.forEach((row:Row,i:number)=>{
    requireStructure(row.subject===value.owner+':roster:'+(i+1),'native moves roster subject');checkFact(row.current_moves,false);
    const fact=value.current.find((f:Row)=>f.property==='current_moves'&&f.subject===row.subject);
    requireStructure(fact&&fact.owner===value.owner&&fact.family==='K02'&&fact.effect_key===null&&fact.state===row.current_moves.state&&fact.reason===row.current_moves.reason&&fact.observed_at===row.current_moves.observed_at&&fact.freshness==='current'&&fact.precision===(fact.state==='known'?'exact':'not_applicable')&&
      (fact.state==='known'?fact.value?.type==='texts'&&canonicalKnowledgeJson(fact.value.data).equals(canonicalKnowledgeJson(row.current_moves.value)):fact.value===null),'native moves vector fact');
    const positions=row.unbound_positions;
    requireStructure(new Set(positions).size===positions.length&&positions.every((n:number)=>n<=row.current_moves.value?.length),'native moves unbound positions');
    requireStructure(row.current_moves.state==='unknown'?row.incarnation_coverage==='blocked'&&row.reason==='not_emitted'&&positions.length===0:
      row.incarnation_coverage===(positions.length?'blocked':'ordinary_base')&&row.reason===(positions.length?'unsupported_writer':'none'),'native moves coverage');
  });
  const subjects=new Map<string,Row>();
  for(const row of moves.moves){
    requireStructure(!subjects.has(row.subject)&&row.subject===value.owner+':roster:'+row.subject.split(':')[2]+':move:'+row.anchor+':incarnation:1'&&+row.subject.split(':')[2]<=count,'native move incarnation');subjects.set(row.subject,row);
    checkFact(row.pp,true);checkFact(row.max_pp,true);
    requireStructure(row.pp.state===row.max_pp.state&&row.pp.freshness===row.max_pp.freshness&&row.pp.sequence===row.max_pp.sequence&&row.pp.observed_at===row.max_pp.observed_at,'native move PP tuple');
    if(row.pp.state==='known')requireStructure(row.pp.value<=row.max_pp.value,'native move PP range');
    if(row.membership==='present')requireStructure(moves.roster[+row.subject.split(':')[2]-1].current_moves.state==='known','native move membership');
  }
  const indices=new Set<number>(),linked=new Set<string>();
  for(const link of moves.option_links){
    const row=subjects.get(link.subject),option=value.request.options?.[link.option_index-1];
    requireStructure(row&&row.membership==='present'&&!indices.has(link.option_index)&&!linked.has(link.subject)&&link.cursor===value.request.cursor&&link.sequence===value.request.sequence&&option&&row.pp.state==='known'&&row.pp.freshness==='current'&&row.pp.value===option.pp.value&&row.max_pp.value===option.max_pp.value&&row.subject.startsWith(value.request.subject+':move:'),'native move option link');
    indices.add(link.option_index);linked.add(link.subject);
  }
  for(const row of moves.moves)if(row.pp.state==='known'&&row.pp.freshness==='current')requireStructure(linked.has(row.subject),'native move unlinked current PP');
}
