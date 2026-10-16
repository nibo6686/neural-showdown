import { helperContext as readerContext, runtimeData, assertReaderInput, HISTORICAL10_CONTEXT, type ReaderContext } from './version_profile';
import { PROTOCOL_CONTRACT } from './protocol_contract';

/** Consume only a prefix whose raw grammar and effect inventory were validated. */
export function assertPublicFieldMatchesEvidence(prefix: readonly string[], field: {
  weather: string | null; terrain: string | null; pseudo_weather: string[];
  side_conditions: {self: Record<string, number>; opponent: Record<string, number>};
}, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): void {
  readerContext(rulesContext);
  const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
  if (!record(field) || Object.keys(field).length !== 4
    || !['weather', 'terrain', 'pseudo_weather', 'side_conditions'].every(key => Object.hasOwn(field, key))) {
    throw new Error('Observation field fields are not exact.');
  }
  if ((field.weather !== null && typeof field.weather !== 'string')
    || (field.terrain !== null && typeof field.terrain !== 'string')
    || !Array.isArray(field.pseudo_weather) || field.pseudo_weather.some(value => typeof value !== 'string')) {
    throw new Error('Observation field values are malformed.');
  }
  const sides = field.side_conditions;
  if (!record(sides) || Object.keys(sides).length !== 2 || !['self', 'opponent'].every(key => Object.hasOwn(sides, key))
    || Object.values(sides).some(side => !record(side) || Object.values(side).some(value => typeof value !== 'number' || !Number.isFinite(value)))) {
    throw new Error('Observation side conditions are malformed.');
  }
  let weather: string | null = null;
  let terrain: string | null = null;
  let trickRoom = false;
  const rules = readerContext(rulesContext).protocol.validation_rules;
  const fail = (detail: string): never => { throw new Error(`Public field evidence mismatch: ${detail}`); };
  for (const line of prefix) {
    const parts = line.split('|'), command = parts[1], value = parts[2];
    if (command === '-weather') {
      if (value === 'none') {
        if (weather === null || weather === 'none') fail('weather ends without a public start');
        weather = 'none';
      } else {
        if (!rules.weather.ids.includes(value)) fail('unsupported weather writer');
        const id = value.toLowerCase();
        if (parts[3] === '[upkeep]') {
          if (weather !== id) fail('weather upkeep disagrees with its public start');
        } else weather = id;
      }
    } else if (command === '-fieldstart' || command === '-fieldend') {
      const id = rules.terrain.ids.find(id => rules.terrain.public_names[id] === value);
      if (id) {
        if (command === '-fieldstart') terrain = id;
        else {
          if (terrain !== id) fail('terrain ends without its current public start');
          terrain = null;
        }
      } else if (value === rules.trick_room.effect) {
        const start = command === rules.trick_room.start_command;
        if (start === trickRoom) fail('Trick Room writer disagrees with its public lifecycle');
        trickRoom = start;
      }
    }
  }
  if (field.weather !== weather) fail('weather disagrees with retained public prefix');
  if (field.terrain !== terrain) fail('terrain disagrees with retained public prefix');
  // Terrain and other rooms retain their existing coarse list conventions.
  if (field.pseudo_weather.includes('trickroom') !== trickRoom) fail('Trick Room membership disagrees with retained public prefix');
}
