import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { LocalBattleEnv, TerminalRequestHistoryValidationError } from '../src/env_manager';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import { illusionBattle, lifecycleChoices, LIFECYCLE_OPTIONS as OPTIONS, LIFECYCLE_SEED as SEED, teraFaintBattle, teraIllusionBattle } from './helpers/state_lifecycle';
import type { PlayerID } from '../src/types';

async function terminalTeraSnapshot(): Promise<Record<string, any>> {
  const battle = teraFaintBattle('p1');
  const env = new LocalBattleEnv('terminal-history-source', 'gen9randombattle', SEED);
  try {
    let result = await env.resetFromSerialized(battle.toJSON(), OPTIONS);
    result = await env.stepWithOptions({ p1: 'move 1 terastallize', p2: 'move 1' }, OPTIONS);
    for (let turn = 0; turn < 4 && !result.terminated; turn++) {
      result = await env.stepWithOptions({ p1: 'move 1', p2: 'move 2' }, OPTIONS);
    }
    assert.equal(result.terminated, true);
    return env.serializeBattle() as Record<string, any>;
  } finally {
    battle.destroy();
    await env.close();
  }
}

function comparableStep(result: Awaited<ReturnType<LocalBattleEnv['stepWithOptions']>>) {
  return {
    ...result,
    env_id: '<environment>',
    // Independent runs may cross a wall-clock second. Match the seeded
    // identity contract; per-run exact-prefix assertions remain unchanged.
    log_delta: result.log_delta.map((line) => /^\|t:\|\d+$/.test(line) ? '|t:|<timestamp>' : line),
    views: Object.fromEntries(Object.entries(result.views).map(([player, view]) => [
      player,
      view ? { ...view, env_id: '<environment>' } : view,
    ])),
  };
}

test('terminal request history rejects consumed malformed data before replacing a live environment', async () => {
  const terminal = await terminalTeraSnapshot();
  const mutations: Array<{ name: string; path: string; mutate: (snapshot: Record<string, any>) => void }> = [
    { name: 'null roster entry', path: 'side.pokemon[0]', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0] = null; } },
    { name: 'numeric identity', path: 'ident', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].ident = 7; } },
    { name: 'numeric details', path: 'details', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].details = 7; } },
    { name: 'numeric condition', path: 'condition', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].condition = 7; } },
    { name: 'empty condition', path: 'condition', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].condition = ''; } },
    { name: 'string stats', path: 'stats', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].stats = 'bad'; } },
    { name: 'non-string move', path: 'moves[0]', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].moves[0] = 7; } },
    { name: 'string active marker', path: 'active', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].active = 'yes'; } },
    { name: 'numeric item', path: 'item', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].item = 7; } },
    { name: 'numeric ability', path: 'ability', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].ability = 7; } },
    { name: 'numeric tera type', path: 'teraType', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].teraType = 7; } },
    { name: 'empty roster', path: 'side.pokemon', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon = []; } },
    { name: 'oversize roster', path: 'side.pokemon', mutate: (snapshot) => {
      const roster = snapshot.__neural_terminal_request_history.requests.p2.side.pokemon;
      while (roster.length < 7) roster.push(structuredClone(roster[0]));
    } },
    { name: 'sparse roster', path: 'side.pokemon', mutate: (snapshot) => { delete snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0]; } },
    { name: 'null move', path: 'moves[0]', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].moves[0] = null; } },
    { name: 'sparse moves', path: 'moves[0]', mutate: (snapshot) => { delete snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].moves[0]; } },
    { name: 'missing stat', path: 'stats', mutate: (snapshot) => { delete snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].stats.atk; } },
    { name: 'extra stat', path: 'stats', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].stats.hp = 1; } },
    { name: 'NaN stat', path: 'stats.atk', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].stats.atk = Number.NaN; } },
    { name: 'infinite stat', path: 'stats.def', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].stats.def = Infinity; } },
    { name: 'unsafe stat', path: 'stats.spa', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].stats.spa = Number.MAX_SAFE_INTEGER + 1; } },
    { name: 'empty requests', path: 'requests', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests = {}; } },
    { name: 'invalid status', path: 'condition', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].condition = '2/3 xyz'; } },
    { name: 'invalid HP ratio', path: 'condition', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].condition = '3/2'; } },
    { name: 'invalid details level', path: 'details', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p2.side.pokemon[0].details = 'Skarmory, L0'; } },
    { name: 'invalid details tera type', path: 'details', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].details = 'Zoroark, tera:NotAType'; } },
    { name: 'bad addressed identity', path: 'ident', mutate: (snapshot) => { snapshot.__neural_terminal_request_history.requests.p1.side.pokemon[0].ident = 'p2: private-name'; } },
  ];
  for (const mutation of mutations) {
    const liveBattle = teraFaintBattle('p1');
    const twinBattle = teraFaintBattle('p1');
    const live = new LocalBattleEnv(`terminal-history-live-${mutation.name}`, 'gen9randombattle', SEED);
    const twin = new LocalBattleEnv(`terminal-history-twin-${mutation.name}`, 'gen9randombattle', SEED);
    try {
      const initial = await live.resetFromSerialized(liveBattle.toJSON(), OPTIONS);
      const twinInitial = await twin.resetFromSerialized(twinBattle.toJSON(), OPTIONS);
      assert.deepEqual(comparableStep(initial), comparableStep(twinInitial));
      const before = live.captureSeededSnapshot();
      const beforeSerialized = live.serializeBattle();
      const malformed = structuredClone(terminal);
      mutation.mutate(malformed);
      await assert.rejects(live.resetFromSerialized(malformed, OPTIONS), (error: unknown) => {
        assert.ok(error instanceof TerminalRequestHistoryValidationError);
        assert.equal(error.code, 'terminal-request-history/invalid');
        assert.ok(error.path.includes(mutation.path.split('.')[0]));
        assert.ok(error.reason.length > 0);
        assert.equal(error.message.includes('private-name'), false);
        return true;
      });
      const after = live.captureSeededSnapshot();
      assert.equal(after.state_fingerprint, before.state_fingerprint);
      assert.equal(after.branch_id, before.branch_id);
      assert.deepEqual(live.serializeBattle(), beforeSerialized);
      const continued = await live.stepWithOptions({ p1: 'move 1', p2: 'move 1' }, OPTIONS);
      const twinContinued = await twin.stepWithOptions({ p1: 'move 1', p2: 'move 1' }, OPTIONS);
      assert.deepEqual(comparableStep(continued), comparableStep(twinContinued));
    } finally {
      liveBattle.destroy(); twinBattle.destroy();
      await live.close(); await twin.close();
    }
  }
});

