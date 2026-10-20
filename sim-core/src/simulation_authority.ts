/** A simulation result can never be published as authoritative episode evidence. */
export function rejectSimulationOnlyPayload(value: unknown): void {
  const pending: unknown[] = [value], seen = new WeakSet<object>();
  while (pending.length) {
    const item = pending.pop();
    if (!item || typeof item !== 'object' || seen.has(item)) continue;
    seen.add(item);
    for (const [key, descriptor] of Object.entries(Object.getOwnPropertyDescriptors(item))) {
      if (!Object.hasOwn(descriptor, 'value')) continue;
      if (key === 'authority' && descriptor.value === 'simulation-only') throw new SimulationOnlyAuthorityError();
      pending.push(descriptor.value);
    }
  }
}
export class SimulationOnlyAuthorityError extends Error {
  constructor() { super('simulation-only/v1/no-authority'); }
}
