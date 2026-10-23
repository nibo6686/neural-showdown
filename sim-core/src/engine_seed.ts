/** Native PRNG strings retain their algorithm; legacy numeric roots stay unchanged. */
export type EngineSeed = [number, number, number, number] | string;
export function isEngineSeed(value: unknown): value is EngineSeed {
  return typeof value === 'string'
    ? /^(?:sodium,[a-f0-9]{32}|gen5,[a-f0-9]{16})$/.test(value)
    : Array.isArray(value) && value.length === 4 && Array.from(value).every(Number.isSafeInteger);
}
export function copyEngineSeed(value: readonly number[] | string): EngineSeed {
  if (!isEngineSeed(value)) throw new Error('Invalid native engine seed');
  return typeof value === 'string' ? value : [...value];
}
export interface PlayerGenerationInputs {
  p1: {name: string; seed: EngineSeed};
  p2: {name: string; seed: EngineSeed};
}
