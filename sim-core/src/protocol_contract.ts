import fs from 'node:fs';
import path from 'node:path';

type JsonObject = Record<string, unknown>;
export interface ProtocolContract {
  schema_version: 'showdown-protocol-contract/v2';
  simulator: { package: string; version: string; format: string; mod: string; game_type: string };
  source_basis: string[];
  framing_only_records: Array<{ record: string; disposition: string; evidence: string }>;
  supported_commands: string[];
  recognized_unsupported_commands: Array<{ token: string; kind: string; reason: string; source?: string }>;
  record_fixtures: Array<Record<string, unknown>>;
  rejection_fixtures: Array<{ record: string; kind: string }>;
  valid_record_controls: Array<{ token: string; record: string; evidence: string; reconstruction_scope: string }>;
  validation_rules: {
    integer: { lexeme: string; leading_zeroes: string; safe_limit: number };
    request: { root: string; rqid_presence: string; rqid_type: string; rqid_null: string; rqid_boolean: string; non_finite_numbers: string; other_properties: string };
    health_condition: { fainted: string; ratio: string; numerator_limit: string; statuses: string[] };
    player_ident: { side_ids: string[]; slots: string[]; separator: string; name: string };
    switch_drag: { optional_tag: string };
    boost_event: { stats: string[]; delta_min: number; delta_max: number; set_min: number; set_max: number; tags: string[] };
    health_event_tags: Record<'damage' | 'heal' | 'sethp', string[]>;
    detailschange: { condition: string };
    endability: { forms: string[]; move_source_tag: string };
    singleturn: { untagged_effects: string[]; tagged_forms: Array<{ effect: string; tag: string; tag_value: string; ident_role?: 'active' | 'side-or-active' }> };
    tier: { payload_fields: number; label: string };
  };
}

export class ProtocolContractError extends Error {}

const EXPECTED_RULES = {
  integer: { lexeme: 'ascii-decimal', leading_zeroes: 'reject', safe_limit: 9007199254740991 },
  request: {
    root: 'object', rqid_presence: 'optional', rqid_type: 'safe-integer', rqid_null: 'reject',
    rqid_boolean: 'reject', non_finite_numbers: 'reject', other_properties: 'transient-private',
  },
  health_condition: {
    fainted: '0 fnt', ratio: 'positive-safe-integer-pair', numerator_limit: 'at-most-denominator',
    statuses: ['brn', 'par', 'slp', 'psn', 'tox', 'frz'],
  },
  player_ident: {
    side_ids: ['p1', 'p2'], slots: ['', 'a', 'b', 'c', 'd', 'e', 'f'],
    separator: ': ', name: 'trimmed-nonempty-text',
  },
  switch_drag: { optional_tag: '[from] trimmed-nonempty-text' },
  boost_event: {
    stats: ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'],
    delta_min: 0, delta_max: 12, set_min: -6, set_max: 6,
    tags: ['[from] trimmed-nonempty-text', '[silent]', '[zeffect]'],
  },
  health_event_tags: {
    damage: ['[from] trimmed-nonempty-text', '[of] player-ident', '[silent]', '[partiallytrapped]'],
    heal: ['[from] trimmed-nonempty-text', '[of] player-ident', '[silent]', '[zeffect]', '[wisher] trimmed-nonempty-text'],
    sethp: ['[from] trimmed-nonempty-text', '[silent]'],
  },
  detailschange: { condition: 'optional-health-condition' },
  endability: { forms: ['target-only', 'move-source'], move_source_tag: '[from] move: ' },
  singleturn: {
    untagged_effects: [
      'move: Protect', 'move: Beak Blast', 'Crafty Shield', 'move: Electrify', 'move: Endure',
      'move: Focus Punch', 'move: Follow Me', 'Protect', 'move: Magic Coat', 'Mat Block',
      'Max Guard', 'Powder', 'Quick Guard', 'move: Rage Powder', 'move: Roost', 'move: Shell Trap',
      'Snatch', 'move: Spotlight', 'Wide Guard',
    ],
    tagged_forms: [
      { effect: 'move: Follow Me', tag: '[zeffect]', tag_value: 'none' },
      // Helping Hand receives its source as the acting Pokemon, whose
      // Pokemon.toString() form includes an active slot.
      { effect: 'Helping Hand', tag: '[of]', tag_value: 'player-ident', ident_role: 'active' },
    ],
  },
  tier: { payload_fields: 1, label: 'nonempty-text' },
};
const ROOT_KEYS = [
  'schema_version', 'simulator', 'source_basis', 'framing_only_records', 'supported_commands', 'recognized_unsupported_commands',
  'record_fixtures', 'rejection_fixtures', 'disposition_rules', 'validation_rules', 'valid_record_controls',
];
const SIMULATOR = { package: 'pokemon-showdown', version: '0.11.10', format: 'gen9randombattle', mod: 'gen9', game_type: 'singles' };
const DISPOSITION_KEYS = ['supported', 'recognized_unsupported', 'malformed_supported', 'unknown', 'privacy'];
const CLASSIFICATIONS = new Set(['raw-only', 'represented', 'represented (bounded Topsy-Turvy)']);
const UNSUPPORTED_KINDS = new Set(['unresolved_alias', 'internal_alias', 'unsupported_stop']);
const REJECTION_KINDS = new Set(['malformed', 'unknown', ...UNSUPPORTED_KINDS]);

