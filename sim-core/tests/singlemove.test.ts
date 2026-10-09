import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { validateRawProtocolRecord } from '../src/observable_state';
import { PROTOCOL_CONTRACT } from '../src/protocol_contract';
import { PlayerStateExtractor } from '../src/state_extractor';

const PLAYERS = ['p1', 'p2'] as const;
const SOURCES = [
  { move: 'destinybond', seed: 147, species: 'Froslass', suffix: 'Destiny Bond', next: 'poltergeist' },
  { move: 'glaiverush', seed: 79, species: 'Baxcalibur', suffix: 'Glaive Rush|[silent]', next: 'earthquake' },
] as const;

const ANIM_SOURCES = [
  { id: 'solarbeam', label: 'Solar Beam', seed: 93, slot: 4, species: 'Sunflora', setup: 'sunnyday' },
  { id: 'meteorbeam', label: 'Meteor Beam', seed: 22, slot: 4, species: 'Armarouge', setup: undefined },
  { id: 'dragondarts', label: 'Dragon Darts', seed: 59, slot: 2, species: 'Dragapult', setup: undefined },
] as const;

function generatedAnimSource(source: typeof ANIM_SOURCES[number]) {
  const pokemon = Teams.generate('gen9randombattle', { seed: [source.seed, 2, 3, 4] })[source.slot];
  assert.equal(pokemon.species, source.species);
  assert.ok(pokemon.moves.includes(source.id));
  if (source.id === 'meteorbeam') assert.equal(pokemon.item, 'Power Herb');
  return pokemon;
}

for (const source of ANIM_SOURCES) for (const actor of PLAYERS) {
  test(`${source.label} emits its exact public raw animation for ${actor}`, () => {
    const own = generatedAnimSource(source);
    const foe = Teams.import('Snorlax\nAbility: Immunity\n- Splash\n')![0];
    const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
    battle.setPlayer('p1', { team: [actor === 'p1' ? own : foe] });
    battle.setPlayer('p2', { team: [actor === 'p2' ? own : foe] });
    const choice = (pokemon: typeof own, move: string) => `move ${pokemon.moves.indexOf(move) + 1}`;
    try {
      if (source.setup) battle.makeChoices(
        actor === 'p1' ? choice(own, source.setup) : 'move 1',
        actor === 'p2' ? choice(own, source.setup) : 'move 1',
      );
      battle.makeChoices(
        actor === 'p1' ? choice(own, source.id) : 'move 1',
        actor === 'p2' ? choice(own, source.id) : 'move 1',
      );
      const target = actor === 'p1' ? 'p2a: Snorlax' : 'p1a: Snorlax';
      const record = `|-anim|${actor}a: ${source.species}|${source.label}|${target}`;
      assert.ok(battle.log.includes(record), 'pinned simulator must emit the exact source form');
      assert.doesNotThrow(() => validateRawProtocolRecord(record));
      assert.doesNotThrow(() => projectPipelineProtocolPrefix([record]));
      if (source.id === 'dragondarts') for (const malformed of [
        record + '|[still]', record.replace(target, `${actor}a: Snorlax`), record.replace('Dragon Darts', 'Dragon Darts '),
      ]) {
        assert.throws(() => validateRawProtocolRecord(malformed), malformed);
        assert.throws(() => projectPipelineProtocolPrefix([malformed]), malformed);
      }
    } finally {
      battle.destroy();
    }
  });
}

test('animation controls are table-driven raw-only evidence for both perspectives', () => {
  const controls = PROTOCOL_CONTRACT.valid_record_controls.filter((control) => control.token === '-anim');
  assert.deepEqual(controls.map((control) => [control.record.split('|')[3]]), PROTOCOL_CONTRACT.validation_rules.anim.forms);
  for (const actor of PLAYERS) for (const control of controls) {
    const record = actor === 'p1' ? control.record : control.record
      .replace('p1a: Pikachu', 'p2a: Pikachu').replace('p2a: Eevee', 'p1a: Eevee');
    assert.doesNotThrow(() => validateRawProtocolRecord(record));
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
  }
});

