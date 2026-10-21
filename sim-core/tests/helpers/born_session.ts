import assert from 'node:assert/strict';
import {Teams} from 'pokemon-showdown';
import {canonicalActionFromLegalAction} from '../../src/canonical_action';
import {PipelineIntegrationSession, type PipelineIntegrationOptions} from '../../src/pipeline_integration';
import type {PlayerID} from '../../src/types';

type PokemonSet = ReturnType<typeof Teams.generate>[number];
export type BornTeams = Readonly<Record<PlayerID, string | readonly PokemonSet[]>>;
export type BornStep = Readonly<Partial<Record<PlayerID, string>>>;

/** Scope exact team generation to the two original submissions, even for episode runners. */
export async function withBornTeams<T>(teams: BornTeams, create: () => Promise<T>): Promise<T> {
  const generated = (['p1', 'p2'] as const).map(owner => {
    const team = typeof teams[owner] === 'string' ? Teams.import(teams[owner] as string) : teams[owner];
    assert.ok(team?.length, `nonempty born team for ${owner}`);
    return structuredClone(team) as PokemonSet[];
  });
  const generate = Teams.generate;
  let count = 0;
  Teams.generate = function () {
    const team = generated[count++];
    assert.ok(team, 'only two original team submissions');
    if (count === 2) Teams.generate = generate;
    return structuredClone(team);
  };
  try { return await create(); }
  finally { Teams.generate = generate; }
}

export function bornSession({teams, seed = [1, 2, 3, 4], options}: {
  teams: BornTeams;
  seed?: readonly number[];
  options: Omit<PipelineIntegrationOptions, 'seed' | 'format'> & {format?: string};
}): Promise<PipelineIntegrationSession> {
  return withBornTeams(teams, () => PipelineIntegrationSession.create({
    format: 'gen9randombattle', ...options, seed,
  }));
}

/** Resolve every script choice against its current owner request before submitting either side. */
export async function playTo(session: PipelineIntegrationSession, steps: readonly BornStep[]): Promise<PipelineIntegrationSession['boundary'][]> {
  const boundaries = [session.boundary];
  for (const step of steps) {
    const actions: Partial<NonNullable<Parameters<PipelineIntegrationSession['step']>[0]>> = {};
    for (const owner of ['p1', 'p2'] as const) {
      const text = step[owner];
      if (text === undefined) continue;
      const request = session.boundary.perspectives[owner].observation.request;
      assert.ok(request, `current request for ${owner}`);
      const action = request.legal_actions.actions.find(candidate => candidate?.choice === text);
      assert.ok(action, `${text} legal for ${owner}`);
      actions[owner] = canonicalActionFromLegalAction(request, action.index);
    }
    if (session.boundary.kind === 'joint_actionable') {
      assert.ok(actions.p1 && actions.p2, 'joint script supplies both owners');
      await session.step({p1: actions.p1, p2: actions.p2});
    } else {
      const selected = Object.values(actions);
      assert.equal(selected.length, 1, 'selection script supplies exactly one owner');
      if (session.boundary.kind === 'one_sided_revival') await session.stepRevival(selected[0]);
      else {
        assert.equal(session.boundary.kind, 'one_sided_forced_switch');
        await session.stepForcedSwitch(selected[0]);
      }
    }
    boundaries.push(session.boundary);
  }
  return boundaries;
}