test('terminal request history migrates historical v1 data to a minimal deterministic payload', async () => {
  const historical = await terminalTeraSnapshot();
  for (const request of Object.values(historical.__neural_terminal_request_history.requests) as any[]) {
    request.active = [{ moves: [{ move: 'private move' }] }];
    request.side.name = 'private side name';
    for (const pokemon of request.side.pokemon) {
      pokemon.pokeball = 'private ball';
      pokemon.commanding = true;
      pokemon.reviving = true;
      pokemon.terastallized = pokemon.terastallized ? pokemon.teraType : '';
    }
  }
  const historicalFainted = historical.__neural_terminal_request_history.requests.p1.side.pokemon[0];
  historicalFainted.ident = 'p1: X';
  historicalFainted.details = 'Zoroark, M, shiny, tera:Fire';
  historicalFainted.condition = '0 fnt';
  // Showdown marks the former position active even in a forced-switch request.
  // The terminal reader must preserve this valid active-fainted legacy shape.
  historicalFainted.active = true;
  const first = new LocalBattleEnv('terminal-history-migration-one', 'gen9randombattle', SEED);
  const second = new LocalBattleEnv('terminal-history-migration-two', 'gen9randombattle', SEED);
  try {
    const restored = await first.resetFromSerialized(historical, OPTIONS);
    assert.equal(restored.requests.p1, null);
    assert.equal(restored.requests.p2, null);
    const canonical = first.serializeBattle() as Record<string, any>;
    const requests = canonical.__neural_terminal_request_history.requests;
    for (const request of Object.values(requests) as any[]) {
      assert.deepEqual(Object.keys(request), ['side']);
      assert.deepEqual(Object.keys(request.side), ['id', 'pokemon']);
      for (const pokemon of request.side.pokemon) {
        assert.deepEqual(Object.keys(pokemon), [
          'ident', 'details', 'condition', 'active', 'moves', 'stats', 'baseAbility', 'item', 'ability', 'teraType', 'terastallized',
        ]);
        assert.equal(typeof pokemon.terastallized, 'boolean');
      }
    }
    const replay = await second.resetFromSerialized(canonical, OPTIONS);
    assert.deepEqual(comparableStep(restored), comparableStep(replay));
    assert.equal(first.captureSeededSnapshot().state_fingerprint, second.captureSeededSnapshot().state_fingerprint);
    assert.deepEqual(second.serializeBattle(), canonical);
  } finally {
    await first.close(); await second.close();
  }
});

