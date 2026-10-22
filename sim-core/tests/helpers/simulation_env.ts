import { Battle } from 'pokemon-showdown';
import { LocalBattleEnv, type SimulationOnlyOptions } from '../../src/env_manager';
import type { StepResult, StepResultOptions } from '../../src/types';
import {createSeededBattleSnapshot} from '../../src/transition';

type Options = SimulationOnlyOptions & { step?: StepResultOptions };

/** Diagnostic serialization comparisons only: no held occurrence or restore ticket is minted. */
export function simulationSnapshotEnv(options: SimulationOnlyOptions): LocalBattleEnv {
  const env = LocalBattleEnv.createSimulationOnly(options);
  env.captureSeededSnapshot = (parent = null) => Object.assign(
    createSeededBattleSnapshot(env.format, env.seed, env.serializeBattle(), parent),
    {authority: 'simulation-only' as const},
  );
  return env;
}

export function simulationEnv(options: Options): LocalBattleEnv;
export function simulationEnv(snapshot: Battle | Record<string, unknown>, options: Options): Promise<{env: LocalBattleEnv; result: StepResult}>;
export function simulationEnv(snapshotOrOptions: Battle | Record<string, unknown> | Options, options?: Options): LocalBattleEnv | Promise<{env: LocalBattleEnv; result: StepResult}> {
  if (!options) return LocalBattleEnv.createSimulationOnly(snapshotOrOptions as Options);
  const env = LocalBattleEnv.createSimulationOnly(options);
  const snapshot = snapshotOrOptions instanceof Battle ? snapshotOrOptions.toJSON() : snapshotOrOptions;
  return env.resetFromSerialized(snapshot as Record<string, unknown>, options.step)
    .then(result => ({env, result}), async error => { await env.close(); throw error; });
}