test('all source singlemove suffixes are exact raw-only evidence before extraction', () => {
  const controls = PROTOCOL_CONTRACT.valid_record_controls.filter(c => c.token === '-singlemove');
  assert.deepEqual(controls.map(c => c.record.split('|').slice(3)), PROTOCOL_CONTRACT.validation_rules.singlemove.forms);
  for (const perspective of PLAYERS) {
    const extractor = new PlayerStateExtractor('singlemove-raw', 'gen9randombattle', perspective);
    extractor.consumeChunk('|switch|p1a: Pikachu|Pikachu, L80|100/100\n|switch|p2a: Eevee|Eevee, L80|100/100');
    const before = structuredClone(extractor.getView());
    for (const control of controls) for (const target of ['p1a: Pikachu', 'p2a: Eevee']) {
      const record = control.record.replace('p1a: Pikachu', target);
      assert.doesNotThrow(() => validateRawProtocolRecord(record));
      assert.deepEqual(projectPipelineProtocolPrefix([record, record]), [record, record]);
      extractor.consumeChunk(record);
      assert.deepEqual(extractor.getView(), before, 'raw evidence must not fabricate typed state or action facts');
    }
    for (const fixture of PROTOCOL_CONTRACT.rejection_fixtures.filter(f => f.record.startsWith('|-singlemove'))) {
      assert.throws(() => extractor.consumeChunk(fixture.record), fixture.record);
      assert.throws(() => projectPipelineProtocolPrefix([fixture.record]), fixture.record);
      assert.deepEqual(extractor.getView(), before, 'malformed record must not mutate extraction');
    }
  }
});

