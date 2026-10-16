/** Pure original-value interpretation, never a source/recipient authority factory. */
export const ORIGINAL_FIELDS = ['nature','evs','ivs','happiness','level','gender','shiny','pokeball','teraType'] as const;
export const ORIGINAL_STATS = ['hp','atk','def','spa','spd','spe'] as const;
const own = (value: any, key: string) => Object.hasOwn(value, key);
function need(value: unknown, code: string): asserts value { if (!value) throw new Error('native-original-values/v1/' + code); }
const presence = (value: any, key: string) => !own(value, key) ? 'omitted' : value[key] === undefined ? 'undefined' : 'present';
const integer = (value: any) => Number.isSafeInteger(value) && value >= 0 && value <= 2147483647;
export interface OriginalInterpretation { presence: Record<string, string>; components: Record<string, Record<string, string>>; submission: Record<string, any>; normalized: Record<string, any> }
export interface OriginalValue { property: string; state: 'known' | 'known_absent' | 'unknown'; value: any; tag: string; reason: 'none' | 'unsupported_writer' }
export function interpretOriginalValues(raw: Record<string, any>, dex: any, simulator: any): { facts: OriginalValue[]; interpretation: OriginalInterpretation } {
  need(dex.gen === 9 && dex === simulator.Dex.forFormat('gen9randombattle'), 'rules');
  const submitted: Record<string, any> = {}, fields: Record<string, string> = {}, components: Record<string, Record<string, string>> = {};
  for (const field of ORIGINAL_FIELDS) {
    fields[field] = presence(raw, field); const value = raw[field];
    if (field === 'evs' || field === 'ivs') {
      components[field] = {};
      need(value === undefined || value && typeof value === 'object' && !Array.isArray(value)
        && Object.keys(value).every(key => (ORIGINAL_STATS as readonly string[]).includes(key)), 'submitted-stats');
      submitted[field] = value === undefined ? null : {};
      for (const stat of ORIGINAL_STATS) {
        components[field][stat] = value === undefined ? 'omitted' : presence(value, stat);
        const v = value?.[stat]; need(v === undefined || integer(v), 'submitted-component');
        if (submitted[field]) submitted[field][stat] = v === undefined ? null : v;
      }
    } else {
      need(value === undefined || (['happiness','level'].includes(field) ? integer(value)
        : field === 'shiny' ? typeof value === 'boolean' : typeof value === 'string'), 'submitted-field');
      submitted[field] = value === undefined ? null : value;
    }
  }
  need(raw.gender === undefined || ['M','F','N',''].includes(raw.gender), 'gender');
  need(!raw.nature || dex.natures.get(raw.nature).exists, 'nature');
  need(!raw.teraType || dex.types.get(raw.teraType).exists, 'tera');
  // The actual pack/unpack rules normalize only a detached copy of held input.
  const set = simulator.Teams.unpack(simulator.Teams.pack([structuredClone(raw)]))?.[0];
  need(set, 'packing');
  const species = dex.species.get(set.species); need(species.exists, 'species');
  const clamp = (n: number, low: number, high: number) => simulator.Utils.clampIntRange(n, low, high);
  set.level = clamp(set.level || 100, 1, 9999);
  set.evs ||= {}; set.ivs ||= {};
  for (const stat of ORIGINAL_STATS) { set.evs[stat] = clamp(set.evs[stat] || 0, 0, 255); set.ivs[stat] = clamp(set.ivs[stat] ?? 31, 0, 31); }
  const gender = ['M','F','N'].includes(set.gender) ? set.gender : species.gender || null;
  const normalized: Record<string, any> = { nature: set.nature || null, evs: set.evs, ivs: set.ivs,
    happiness: typeof set.happiness === 'number' ? clamp(set.happiness, 0, 255) : 255,
    level: set.level, gender, gender_resolution: gender === null ? 'unresolved' : ['M','F','N'].includes(set.gender) ? 'submitted' : 'species_fixed',
    shiny: !!set.shiny, ball: simulator.toID(set.pokeball) || 'pokeball', starting_tera: set.teraType || species.types[0] };
  // Borrow the pinned public rule functions on a data-only receiver: no Battle,
  // Pokemon, event dispatch, seed, native mutable stat or request is consulted.
  const ruleTable = dex.formats.getRuleTable(dex.formats.get('gen9randombattle'));
  const receiver = { dex, ruleTable, trunc: dex.trunc, statModify: simulator.Battle.prototype.statModify };
  const stats = simulator.Battle.prototype.spreadModify.call(receiver, species.baseStats, set);
  if (species.maxHP) stats.hp = species.maxHP;
  normalized.calculated_stats = Object.fromEntries(ORIGINAL_STATS.filter(stat => stat !== 'hp').map(stat => [stat, stats[stat]]));
  normalized.hp_max = stats.hp;
  normalized.details = gender === null ? null : simulator.Pokemon.prototype.getUpdatedDetails.call({ species, level: set.level, gender: gender === 'N' ? '' : gender, set: { shiny: normalized.shiny } });
  const facts: OriginalValue[] = [];
  function fact(property: string, value: any, tag: string, state: OriginalValue['state'] = value === null ? 'known_absent' : 'known') {
    facts.push({ property, state, value, tag, reason: state === 'unknown' ? 'unsupported_writer' : 'none' });
  }
  for (const [field, property, tag] of [['nature','submitted_nature','text'],['happiness','submitted_happiness','integer'],['gender','gender','text'],['shiny','shiny','boolean'],['pokeball','ball','text']]) fact(property, submitted[field], tag);
  for (const [field, property] of [['evs','submitted_evs'],['ivs','submitted_ivs']]) {
    const partial = submitted[field] !== null && ORIGINAL_STATS.some(stat => components[field][stat] !== 'present');
    fact(property, partial ? null : submitted[field], 'six_stats', partial ? 'unknown' : submitted[field] === null ? 'known_absent' : 'known');
  }
  fact('level', normalized.level, 'integer'); fact('starting_tera', normalized.starting_tera, 'text');
  fact('details', normalized.details, 'text', gender === null ? 'unknown' : 'known');
  fact('calculated_stats', normalized.calculated_stats, 'five_stats'); fact('hp_max', normalized.hp_max, 'integer');
  return { facts, interpretation: { presence: fields, components, submission: submitted, normalized } };
}
