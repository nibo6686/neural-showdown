import { helperContext as readerContext, runtimeData, assertReaderInput, HISTORICAL10_CONTEXT, type ReaderContext } from './version_profile';
import fs from 'node:fs';
import path from 'node:path';

type InventoryEntry = {
  id: string;
  category: string;
  classification: string;
};

type EffectDiscovery = {
  additional_entries: InventoryEntry[];
  special_values: Array<{ id: string; commands: string[]; classification: string }>;
};

type CoverageManifest = {
  condition_inventory: InventoryEntry[];
  effect_discovery: EffectDiscovery;
  public_typed_state_lifecycle?: {
    schema_version: string;
    entries: Array<{ id: string; family: EffectFamily; disposition: string }>;
  };
};

export type EffectDisposition = 'represented' | 'raw-only';
export type EffectFamily = 'ability_state' | 'move_volatile' | 'weather' | 'field' | 'side_condition';

export class EffectInventoryError extends Error {
  readonly code = 'simulator-coverage/v1/unclassified-effect-value';
  readonly command: string;
  readonly family: EffectFamily;
  readonly value: string;

  constructor(command: string, family: EffectFamily, value: string, reason = 'unknown') {
    super(`${'simulator-coverage/v1/unclassified-effect-value'} command=${command} family=${family} value=${value} disposition=${reason}`);
    this.name = 'EffectInventoryError';
    this.command = command;
    this.family = family;
    this.value = value;
  }
}

function loadCoverageManifest(): CoverageManifest {
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(directory, 'simulator_coverage', 'pokemon-showdown-0.11.10-gen9randombattle.json');
    if (fs.existsSync(candidate)) return JSON.parse(fs.readFileSync(candidate, 'utf8')) as CoverageManifest;
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new Error('Simulator effect inventory was not found.');
}

const manifest = loadCoverageManifest();
const lifecycleEntries = new Map((manifest.public_typed_state_lifecycle?.entries || [])
  .map((entry) => [`${entry.family}:${entry.id}`, entry]));
const entries = new Map<string, InventoryEntry>();
for (const item of [...manifest.condition_inventory, ...manifest.effect_discovery.additional_entries]) {
  if (entries.has(item.id)) throw new Error(`Duplicate simulator effect inventory ID ${item.id}.`);
  entries.set(item.id, item);
}

function toEffectID(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function commandFamily(command: string): { family: EffectFamily; categories: string[] } | null {
  if (command === '-start' || command === '-end') {
    return { family: 'move_volatile', categories: ['move_volatile'] };
  }
  if (command === '-weather') return { family: 'weather', categories: ['weather'] };
  if (command === '-fieldstart' || command === '-fieldend') {
    return { family: 'field', categories: ['pseudo_weather', 'terrain'] };
  }
  if (command === '-sidestart' || command === '-sideend') {
    return { family: 'side_condition', categories: ['side_condition'] };
  }
  return null;
}

export function classifyEffectRecord(command: string, rawValue: string, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): EffectDisposition {
  readerContext(rulesContext);
  const rule = commandFamily(command);
  if (!rule) return 'represented';

  const special = readerContext(rulesContext).inventory.effect_discovery.special_values.find((item: {commands: string[]; id: string; classification: string}) =>
    item.commands.includes(command) && item.id === toEffectID(rawValue));
  if (special) {
    if (!['represented', 'raw-only'].includes(special.classification)) throw new EffectInventoryError(command, rule.family, rawValue, special.classification);
    return special.classification as EffectDisposition;
  }

  const sourcePrefix = /^(move|ability|item):\s*/i.exec(rawValue);
  const identifier = toEffectID(sourcePrefix ? rawValue.slice(sourcePrefix[0].length) : rawValue);
  const item = readerContext(rulesContext).effects[identifier];
  if (!item) throw new EffectInventoryError(command, rule.family, rawValue);
  if (item.category === 'ability_state' && (command === '-start' || command === '-end')) {
    rule.family = 'ability_state'; rule.categories = ['ability_state'];
  }
  const lifecycle = readerContext(rulesContext).lifecycle[`${rule.family}:${identifier}`];
  if (lifecycle?.disposition === 'raw-only') return 'raw-only';
  if (lifecycle?.disposition === 'source-proven-unreachable' || lifecycle?.disposition === 'unsupported-fail-closed') {
    throw new EffectInventoryError(command, rule.family, rawValue, lifecycle.disposition);
  }
  if (item.classification === 'raw-only') return 'raw-only';
  if (item.classification !== 'represented') throw new EffectInventoryError(command, rule.family, rawValue, item.classification);
  if (!rule.categories.includes(item.category)) throw new EffectInventoryError(command, rule.family, rawValue, `family-mismatch:${item.category}`);
  return 'represented';
}
