import { parseDetails } from './battle_helpers';
export const DECLARED_STATS = ['atk','def','spa','spd','spe'] as const;
export const DECLARED_PROPERTIES = ['calculated_stats','hp_max','level','gender','shiny','ball','details'] as const;
export const DECLARED_STATS_SEMANTICS = 'request-declared-baseStoredStats/v1' as const;
function need(value: unknown, code: string): asserts value { if (!value) throw new Error('owned-request-values/v1/' + code); }
export interface DeclaredValue { property: string; tag: string; state: 'known' | 'known_absent' | 'unknown'; value: any; reason: 'none' | 'not_emitted' | 'unsupported_writer' }
/** Exact emitted data interpretation only. This cannot bind an actor, source or delivery. */
export function declaredRequestValues(row: Record<string, any>): DeclaredValue[] {
  const values: DeclaredValue[] = [];
  const emit = (property: string, value: any, tag: string, state: DeclaredValue['state'] = 'known') =>
    values.push({ property, value, tag, state, reason: state === 'unknown' ? 'not_emitted' : 'none' });
  if (Object.hasOwn(row,'stats')) {
    const stats = row.stats;
    need(stats && typeof stats === 'object' && !Array.isArray(stats) && Object.keys(stats).sort().join(',') === [...DECLARED_STATS].sort().join(',')
      && DECLARED_STATS.every(key => Number.isSafeInteger(stats[key]) && stats[key] >= 0 && stats[key] <= 2147483647), 'stats');
    emit('calculated_stats', Object.fromEntries(DECLARED_STATS.map(key => [key,stats[key]])), 'five_stats');
  } else emit('calculated_stats',null,'five_stats','unknown');
  const condition = row.condition;
  const positive = typeof condition === 'string' && /^([1-9][0-9]*)\/([1-9][0-9]*)(?: (?:brn|par|slp|frz|psn|tox))?$/.exec(condition);
  if (positive) {
    const hp=Number(positive[1]), max=Number(positive[2]);
    need(Number.isSafeInteger(hp) && hp <= max && max <= 2147483647, 'denominator'); emit('hp_max',max,'integer');
  } else { need(condition === undefined || condition === '0 fnt','condition'); emit('hp_max',null,'integer','unknown'); }
  if (Object.hasOwn(row,'details')) {
    const details = row.details;
    need(typeof details === 'string' && details.length <= 256, 'details');
    const match = /^([^,|\[\]\r\n]+)(?:, L([1-9][0-9]{0,3}))?(?:, ([MF]))?(, shiny)?$/.exec(details);
    need(match && match[1].trim() === match[1] && match[1].length > 0, 'details');
    const parsed = parseDetails(details), level = parsed.level ?? 100, shiny = !!match[4];
    need(details === match[1] + (level === 100 ? '' : ', L' + level) + (parsed.gender ? ', ' + parsed.gender : '') + (shiny ? ', shiny' : ''), 'details-order');
    emit('details',details,'text'); emit('level',level,'integer');
    emit('gender',parsed.gender,'text',parsed.gender === null ? 'known_absent' : 'known'); emit('shiny',shiny,'boolean');
  } else for (const [property,tag] of [['details','text'],['level','integer'],['gender','text'],['shiny','boolean']]) emit(property,null,tag,'unknown');
  if (Object.hasOwn(row,'pokeball')) { need(typeof row.pokeball === 'string' && /^[a-z0-9]+$/.test(row.pokeball),'ball'); emit('ball',row.pokeball,'text'); }
  else emit('ball',null,'text','unknown');
  return values;
}