function fail(detail: string): never {
  throw new ProtocolContractError(`Invalid shared protocol contract: ${detail}.`);
}

function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value: JsonObject, required: string[], optional: string[], label: string): void {
  const keys = Object.keys(value);
  const missing = required.filter((key) => !Object.hasOwn(value, key));
  const extra = keys.filter((key) => !required.includes(key) && !optional.includes(key));
  if (missing.length || extra.length) fail(`${label} keys (missing: ${missing.join(',') || 'none'}; unsupported: ${extra.join(',') || 'none'})`);
}

function string(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || value.trim() === '') fail(`${label} must be nonempty text`);
}

function stringArray(value: unknown, label: string, nonempty = true): asserts value is string[] {
  if (!Array.isArray(value) || (nonempty && value.length === 0) || value.some((item) => typeof item !== 'string' || !item.trim())) {
    fail(`${label} must be ${nonempty ? 'a nonempty ' : 'an '}array of nonempty strings`);
  }
}

function sameJson(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length
      && left.every((item, index) => sameJson(item, right[index]));
  }
  if (isObject(left) || isObject(right)) {
    if (!isObject(left) || !isObject(right)) return false;
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return sameJson(leftKeys, rightKeys) && leftKeys.every((key) => sameJson(left[key], right[key]));
  }
  return left === right;
}

function commandToken(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || !(value === 't:' || /^-?[a-z][a-z0-9]*$/.test(value))) fail(`${label} is not a supported protocol token`);
}

function recordToken(record: unknown, label: string): string {
  if (typeof record !== 'string' || !record.startsWith('|') || record.includes('\n') || record.includes('\r')) {
    fail(`${label} must be one protocol record`);
  }
  return record.split('|')[1] ?? '';
}