// Generated seeds witness direct pool reachability. The one-Pokemon fixture and
// passive Snorlax opponent are controlled callback witnesses, not full random episodes.
for (const source of SOURCES) for (const actor of PLAYERS) {
  for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
    test(`${source.move} ${actor} ${version}: source emission, expiry, restore and terminal publication`, async () => {
      const own = Teams.generate('gen9randombattle', { seed: [source.seed, 2, 3, 4] })[0];
      assert.equal(own.species, source.species);
      assert.ok(own.moves.includes(source.move));
      const other = Teams.import('Snorlax\nAbility: Immunity\n- Splash\n- Crunch\n')![0];
      const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
      battle.setPlayer('p1', { team: [actor === 'p1' ? own : other] });
      battle.setPlayer('p2', { team: [actor === 'p2' ? own : other] });
      const data = structuredClone(battle.toJSON());
      const reset = LocalBattleEnv.prototype.resetWithOptions;
      const sessions: Awaited<ReturnType<typeof createPipelineIntegrationSession>>[] = [];
      try {
        LocalBattleEnv.prototype.resetWithOptions = function (options) {
          return this.resetFromSerialized(structuredClone(data), options);
        };
        for (let i = 0; i < 2; i++) sessions.push(await createPipelineIntegrationSession({
          battle_id: `singlemove-${source.move}-${actor}-${version}`,
          format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: version,
        }));
      } finally {
        LocalBattleEnv.prototype.resetWithOptions = reset;
      }
      const expectedRecord = `|-singlemove|${actor}a: ${source.species}|${source.suffix}`;
      const frozenFrames: { value: unknown; json: string }[] = [];
      const bundles: unknown[] = [];
      const step = async (move: string, opponentMove: string) => {
        const ownChoice = `move ${own.moves.indexOf(move) + 1}`;
        const choices = actor === 'p1' ? { p1: ownChoice, p2: opponentMove } : { p1: opponentMove, p2: ownChoice };
        battle.makeChoices(choices.p1, choices.p2);
        const results: Awaited<ReturnType<(typeof sessions)[number]['step']>>[] = [];
        for (const session of sessions) {
          const actions = Object.fromEntries(PLAYERS.map(player => {
            const request = session.boundary.perspectives[player].observation.request!;
            const action = request.legal_actions.actions.find(candidate => candidate?.choice === choices[player]);
            assert.ok(action);
            return [player, canonicalActionFromLegalAction(request, action.index)];
          })) as Parameters<typeof session.step>[0];
          results.push(await session.step(actions));
        }
        // Every step restores its disposable simulator candidate; duplicate
        // sessions also establish deterministic request/observation/belief lineage.
        assert.deepEqual(results[0], results[1]);
        for (const player of PLAYERS) {
          const bundle = results[0].record_bundles[player];
          const observation = bundle.successor_observation;
          assert.ok(observation.protocol_prefix.includes(expectedRecord));
          assert.deepEqual(observation.protocol_prefix.slice(0, bundle.input_observation.event_cursor), bundle.input_observation.protocol_prefix);
          assert.equal(observation.event_cursor, observation.protocol_prefix.length);
          assert.deepEqual(bundle.successor_belief.source_protocol_prefix, observation.protocol_prefix);
          const publicTeam = player === actor ? observation.view.self_team : observation.view.opponent_team;
          assert.ok(!publicTeam.some(pokemon => pokemon.volatiles?.includes(source.move)));
          assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
          if (observation.request) assert.equal(observation.request.player, player);
          bundles.push(bundle);
          frozenFrames.push({ value: observation, json: JSON.stringify(observation) });
        }
        return results[0];
      };
      try {
        await step(source.move, 'move 1');
        assert.ok(battle.log.includes(expectedRecord), 'unmodified pinned callback emits exact grammar');
        assert.ok(battle[actor].active[0].volatiles[source.move], 'effect exists only in authoritative simulator');
        await step(source.next, source.move === 'destinybond' ? 'move 2' : 'move 1');
        assert.ok(!battle[actor].active[0].volatiles[source.move], 'next move removes effect without invented typed expiry');
        if (source.move === 'destinybond') {
          await step(source.move, 'move 2');
          assert.ok(battle.log.some(line => line.includes('|move: Destiny Bond')));
          assert.equal(battle.log.filter(line => line.startsWith('|faint|')).length, 2);
          assert.ok(battle.log.some(line => line.startsWith('|win|')));
        } else {
          for (let turn = 0; !battle.ended && turn < 8; turn++) await step(source.next, 'move 1');
          assert.ok(battle.log.some(line => line.startsWith('|win|')));
        }
        assert.ok(battle.ended);
        for (const player of PLAYERS) {
          const observation = sessions[0].boundary.perspectives[player].observation;
          assert.equal(observation.snapshot_phase, 'terminal');
          assert.ok(observation.protocol_prefix.some(line => line === '|tie' || line.startsWith('|win|')));
        }
        for (const frame of frozenFrames) assert.equal(JSON.stringify(frame.value), frame.json);
        const python = spawnSync(process.env.PYTHON || 'python3', ['-c', `import io,json,sys
from unittest.mock import patch
from neural.pipeline_record import main
from neural.ts_identity import verify_bundle_identities
for bundle in json.load(sys.stdin):
 verify_bundle_identities(bundle)
 out,err=io.StringIO(),io.StringIO()
 with patch('sys.stdin',io.StringIO(json.dumps(bundle))), patch('sys.stdout',out), patch('sys.stderr',err): result=main()
 assert result == 0 and out.getvalue(), (result,err.getvalue())
print('published')`], {
          input: JSON.stringify(bundles), encoding: 'utf8',
          env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
        });
        assert.equal(python.status, 0, python.stderr);
        assert.equal(python.stdout.trim(), 'published');
      } finally {
        battle.destroy();
        for (const session of sessions) await session.close();
      }
    });
  }
}