for (const actor of ['p1', 'p2'] as const) {
  const other = actor === 'p1' ? 'p2' : 'p1';

  test(`pinned Showdown keeps ${actor} Stellar Tera defensive types`, () => {
    const battle = teraFaintBattle(actor, 'Stellar');
    try {
      const choices = lifecycleChoices(actor, 'move 1 terastallize', 'move 1');
      battle.makeChoices(choices.p1, choices.p2);
      const pokemon = battle.sides[actor === 'p1' ? 0 : 1]!.active[0]!;
      assert.equal(pokemon.terastallized, 'Stellar');
      assert.deepEqual(pokemon.getTypes(), ['Dark']);
    } finally {
      battle.destroy();
    }
  });

  for (const teraType of ['Fire', 'Stellar'] as const) {
    const ownTeraTypes = teraType === 'Stellar' ? ['Dark'] : [teraType];
    const displayedTeraTypes = teraType === 'Stellar' ? ['Normal'] : [teraType];
    for (const reentry of ['switch', 'drag'] as const) {
      test(`public ${teraType} Tera survives ${actor} ${reentry} re-entry without resolving Illusion`, async () => {
      const battle = teraIllusionBattle(actor, teraType);
      const env = new LocalBattleEnv(`tera-${actor}-${reentry}`, 'gen9randombattle', SEED);
      const deterministic = new LocalBattleEnv(`tera-${actor}-${reentry}-repeat`, 'gen9randombattle', SEED);
      const restored = new LocalBattleEnv(`tera-${actor}-${reentry}-restored`, 'gen9randombattle', SEED);
      try {
        const serialized = battle.toJSON();
        let result = await env.resetFromSerialized(serialized, OPTIONS);
        const prefix = [...result.log_delta];
        let observations = projectPipelineStepResult(result, 'tera-reentry', projectPipelineProtocolPrefix(prefix));
        let deterministicResult = await deterministic.resetFromSerialized(serialized, OPTIONS);
        const deterministicPrefix = [...deterministicResult.log_delta];
        assert.deepEqual(
          projectPipelineStepResult(deterministicResult, 'tera-reentry', projectPipelineProtocolPrefix(deterministicPrefix)),
          observations,
        );
        const immutable = [{ observations, json: JSON.stringify(observations) }];
        const step = async (own: string, foe: string) => {
          const previous = observations;
          result = await env.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
          prefix.push(...result.log_delta);
          observations = projectPipelineStepResult(result, 'tera-reentry', projectPipelineProtocolPrefix(prefix));
          deterministicResult = await deterministic.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
          deterministicPrefix.push(...deterministicResult.log_delta);
          assert.deepEqual(
            projectPipelineStepResult(deterministicResult, 'tera-reentry', projectPipelineProtocolPrefix(deterministicPrefix)),
            observations,
          );
          for (const player of ['p1', 'p2'] as const) {
            assert.deepEqual(
              observations[player].protocol_prefix.slice(0, previous[player].event_cursor),
              previous[player].protocol_prefix,
            );
            for (const foe of observations[player].view.opponent_team) {
              assert.equal('moves' in foe, false); assert.equal('boosts' in foe, false);
              assert.equal('stats' in foe, false); assert.equal('ability' in foe, false);
              assert.equal('tera_type' in foe, false);
            }
          }
          immutable.push({ observations, json: JSON.stringify(observations) });
        };
        const ownFox = () => observations[actor].view.self_team.find((pokemon) => pokemon.name === 'Fox')!;
        const publicActive = () => observations[other].view.opponent_team.find((pokemon) => pokemon.active)!;

        await step('move 1 terastallize', 'move 1');
        assert.equal(ownFox().terastallized, true);
        assert.equal(ownFox().tera_type, teraType);
        assert.deepEqual(ownFox().types, ownTeraTypes);
        assert.equal(publicActive().terastallized, true);
        assert.deepEqual(publicActive().types, displayedTeraTypes);
        assert.ok(observations[other].view.opponent_team.every((pokemon) => pokemon.name !== 'Fox' && pokemon.species !== 'Zoroark'));

        if (reentry === 'switch') {
          await step('switch 2', 'move 1');
          assert.equal(publicActive().terastallized, false);
          assert.deepEqual(publicActive().types, ['Normal']);
          await step('switch 2', 'move 1');
        } else {
          // Whirlwind first drags in Mask, then its only teammate makes the
          // next forced entry deterministically return the Tera Fox appearance.
          await step('move 1', 'move 2');
          assert.equal(publicActive().terastallized, false);
          assert.deepEqual(publicActive().types, ['Normal']);
          await step('move 1', 'move 2');
        }
        assert.ok(result.log_delta.some((line) => line.startsWith(`|${reentry}|${actor}a: Mask|Snorlax, F, tera:${teraType}|`)));
        assert.equal(ownFox().terastallized, true);
        assert.equal(ownFox().tera_type, teraType);
        assert.deepEqual(ownFox().types, ownTeraTypes);
        assert.equal(publicActive().terastallized, true);
        assert.deepEqual(publicActive().types, displayedTeraTypes);
        assert.ok(observations[other].view.opponent_team.every((pokemon) => pokemon.name !== 'Fox' && pokemon.species !== 'Zoroark'));
        const ownMask = observations[actor].view.self_team.find((pokemon) => pokemon.name === 'Mask')!;
        assert.equal(ownMask.terastallized, false);
        assert.notEqual(ownMask.tera_type, teraType);

        const replay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
        assert.deepEqual(projectPipelineStepResult(replay, 'tera-reentry', projectPipelineProtocolPrefix(replay.log_delta)), observations);
        await step('move 1', 'move 3');
        const revealed = observations[other].view.opponent_team.find((pokemon) => pokemon.name === 'Fox')!;
        assert.equal(revealed.illusion_revealed, true);
        assert.equal(revealed.terastallized, true);
        assert.deepEqual(revealed.types, ownTeraTypes);
        const afterReveal = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
        assert.deepEqual(projectPipelineStepResult(afterReveal, 'tera-reentry', projectPipelineProtocolPrefix(afterReveal.log_delta)), observations);
        const original = LocalBattleEnv.prototype.resetWithOptions;
        const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
        try {
          try {
            LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(serialized, options); };
            sessions.push(
              await createPipelineIntegrationSession({ battle_id: 'tera-records', format: 'gen9randombattle', seed: SEED }),
              await createPipelineIntegrationSession({ battle_id: 'tera-records', format: 'gen9randombattle', seed: SEED }),
            );
          } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
          const choices = reentry === 'switch'
            ? [['move 1 terastallize', 'move 1'], ['switch 2', 'move 1'], ['switch 2', 'move 1'], ['move 1', 'move 3']]
            : [['move 1 terastallize', 'move 1'], ['move 1', 'move 2'], ['move 1', 'move 2'], ['move 1', 'move 3']];
          for (const [index, [own, foe]] of choices.entries()) {
            const outputs = await Promise.all(sessions.map(async (session) => {
              const selected = lifecycleChoices(actor, own, foe);
              const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
                const request = session.boundary.perspectives[player].observation.request!;
                const legal = request.legal_actions.actions.find((action) => action?.choice === selected[player])!;
                return [player, canonicalActionFromLegalAction(request, legal.index)];
              })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
              return session.step(actions);
            }));
            assert.deepEqual(outputs[0].record_bundles, outputs[1].record_bundles);
            for (const player of ['p1', 'p2'] as const) {
              const state = outputs[0].boundary.perspectives[player];
              assert.deepEqual(state.belief, outputs[1].boundary.perspectives[player].belief);
              for (const foeView of state.observation.view.opponent_team) assert.equal('tera_type' in foeView, false);
              const check = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
                input: JSON.stringify(outputs[0].record_bundles[player]), encoding: 'utf8',
                env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
              });
              assert.equal(check.status, 0, check.stderr);
            }
            if (index === 2) {
              const published = outputs[0].boundary.perspectives[other].observation.view.opponent_team.find((pokemon) => pokemon.active)!;
              assert.equal(published.terastallized, true);
              assert.deepEqual(published.types, displayedTeraTypes);
            }
          }
        } finally { for (const session of sessions) await session.close(); }
        for (const prior of immutable) assert.equal(JSON.stringify(prior.observations), prior.json);
      } finally { battle.destroy(); await env.close(); await deterministic.close(); await restored.close(); }
      });
    }

  test(`public ${teraType} Tera resets to native type after terminal ${actor} faint without losing known type`, async () => {
    const battle = teraFaintBattle(actor, teraType);
    const env = new LocalBattleEnv(`tera-faint-${actor}`, 'gen9randombattle', SEED);
    const twin = new LocalBattleEnv(`tera-faint-${actor}-repeat`, 'gen9randombattle', SEED);
    const restored = new LocalBattleEnv(`tera-faint-${actor}-restored`, 'gen9randombattle', SEED);
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      const serialized = battle.toJSON();
      let result = await env.resetFromSerialized(serialized, OPTIONS);
      let twinResult = await twin.resetFromSerialized(serialized, OPTIONS);
      const prefix = [...result.log_delta];
      const twinPrefix = [...twinResult.log_delta];
      let observations = projectPipelineStepResult(result, 'tera-faint', projectPipelineProtocolPrefix(prefix));
      const advance = async (own: string, foe: string) => {
        const before = observations;
        result = await env.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
        twinResult = await twin.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
        prefix.push(...result.log_delta); twinPrefix.push(...twinResult.log_delta);
        observations = projectPipelineStepResult(result, 'tera-faint', projectPipelineProtocolPrefix(prefix));
        assert.deepEqual(
          projectPipelineStepResult(twinResult, 'tera-faint', projectPipelineProtocolPrefix(twinPrefix)),
          observations,
        );
        for (const player of ['p1', 'p2'] as const) {
          assert.deepEqual(observations[player].protocol_prefix.slice(0, before[player].event_cursor), before[player].protocol_prefix);
          for (const foeView of observations[player].view.opponent_team) assert.equal('tera_type' in foeView, false);
        }
      };

      await advance('move 1 terastallize', 'move 1');
      const live = observations;
      const liveJson = JSON.stringify(live);
      const ownLive = live[actor].view.self_team.find((pokemon) => pokemon.name === 'Flare')!;
      const publicLive = live[other].view.opponent_team.find((pokemon) => pokemon.name === 'Flare')!;
      assert.equal(ownLive.terastallized, true); assert.deepEqual(ownLive.types, ownTeraTypes);
      assert.equal(publicLive.terastallized, true); assert.deepEqual(publicLive.types, ownTeraTypes);
      const middleSnapshot = env.serializeBattle() as Record<string, unknown>;
      assert.equal(middleSnapshot.__neural_terminal_request_history, undefined);
      const middleReplay = await restored.resetFromSerialized(middleSnapshot, OPTIONS);
      assert.deepEqual(projectPipelineStepResult(middleReplay, 'tera-faint', projectPipelineProtocolPrefix(middleReplay.log_delta)), observations);

      // The last request was emitted while Tera was active. The terminal faint
      // therefore proves own-request reconstruction cannot retain stale Tera.
      for (let turn = 0; turn < 4 && !result.terminated; turn++) {
        await advance('move 1', 'move 2');
      }
      assert.equal(result.terminated, true);
      assert.ok(result.log_delta.some((line) => line === `|faint|${actor}a: Flare`));
      const ownFainted = observations[actor].view.self_team.find((pokemon) => pokemon.name === 'Flare')!;
      const publicFainted = observations[other].view.opponent_team.find((pokemon) => pokemon.name === 'Flare')!;
      for (const pokemon of [ownFainted, publicFainted]) {
        assert.equal(pokemon.fainted, true); assert.equal(pokemon.terastallized, false);
        assert.deepEqual(pokemon.types, ['Dark']);
      }
      assert.equal(ownFainted.tera_type, teraType);
      assert.equal('tera_type' in publicFainted, false);
      for (const player of ['p1', 'p2'] as const) {
        assert.ok(observations[player].protocol_prefix.every((line) => !line.startsWith('|request|')));
      }
      const terminalSnapshot = env.serializeBattle() as Record<string, any>;
      assert.equal(terminalSnapshot.__neural_terminal_request_history.schema_version, 'terminal-request-history/v1');
      assert.equal(terminalSnapshot.__neural_terminal_request_history.requests[actor].side.id, actor);
      assert.equal(env.captureSeededSnapshot().state_fingerprint, twin.captureSeededSnapshot().state_fingerprint);
      const unknownHistory = structuredClone(terminalSnapshot);
      unknownHistory.__neural_terminal_request_history.schema_version = 'terminal-request-history/v0';
      const restoredFingerprint = restored.captureSeededSnapshot().state_fingerprint;
      await assert.rejects(restored.resetFromSerialized(unknownHistory, OPTIONS), /Unsupported terminal request history schema/);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, restoredFingerprint);
      const swappedHistory = structuredClone(terminalSnapshot);
      [swappedHistory.__neural_terminal_request_history.requests.p1, swappedHistory.__neural_terminal_request_history.requests.p2] = [
        swappedHistory.__neural_terminal_request_history.requests.p2,
        swappedHistory.__neural_terminal_request_history.requests.p1,
      ];
      await assert.rejects(restored.resetFromSerialized(swappedHistory, OPTIONS), /does not match its addressed side/);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, restoredFingerprint);
      const malformedHistory = structuredClone(terminalSnapshot);
      malformedHistory.__neural_terminal_request_history.requests[actor].side.pokemon = null;
      await assert.rejects(restored.resetFromSerialized(malformedHistory, OPTIONS), /does not match its addressed side/);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, restoredFingerprint);
      const nonterminalHistory = structuredClone(middleSnapshot) as Record<string, any>;
      nonterminalHistory.__neural_terminal_request_history = structuredClone(terminalSnapshot.__neural_terminal_request_history);
      await assert.rejects(restored.resetFromSerialized(nonterminalHistory, OPTIONS), /only valid for terminal snapshots/);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, restoredFingerprint);
      const terminalReplay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
      assert.deepEqual(
        projectPipelineStepResult(terminalReplay, 'tera-faint', projectPipelineProtocolPrefix(terminalReplay.log_delta)),
        observations,
      );
      assert.equal(JSON.stringify(live), liveJson);
      const original = LocalBattleEnv.prototype.resetWithOptions;
      try {
        LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(serialized, options); };
        sessions.push(
          await createPipelineIntegrationSession({ battle_id: 'tera-faint-records', format: 'gen9randombattle', seed: SEED }),
          await createPipelineIntegrationSession({ battle_id: 'tera-faint-records', format: 'gen9randombattle', seed: SEED }),
        );
      } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
      let terminalPublished = false;
      for (let turn = 0; turn < 5 && !terminalPublished; turn++) {
        const selected = lifecycleChoices(actor, turn === 0 ? 'move 1 terastallize' : 'move 1', turn === 0 ? 'move 1' : 'move 2');
        const outputs = await Promise.all(sessions.map(async (session) => {
          const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
            const request = session.boundary.perspectives[player].observation.request!;
            const legal = request.legal_actions.actions.find((action) => action?.choice === selected[player])!;
            return [player, canonicalActionFromLegalAction(request, legal.index)];
          })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
          return session.step(actions);
        }));
        assert.deepEqual(outputs[0].record_bundles, outputs[1].record_bundles);
        for (const player of ['p1', 'p2'] as const) {
          assert.deepEqual(outputs[0].boundary.perspectives[player].belief, outputs[1].boundary.perspectives[player].belief);
          const check = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(outputs[0].record_bundles[player]), encoding: 'utf8',
            env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(check.status, 0, check.stderr);
        }
        terminalPublished = outputs[0].boundary.kind === 'terminal';
      }
      assert.equal(terminalPublished, true);
    } finally {
      battle.destroy(); await env.close(); await twin.close(); await restored.close();
      for (const session of sessions) await session.close();
    }
  });

  test(`unrevealed Illusion ${actor} ${teraType} faint resets public Tera without changing its teammate`, async () => {
    const battle = teraIllusionBattle(actor, teraType);
    const env = new LocalBattleEnv(`tera-illusion-faint-${actor}`, 'gen9randombattle', SEED);
    const twin = new LocalBattleEnv(`tera-illusion-faint-${actor}-repeat`, 'gen9randombattle', SEED);
    const restored = new LocalBattleEnv(`tera-illusion-faint-${actor}-restored`, 'gen9randombattle', SEED);
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    try {
      const serialized = battle.toJSON();
      let result = await env.resetFromSerialized(serialized, OPTIONS);
      let twinResult = await twin.resetFromSerialized(serialized, OPTIONS);
      const prefix = [...result.log_delta];
      const twinPrefix = [...twinResult.log_delta];
      let observations = projectPipelineStepResult(result, 'tera-illusion-faint', projectPipelineProtocolPrefix(prefix));
      const advance = async (own: string, foe: string) => {
        const before = observations;
        result = await env.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
        twinResult = await twin.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
        prefix.push(...result.log_delta); twinPrefix.push(...twinResult.log_delta);
        observations = projectPipelineStepResult(result, 'tera-illusion-faint', projectPipelineProtocolPrefix(prefix));
        assert.deepEqual(
          projectPipelineStepResult(twinResult, 'tera-illusion-faint', projectPipelineProtocolPrefix(twinPrefix)),
          observations,
        );
        for (const player of ['p1', 'p2'] as const) {
          assert.deepEqual(observations[player].protocol_prefix.slice(0, before[player].event_cursor), before[player].protocol_prefix);
          for (const foeView of observations[player].view.opponent_team) assert.equal('tera_type' in foeView, false);
        }
      };

      await advance('move 1 terastallize', 'move 1');
      const teraObservation = observations;
      const teraJson = JSON.stringify(teraObservation);
      assert.deepEqual(teraObservation[other].view.opponent_team.find((pokemon) => pokemon.active)!.types, displayedTeraTypes);
      await advance('move 2', 'move 1');
      assert.ok(result.log_delta.some((line) => line === `|faint|${actor}a: Mask`));
      assert.ok(prefix.every((line) => !line.startsWith(`|replace|${actor}a: Fox|`)));
      const ownFox = observations[actor].view.self_team.find((pokemon) => pokemon.name === 'Fox')!;
      const ownMask = observations[actor].view.self_team.find((pokemon) => pokemon.name === 'Mask')!;
      const publicMask = observations[other].view.opponent_team.find((pokemon) => pokemon.name === 'Mask')!;
      assert.equal(ownFox.fainted, true); assert.equal(ownFox.terastallized, false);
      assert.equal(ownFox.tera_type, teraType); assert.deepEqual(ownFox.types, ['Dark']);
      assert.equal(ownMask.fainted, false); assert.equal(ownMask.terastallized, false);
      assert.notEqual(ownMask.tera_type, teraType);
      assert.equal(publicMask.fainted, true); assert.equal(publicMask.terastallized, false);
      assert.deepEqual(publicMask.types, ['Normal']);
      assert.ok(observations[other].view.opponent_team.every((pokemon) => pokemon.name !== 'Fox' && pokemon.species !== 'Zoroark'));
      assert.equal(JSON.stringify(teraObservation), teraJson);
      const replay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
      assert.deepEqual(projectPipelineStepResult(replay, 'tera-illusion-faint', projectPipelineProtocolPrefix(replay.log_delta)), observations);

      const original = LocalBattleEnv.prototype.resetWithOptions;
      try {
        LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(serialized, options); };
        sessions.push(
          await createPipelineIntegrationSession({ battle_id: 'tera-illusion-faint-records', format: 'gen9randombattle', seed: SEED }),
          await createPipelineIntegrationSession({ battle_id: 'tera-illusion-faint-records', format: 'gen9randombattle', seed: SEED }),
        );
      } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
      for (const [own, foe] of [['move 1 terastallize', 'move 1'], ['move 2', 'move 1']]) {
        const outputs = await Promise.all(sessions.map(async (session) => {
          const selected = lifecycleChoices(actor, own, foe);
          const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
            const request = session.boundary.perspectives[player].observation.request!;
            const legal = request.legal_actions.actions.find((action) => action?.choice === selected[player])!;
            return [player, canonicalActionFromLegalAction(request, legal.index)];
          })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
          return session.step(actions);
        }));
        assert.deepEqual(outputs[0].record_bundles, outputs[1].record_bundles);
        for (const player of ['p1', 'p2'] as const) {
          assert.deepEqual(outputs[0].boundary.perspectives[player].belief, outputs[1].boundary.perspectives[player].belief);
          const check = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(outputs[0].record_bundles[player]), encoding: 'utf8',
            env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(check.status, 0, check.stderr);
        }
      }
    } finally {
      battle.destroy(); await env.close(); await twin.close(); await restored.close();
      for (const session of sessions) await session.close();
    }
  });

  }

  test(`Illusion ${actor} can depart unrevealed without contaminating its impersonated teammate`, async () => {
    const battle = illusionBattle(actor);
    const env = new LocalBattleEnv('unrevealed', 'gen9randombattle', SEED);
    const restored = new LocalBattleEnv('unrevealed-replay', 'gen9randombattle', SEED);
    try {
      const initial = await env.resetFromSerialized(battle.toJSON(), OPTIONS);
      const prefix = [...initial.log_delta];
      const boosted = await env.stepWithOptions(lifecycleChoices(actor, 'move 1'), OPTIONS);
      prefix.push(...boosted.log_delta);
      const before = projectPipelineStepResult(boosted, 'unrevealed', projectPipelineProtocolPrefix(prefix));
      const next = await env.stepWithOptions(lifecycleChoices(actor, 'switch 2'), OPTIONS);
      prefix.push(...next.log_delta);
      const observations = projectPipelineStepResult(next, 'unrevealed', projectPipelineProtocolPrefix(prefix));
      assert.ok(prefix.every((line) => !line.startsWith('|replace|')));
      const ownTeam = observations[actor].view.self_team;
      assert.equal(ownTeam[0].name, 'Mask'); assert.ok(ownTeam[0].active);
      for (const pokemon of ownTeam) {
        assert.deepEqual(pokemon.boosts, {}); assert.deepEqual(pokemon.volatiles, []);
      }
      assert.deepEqual(ownTeam[0].moves, ['amnesia', 'splash']);
      assert.ok(observations[other].view.opponent_team.every((p) => p.species !== 'Zoroark'));
      const replay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
      assert.deepEqual(projectPipelineStepResult(replay, 'unrevealed', projectPipelineProtocolPrefix(replay.log_delta)), observations);
      assert.deepEqual(observations[actor].protocol_prefix.slice(0, before[actor].event_cursor), before[actor].protocol_prefix);
      assert.equal(before[actor].view.self_team.find((p) => p.name === 'Fox')!.boosts!.spa, 2);
    } finally { battle.destroy(); await env.close(); await restored.close(); }
  });

  for (const knownTeammate of [false, true]) {
    test(`real Illusion ${actor}, known teammate ${knownTeammate}: ownership, reveal, departure/faint and replay`, async () => {
      const battle = illusionBattle(actor, knownTeammate);
      const env = new LocalBattleEnv('illusion-live', 'gen9randombattle', SEED);
      const restored = new LocalBattleEnv('illusion-restored', 'gen9randombattle', SEED);
      try {
        let result = await env.resetFromSerialized(battle.toJSON(), OPTIONS);
        const prefix = [...result.log_delta];
        let observations = projectPipelineStepResult(result, 'illusion', projectPipelineProtocolPrefix(prefix));
        const history = [{ observations, json: JSON.stringify(observations) }];
        const verifyReplay = async () => {
          const replay = await restored.resetFromSerialized(env.serializeBattle(), OPTIONS);
          const projected = projectPipelineStepResult(replay, 'illusion', projectPipelineProtocolPrefix(replay.log_delta));
          assert.deepEqual(projected, observations);
          assert.equal(restored.captureSeededSnapshot().state_fingerprint, env.captureSeededSnapshot().state_fingerprint);
        };
        const step = async (own: string, foe = 'move 1') => {
          const previous = observations;
          result = await env.stepWithOptions(lifecycleChoices(actor, own, foe), OPTIONS);
          prefix.push(...result.log_delta);
          observations = projectPipelineStepResult(result, 'illusion', projectPipelineProtocolPrefix(prefix));
          for (const p of ['p1', 'p2'] as const) {
            assert.deepEqual(observations[p].protocol_prefix.slice(0, previous[p].event_cursor), previous[p].protocol_prefix);
            assert.ok(observations[p].protocol_prefix.every((line) => !line.startsWith('|request|')));
            for (const foe of observations[p].view.opponent_team) {
              assert.equal('moves' in foe, false); assert.equal('boosts' in foe, false);
              assert.equal('stats' in foe, false); assert.equal('ability' in foe, false);
            }
          }
          history.push({ observations, json: JSON.stringify(observations) });
          await verifyReplay();
        };
        if (knownTeammate) {
          await step('move 1'); // Actual Snorlax uses Amnesia before being impersonated.
          await step('switch 2');
        }
        await step('move 1'); // Disguised Zoroark uses Nasty Plot.
        const ownFox = () => observations[actor].view.self_team.find((p) => p.name === 'Fox')!;
        const ownMask = () => observations[actor].view.self_team.find((p) => p.name === 'Mask')!;
        assert.equal(ownFox().species, 'Zoroark'); assert.equal(ownFox().displayed_species, 'Snorlax');
        assert.equal(ownFox().boosts!.spa, 2);
        assert.deepEqual(ownMask().boosts, {});
        assert.deepEqual(ownMask().moves, ['amnesia', 'splash']);
        assert.deepEqual(ownMask().revealed_moves, ['amnesia', 'splash']);
        const hidden = observations[other].view.opponent_team;
        assert.ok(hidden.every((p) => p.name !== 'Fox' && p.species !== 'Zoroark'));
        assert.ok(hidden.find((p) => p.active)!.displayed_species_uncertain);
        await step('move 2'); // Substitute survives Round because sound bypasses it.
        assert.deepEqual(ownFox().volatiles, ['substitute']);
        assert.deepEqual(ownMask().volatiles, []);
        const beforeReveal = observations;
        await step('move 3', 'move 2');
        assert.ok(result.log_delta.some((line) => line.startsWith(`|replace|${actor}a: Fox|Zoroark`) && line.split('|').length === 4));
        assert.ok(observations[actor].protocol_prefix.some((line) => line.startsWith('|-hint|')));
        assert.equal(ownFox().boosts!.spa, 2);
        assert.deepEqual(ownFox().volatiles, ['substitute']);
        assert.equal(ownFox().illusion_revealed, true);
        const publicFox = observations[other].view.opponent_team.find((p) => p.name === 'Fox')!;
        assert.equal(publicFox.species, 'Zoroark'); assert.equal(publicFox.illusion_revealed, true);
        assert.deepEqual(publicFox.volatiles, ['substitute']);
        assert.ok(beforeReveal[other].view.opponent_team.every((p) => p.species !== 'Zoroark'));
        if (knownTeammate) {
          const team = result.views[other]!.opponent_team;
          const mask = team.find((p) => p.name === 'Mask')!;
          const fox = team.find((p) => p.name === 'Fox')!;
          assert.equal(mask.active, false); assert.deepEqual(mask.boosts, {});
          assert.deepEqual(mask.revealed_moves, ['Amnesia']);
          assert.ok(!fox.revealed_moves.includes('Amnesia'));
          assert.equal(new Set(team.map((p) => p.slot)).size, team.length);
        }
        await step('switch 2');
        assert.deepEqual(ownFox().boosts, {}); assert.deepEqual(ownFox().volatiles, []);
        await step('switch 2'); // Illusion again; reveal must reuse the confirmed Fox entry.
        await step('move 1');
        await step('move 3', 'move 2');
        const foeTeam = observations[other].view.opponent_team;
        assert.equal(foeTeam.filter((p) => p.name === 'Fox').length, 1);
        assert.equal(foeTeam.filter((p) => p.name === 'Mask').length, 1);
        await step('move 3', 'move 3'); // Boomburst KOs the revealed Zoroark.
        assert.ok(ownFox().fainted);
        assert.deepEqual(ownFox().boosts, {}); assert.deepEqual(ownFox().volatiles, []);
        assert.equal(ownMask().fainted, false);
        for (const prior of history) assert.equal(JSON.stringify(prior.observations), prior.json);
      } finally { battle.destroy(); await env.close(); await restored.close(); }
    });
  }

  test(`Illusion ${actor} publishes repeatable observations, beliefs and Python records through reveal`, async () => {
    const battle = illusionBattle(actor);
    const snapshot = battle.toJSON();
    const original = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
    const direct = new LocalBattleEnv('illusion-direct', 'gen9randombattle', SEED);
    try {
      try {
        LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(snapshot, options); };
        for (let i = 0; i < 2; i++) sessions.push(await createPipelineIntegrationSession({ battle_id: 'illusion-records', format: 'gen9randombattle', seed: SEED }));
      } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
      const initial = await direct.resetFromSerialized(snapshot, OPTIONS);
      const prefix = [...initial.log_delta];
      for (const [own, foe] of [['move 1', 'move 1'], ['move 2', 'move 1'], ['move 3', 'move 2']]) {
        const choices = lifecycleChoices(actor, own, foe);
        const outputs: Awaited<ReturnType<(typeof sessions)[number]['step']>>[] = [];
        for (const session of sessions) {
          const actions = Object.fromEntries((['p1', 'p2'] as const).map((p) => {
            const r = session.boundary.perspectives[p].observation.request!;
            const legal = r.legal_actions.actions.find((a) => a?.choice === choices[p])!;
            return [p, canonicalActionFromLegalAction(r, legal.index)];
          })) as Record<PlayerID, ReturnType<typeof canonicalActionFromLegalAction>>;
          outputs.push(await session.step(actions));
        }
        assert.deepEqual(outputs[0].record_bundles, outputs[1].record_bundles);
        const next = await direct.stepWithOptions(choices, OPTIONS); prefix.push(...next.log_delta);
        const observations = projectPipelineStepResult(next, 'illusion-records', projectPipelineProtocolPrefix(prefix));
        for (const p of ['p1', 'p2'] as const) {
          const state = outputs[0].boundary.perspectives[p];
          assert.deepEqual(state.observation, observations[p]);
          assert.equal(state.belief.observation.observation_id, state.observation.observation_id);
          assert.equal(state.belief.transition_lineage?.transition_id, outputs[0].transition_id);
          assert.deepEqual(state.belief, outputs[1].boundary.perspectives[p].belief);
          const check = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
            input: JSON.stringify(outputs[0].record_bundles[p]), encoding: 'utf8',
            env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
          });
          assert.equal(check.status, 0, check.stderr);
        }
      }
    } finally { battle.destroy(); await direct.close(); for (const session of sessions) await session.close(); }
  });
}