function validateContract(value: unknown): ProtocolContract {
  if (!isObject(value)) fail('root must be an object');
  exactKeys(value, ROOT_KEYS, [], 'root');
  if (value.schema_version !== 'showdown-protocol-contract/v2') fail('unsupported schema_version');
  if (!isObject(value.simulator)) fail('simulator must be an object');
  exactKeys(value.simulator, Object.keys(SIMULATOR), [], 'simulator');
  if (!sameJson(value.simulator, SIMULATOR)) fail('simulator provenance must match pokemon-showdown@0.11.10 gen9randombattle singles');
  stringArray(value.source_basis, 'source_basis');
  if (!Array.isArray(value.framing_only_records) || value.framing_only_records.length !== 1) fail('framing_only_records must define the single pinned separator record');
  const framing = value.framing_only_records[0];
  if (!isObject(framing)) fail('framing_only_records[0] must be an object');
  exactKeys(framing, ['record', 'disposition', 'evidence'], [], 'framing_only_records[0]');
  if (framing.record !== '|' || framing.disposition !== 'validate then filter from public prefixes'
    || framing.evidence !== 'pinned sim/battle.ts:1451,2754,2881 emits empty separator records') {
    fail('framing_only_records contains an unsupported or unproven record');
  }
  if (!isObject(value.validation_rules) || !sameJson(value.validation_rules, EXPECTED_RULES)) fail('validation_rules contains unsupported or inconsistent definitions');
  if (!isObject(value.disposition_rules)) fail('disposition_rules must be an object');
  exactKeys(value.disposition_rules, DISPOSITION_KEYS, [], 'disposition_rules');
  for (const [key, rule] of Object.entries(value.disposition_rules)) string(rule, `disposition_rules.${key}`);

  if (!Array.isArray(value.supported_commands) || value.supported_commands.length === 0) fail('supported_commands must be a nonempty array');
  value.supported_commands.forEach((token, index) => commandToken(token, `supported_commands[${index}]`));
  const supported = value.supported_commands as string[];
  const supportedSet = new Set(supported);
  if (supportedSet.size !== supported.length) fail('supported_commands contains duplicate tokens');

  if (!Array.isArray(value.recognized_unsupported_commands)) fail('recognized_unsupported_commands must be an array');
  const unsupported = new Map<string, string>();
  value.recognized_unsupported_commands.forEach((entry, index) => {
    if (!isObject(entry)) fail(`recognized_unsupported_commands[${index}] must be an object`);
    exactKeys(entry, ['token', 'kind', 'reason'], ['source'], `recognized_unsupported_commands[${index}]`);
    commandToken(entry.token, `recognized_unsupported_commands[${index}].token`);
    if (typeof entry.kind !== 'string' || !UNSUPPORTED_KINDS.has(entry.kind)) fail(`recognized_unsupported_commands[${index}].kind is unsupported`);
    string(entry.reason, `recognized_unsupported_commands[${index}].reason`);
    if (Object.hasOwn(entry, 'source')) string(entry.source, `recognized_unsupported_commands[${index}].source`);
    if (supportedSet.has(entry.token)) fail(`token ${entry.token} has conflicting supported/unsupported entries`);
    if (unsupported.has(entry.token)) fail(`duplicate recognized-unsupported token ${entry.token}`);
    unsupported.set(entry.token, entry.kind);
  });
  if (unsupported.get('-singlemove') !== 'unsupported_stop') fail('-singlemove must remain a recognized unsupported stop');

  if (!Array.isArray(value.record_fixtures)) fail('record_fixtures must be an array');
  const fixtureTokens = new Set<string>();
  value.record_fixtures.forEach((fixture, index) => {
    const label = `record_fixtures[${index}]`;
    if (!isObject(fixture)) fail(`${label} must be an object`);
    exactKeys(fixture, ['token', 'record', 'inventory_classification', 'grammar_summary', 'evidence', 'inventory_grammar', 'fixture_reference'], ['pinned_emitter_sources', 'pinned_dynamic_emitter_source'], label);
    commandToken(fixture.token, `${label}.token`);
    if (recordToken(fixture.record, `${label}.record`) !== fixture.token) fail(`${label}.token does not match its record token`);
    if (!supportedSet.has(fixture.token)) fail(`${label}.token is not in supported_commands`);
    if (fixtureTokens.has(fixture.token)) fail(`duplicate record fixture for ${fixture.token}`);
    fixtureTokens.add(fixture.token);
    if (typeof fixture.inventory_classification !== 'string' || !CLASSIFICATIONS.has(fixture.inventory_classification)) fail(`${label}.inventory_classification is unsupported`);
    for (const key of ['grammar_summary', 'evidence', 'fixture_reference']) string(fixture[key], `${label}.${key}`);
    if (!isObject(fixture.inventory_grammar)) fail(`${label}.inventory_grammar must be an object`);
    exactKeys(fixture.inventory_grammar, ['required', 'optional', 'shape'], [], `${label}.inventory_grammar`);
    for (const [key, item] of Object.entries(fixture.inventory_grammar)) string(item, `${label}.inventory_grammar.${key}`);
    if (Object.hasOwn(fixture, 'pinned_emitter_sources')) stringArray(fixture.pinned_emitter_sources, `${label}.pinned_emitter_sources`);
    if (Object.hasOwn(fixture, 'pinned_dynamic_emitter_source')) string(fixture.pinned_dynamic_emitter_source, `${label}.pinned_dynamic_emitter_source`);
  });
  if (fixtureTokens.size !== supportedSet.size || [...supportedSet].some((token) => !fixtureTokens.has(token))) fail('record_fixtures must contain exactly one fixture per supported token');

  if (!Array.isArray(value.valid_record_controls) || value.valid_record_controls.length === 0) fail('valid_record_controls must be a nonempty array');
  value.valid_record_controls.forEach((control, index) => {
    const label = `valid_record_controls[${index}]`;
    if (!isObject(control)) fail(`${label} must be an object`);
    exactKeys(control, ['token', 'record', 'evidence', 'reconstruction_scope'], [], label);
    commandToken(control.token, `${label}.token`);
    if (!supportedSet.has(control.token) || recordToken(control.record, `${label}.record`) !== control.token) fail(`${label} has inconsistent command and record tokens`);
    string(control.evidence, `${label}.evidence`);
    string(control.reconstruction_scope, `${label}.reconstruction_scope`);
  });

  if (!Array.isArray(value.rejection_fixtures)) fail('rejection_fixtures must be an array');
  value.rejection_fixtures.forEach((fixture, index) => {
    const label = `rejection_fixtures[${index}]`;
    if (!isObject(fixture)) fail(`${label} must be an object`);
    exactKeys(fixture, ['record', 'kind'], [], label);
    if (typeof fixture.record !== 'string' || typeof fixture.kind !== 'string' || !REJECTION_KINDS.has(fixture.kind)) fail(`${label} has an unsupported rejection definition`);
    const token = fixture.record.startsWith('|') ? recordToken(fixture.record, `${label}.record`) : null;
    if (token === null && fixture.kind !== 'malformed') fail(`${label}.record must be a protocol record for its rejection kind`);
    if (fixture.kind === 'malformed' && token !== null && !supportedSet.has(token)) fail(`${label} marks an unsupported token as malformed`);
    if (fixture.kind === 'unknown' && token !== null && (supportedSet.has(token) || unsupported.has(token))) fail(`${label} marks a classified token unknown`);
    if (UNSUPPORTED_KINDS.has(fixture.kind) && (token === null || unsupported.get(token) !== fixture.kind)) fail(`${label} does not match its recognized-unsupported disposition`);
  });
  return value as unknown as ProtocolContract;
}

export function validateProtocolContract(value: unknown): ProtocolContract {
  return validateContract(value);
}

export function loadProtocolContract(assetPath?: string): ProtocolContract {
  if (assetPath !== undefined) {
    try {
      return validateContract(JSON.parse(fs.readFileSync(assetPath, 'utf8')) as unknown);
    } catch (error) {
      if (error instanceof ProtocolContractError) throw error;
      throw new ProtocolContractError(`Unable to load shared protocol contract at ${assetPath}: ${(error as Error).message}`);
    }
  }
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(directory, 'trainer', 'src', 'neural', 'protocol_contract.json');
    if (fs.existsSync(candidate)) {
      try {
        return validateContract(JSON.parse(fs.readFileSync(candidate, 'utf8')) as unknown);
      } catch (error) {
        if (error instanceof ProtocolContractError) throw error;
        throw new ProtocolContractError(`Unable to load shared protocol contract at ${candidate}: ${(error as Error).message}`);
      }
    }
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new ProtocolContractError('Shared trainer/src/neural/protocol_contract.json was not found.');
}

export const PROTOCOL_CONTRACT = loadProtocolContract();
export const SUPPORTED_RAW_COMMANDS = new Set(PROTOCOL_CONTRACT.supported_commands);
export const RECOGNIZED_UNSUPPORTED_RAW_COMMANDS = new Map(
  PROTOCOL_CONTRACT.recognized_unsupported_commands.map((entry) => [entry.token, entry]),
);

/** Checks the source-emitted Pokemon.toString() spelling without repairing it. */
export function isCanonicalPlayerIdent(value: unknown, activeRequired = false): value is string {
  if (typeof value !== 'string' || value !== value.trim() || value.includes('|')) return false;
  const rule = PROTOCOL_CONTRACT.validation_rules.player_ident;
  const separatorIndex = value.indexOf(rule.separator);
  if (separatorIndex < 0) return false;
  const prefix = value.slice(0, separatorIndex);
  const name = value.slice(separatorIndex + rule.separator.length);
  const side = prefix.slice(0, 2);
  const slot = prefix.slice(2);
  return rule.side_ids.includes(side) && rule.slots.includes(slot)
    && (!activeRequired || slot !== '') && name !== '' && name === name.trim();
}

export function isCanonicalSideOnlyPlayerIdent(value: unknown): value is string {
  const rule = PROTOCOL_CONTRACT.validation_rules.player_ident;
  return isCanonicalPlayerIdent(value)
    && rule.side_ids.some((side) => value.startsWith(side + rule.separator));
}
