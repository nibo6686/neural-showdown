import assert from 'node:assert/strict';
import test from 'node:test';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import { Battle, Teams } from 'pokemon-showdown';
import { projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { projectObservableBattleState, validateRawProtocolRecord } from '../src/observable_state';
import {validateObservableBattleState} from '../src/belief_state';
import {episodeEvidenceContentDigest as digest} from '../src/pipeline_episode_evidence';
import {carryTerminalOwner} from '../src/public_health';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';
import { assertPublicAbilityMatchesEvidence, ownedAbilityAfterSuffix } from '../src/public_ability';

const PLAYERS = ['p1', 'p2'] as const;

test('C22 partial terminal authority replays only independently supplied ability fields', () => {
  for (const actor of PLAYERS) for (const [ownerFields, suffix, expected] of [
    [{ability: null, base_ability: 'imposter'}, [`|-transform|${actor}a: Own|${opponent(actor)}a: Target`, `|faint|${actor}a: Own`], {ability: 'imposter', base_ability: 'imposter'}],
    [{ability: 'static', base_ability: null}, [`|-transform|${actor}a: Own|${opponent(actor)}a: Target`, `|-ability|${actor}a: Own|Air Lock`, `|win|One`], {ability: 'airlock', base_ability: null}],
    [{ability: null, base_ability: 'terashift'}, [`|detailschange|${actor}a: Own|Terapagos-Stellar`, `|win|One`], {ability: null, base_ability: null}],
  ] as const) {
    const prefix = [`|switch|${actor}a: Own|Ditto|100/100`];
    const row = {slot: 1, ident: `${actor}: Own`, name: 'Own', base_species: 'Ditto', active: false, fainted: true,
      transformed: false, item: null, ability_suppressed: false, ...expected, ability_state: expected.ability ? 'known' : 'unknown'};
    const predecessor = {schema_version: 'observable-battle-state/v2', battle_id: `partial-${actor}`, perspective: actor,
      protocol_prefix: prefix, request: {side: [{ident: `${actor}: Own`, active: true, item: null, ...ownerFields}]}, view: {self_team: [row]}};
    const view = {terminated: true, self_team: [structuredClone(row)], opponent_team: []};
    const context = {predecessor, before: {step_index: 0, branch_id: 'before', state_fingerprint: 'before'},
      transition: {step_index: 0, parent_branch_id: 'before', branch_id: 'after', input_state_fingerprint: 'before', output_state_fingerprint: 'after'},
      after: {step_index: 1, branch_id: 'after', state_fingerprint: 'after'}};
    const carry = (candidate: any) => carryTerminalOwner(context, {schema_version: predecessor.schema_version, battle_id: predecessor.battle_id,
      perspective: actor, request: null, protocol_prefix: [...prefix, ...suffix], view: candidate});
    carry(view); assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence([...prefix, ...suffix], view, null, actor));
    for (const field of ['ability', 'base_ability', 'ability_state']) {
      const candidate = structuredClone(view); (candidate.self_team[0] as any)[field] = field === 'ability_state' ? 'none' : 'levitate';
      carry(candidate); const before = structuredClone(candidate);
      assert.throws(() => assertPublicAbilityMatchesEvidence([...prefix, ...suffix], candidate, null, actor), /Public ability evidence mismatch/);
      assert.deepEqual(candidate, before);
    }
  }
});

test('C22 direct invalidation requires current and base authority in canonical observations', () => {
  const generated = Teams.generate('gen9randombattle', {seed: [9,2,3,4]})[4];
  const pythonCases: Array<{observation: any; reject: boolean}> = [];
  for (const actor of PLAYERS) {
    const battle = battleFor(actor, [generated], team('Pikachu\nAbility: Static\n- Splash'));
    try {
      const {extractChannelMessages} = require('pokemon-showdown/dist/sim/battle');
      const native = projectPipelineProtocolPrefix(extractChannelMessages(battle.log.join('\n'), [0])[0]);
      const synthetic = [`|switch|${actor}a: Source|Terapagos|100/100`, `|-ability|${actor}a: Source|Air Lock`];
      const cases = [
        {label: 'generated Imposter', prefix: native},
        {label: 'Transform preserves established base', prefix: [...synthetic, `|-transform|${actor}a: Source|${opponent(actor)}a: Target`]},
        {label: 'silent permanent form', prefix: [...synthetic, `|detailschange|${actor}a: Source|Terapagos-Stellar`]},
        {label: 'silent temporary form', prefix: [...synthetic, `|-formechange|${actor}a: Source|Terapagos-Stellar`]},
        {label: 'public current after Transform', prefix: [...native, `|-ability|${actor}a: Ditto|Static|[from] ability: Trace|[of] ${opponent(actor)}a: Pikachu`]},
        {label: 'plain current after Transform', prefix: [...native, `|-ability|${actor}a: Ditto|Air Lock`]},
        {label: 'plain current after temporary form', prefix: [...synthetic, `|-formechange|${actor}a: Source|Terapagos-Stellar`, `|-ability|${actor}a: Source|Air Lock`]},
        {label: 'public permanent replacement', prefix: [...synthetic, `|detailschange|${actor}a: Source|Terapagos-Stellar`, `|-ability|${actor}a: Source|Teraform Zero`]},
      ];
      for (const {label, prefix} of cases) for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
        const extractor = new PlayerStateExtractor(`invalidation-${actor}`, 'gen9randombattle', actor);
        extractor.consumeChunk(prefix.join('\n'));
        const view = extractor.getView();
        const input = {schema_version: version, source_kind: 'sim_core' as const, battle_id: `invalidation-${actor}`, perspective: actor,
          snapshot_phase: 'pre_decision' as const, protocol_prefix: prefix, view, request: null};
        const valid = projectObservableBattleState(input);
        validateObservableBattleState(valid);
        if (version.endsWith('v2')) pythonCases.push({observation: valid, reject: false});
        const row = valid.view.self_team[0];
        if (label === 'public current after Transform') {
          assert.equal(row.ability, 'static'); assert.equal(row.base_ability, null);
          const compatible = structuredClone(valid); compatible.view.self_team[0].ability_state = 'known';
          compatible.observation_id = `obs-${digest(Object.fromEntries(Object.entries(compatible).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key))))}`;
          validateObservableBattleState(compatible);
          if (version.endsWith('v2')) pythonCases.push({observation: compatible, reject: false});
        }
        const mutations: Array<(row: any) => void> = [
          (r) => {r.ability = 'levitate'; r.ability_state = 'known';},
          (r) => {r.base_ability = 'levitate';},
          (r) => {r.ability_state = row.ability ? 'unknown' : 'changed';},
          (r) => {r.ability_suppressed = true;},
          ...['ability', 'base_ability', 'ability_state', 'ability_suppressed'].map((key) => (r: any) => {delete r[key];}),
        ];
        for (const mutate of mutations) {
          const candidate = structuredClone(valid); mutate(candidate.view.self_team[0]);
          candidate.observation_id = `obs-${digest(Object.fromEntries(Object.entries(candidate).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key))))}`;
          const before = structuredClone(candidate);
          assert.throws(() => validateObservableBattleState(candidate), /Public ability evidence mismatch/, `${label}/${actor}/${version}`);
          assert.throws(() => projectObservableBattleState({...input, view: candidate.view as any}), /Public ability evidence mismatch/);
          assert.deepEqual(candidate, before);
          if (version.endsWith('v2')) pythonCases.push({observation: candidate, reject: true});
        }
      }
      const ownedExtractor = new PlayerStateExtractor(`owner-${actor}`, 'gen9randombattle', actor);
      ownedExtractor.consumeChunk(native.join('\n')); ownedExtractor.consumeChunk(`|request|${JSON.stringify(battle[actor].activeRequest)}`);
      const owned = ownedExtractor.getView(), request = ownedExtractor.getRequest()!;
      for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
        const observation = projectObservableBattleState({schema_version: version, source_kind: 'sim_core', battle_id: `owner-${actor}`, perspective: actor,
          snapshot_phase: 'pre_decision', protocol_prefix: native, view: owned, request});
        validateObservableBattleState(observation);
        if (version.endsWith('v2')) pythonCases.push({observation, reject: false});
      }
      for (const partial of [null, {side: []}, {side: [{ident: `${actor}: Ditto`}]}, {side: [{ident: `${actor}: Ditto`, base_ability: 'imposter'}]}]) {
        const candidate = structuredClone(owned);
        assert.throws(() => assertPublicAbilityMatchesEvidence(native, candidate as any, partial), /Public ability evidence mismatch/);
      }
    } finally {battle.destroy();}
  }
  const result = spawnSync(process.env.PYTHON || 'python3', ['-c', `import json,sys\nfrom neural.pipeline_record import _validate_episode_observation\nfrom neural.ts_identity import verify_observation\nfor case in json.load(sys.stdin):\n o=case['observation']; verify_observation(o,'canonical direct')\n try: _validate_episode_observation(o,o['perspective'],o['battle_id'],'direct authority')\n except ValueError as exc:\n  assert case['reject'] and 'Public ability evidence mismatch' in str(exc), str(exc)\n else: assert not case['reject'], 'false authority accepted'\n`], {
    input: JSON.stringify(pythonCases), encoding: 'utf8', timeout: 30_000,
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  console.log(`Direct authority controls: ${pythonCases.length} canonical Python v2 candidates; mirrored TS v1/v2`);
});

test('Trace requestless copied truth rejects false name and state without mutation', () => {
  for (const actor of PLAYERS) {
    const prefix = [`|switch|${actor}a: Gardevoir|Gardevoir, L83|100/100`,
      `|-ability|${actor}a: Gardevoir|Static|[from] ability: Trace|[of] ${opponent(actor)}a: Pikachu`];
    const extractor = new PlayerStateExtractor(`trace-requestless-${actor}`, 'gen9randombattle', actor);
    extractor.consumeChunk(prefix.join('\n'));
    const view = extractor.getView();
    assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence(prefix, view as any, null));
    assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence(prefix, view as any, {side: [{ident: `${actor}: Gardevoir`}]}));
    for (const [field, value] of [['ability', 'levitate'], ['ability', null], ['ability_state', 'unknown'],
      ['ability_state', 'none'], ['ability_state', 'suppressed']] as const) {
      const candidate = structuredClone(view);
      (candidate.self_team[0] as any)[field] = value;
      const before = structuredClone(candidate);
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, candidate as any, null), /Public ability evidence mismatch/);
      assert.deepEqual(candidate, before);
    }
    const cached = structuredClone(view); cached.self_team[0].ability_state = 'known';
    assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence(prefix, cached as any, null));
    for (const field of ['ability', 'ability_state', 'ability_suppressed']) {
      const candidate = structuredClone(view); delete (candidate.self_team[0] as any)[field];
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, candidate as any, null), /Public ability/);
    }
    for (const candidate of [{player: actor}, {player: actor, self_team: []},
      {player: actor, self_team: [], opponent_team: view.self_team}]) {
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, candidate, null), /exactly one/);
    }
    for (const cleanup of [`|switch|${actor}a: Bench|Eevee|100/100`, `|drag|${actor}a: Bench|Eevee|100/100`,
      `|faint|${actor}a: Gardevoir`]) {
      const cleaned = new PlayerStateExtractor(`trace-cleanup-${actor}-${cleanup}`, 'gen9randombattle', actor);
      cleaned.consumeChunk([...prefix, cleanup].join('\n'));
      const cleanedView = cleaned.getView();
      const row = cleanedView.self_team.find((pokemon) => pokemon.name === 'Gardevoir')!;
      assert.equal(row.ability, null); assert.equal(row.ability_state, 'unknown');
      assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence([...prefix, cleanup], cleanedView as any, null));
      row.ability = 'static'; row.ability_state = 'changed';
      assert.throws(() => assertPublicAbilityMatchesEvidence([...prefix, cleanup], cleanedView as any, null), /Public ability/);
    }
  }
});

function team(text: string) {
  return Teams.import(text)!;
}

function battleFor(actor: PlayerID, source: ReturnType<typeof team>, target: ReturnType<typeof team>) {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  battle.setPlayer('p1', { team: actor === 'p1' ? source : target });
  battle.setPlayer('p2', { team: actor === 'p2' ? source : target });
  return battle;
}

function opponent(actor: PlayerID): PlayerID {
  return actor === 'p1' ? 'p2' : 'p1';
}

test('generated Trace emits exact public copy evidence for both actors', () => {
  const generated = Teams.generate('gen9randombattle', { seed: [2, 2, 3, 4] })[2];
  assert.equal(generated.species, 'Gardevoir');
  assert.equal(generated.ability, 'Trace');
  for (const actor of PLAYERS) {
    const battle = battleFor(actor, [generated], team('Pikachu\nAbility: Static\n- Splash\n'));
    try {
      const target = opponent(actor);
      const record = `|-ability|${actor}a: Gardevoir|Static|[from] ability: Trace|[of] ${target}a: Pikachu`;
      assert.ok(battle.log.includes(record), record);
      assert.doesNotThrow(() => validateRawProtocolRecord(record));
      assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
      for (const perspective of PLAYERS) {
        const extractor = new PlayerStateExtractor(`trace-${actor}-${perspective}`, 'gen9randombattle', perspective);
        extractor.consumeChunk(battle.log.join('\n'));
        const viewed = (perspective === actor ? extractor.getView().self_team : extractor.getView().opponent_team)
          .find((pokemon) => pokemon.name === 'Gardevoir');
        assert.equal(viewed?.ability, 'static');
        assert.equal(viewed?.ability_state, 'changed');
        assert.equal(viewed?.base_ability, null);
      }
    } finally {
      battle.destroy();
    }
  }
});

test('generated Trace faint restores owned base instead of cached copied request ability', () => {
  const generated = Teams.generate('gen9randombattle', {seed: [2, 2, 3, 4]})[2];
  for (const actor of PLAYERS) {
    const battle = battleFor(actor, [generated], team('Pikachu\nLevel: 100\nEVs: 252 HP / 252 Atk\nAbility: Static\n- Explosion'));
    try {
      const extractor = new PlayerStateExtractor(`trace-terminal-faint-${actor}`, 'gen9randombattle', actor);
      extractor.consumeChunk(battle.log.join('\n'));
      extractor.consumeChunk(`|request|${JSON.stringify(battle[actor].activeRequest)}`);
      assert.equal(extractor.getView().self_team[0].ability, 'static');
      const cursor = battle.log.length;
      battle.makeChoices(actor === 'p1' ? 'move 3' : 'move 1', actor === 'p2' ? 'move 3' : 'move 1');
      assert.ok(battle.ended); assert.ok(battle[actor].pokemon[0].fainted);
      assert.equal(battle[actor].pokemon[0].ability, 'trace');
      extractor.consumeChunk(battle.log.slice(cursor).join('\n'));
      assert.equal(extractor.getView().self_team[0].ability, 'trace');
      assert.equal(extractor.getView().self_team[0].ability_state, 'known');
    } finally {battle.destroy();}
  }
});

for (const [seed, ability, suffix] of [
  [[16, 2, 3, 4], 'Air Lock', ''],
  [[2, 2, 3, 4], 'Intimidate', '|boost'],
] as const) {
  test(`generated public ${ability} template emits for both actors`, () => {
    const generated = Teams.generate('gen9randombattle', { seed: [...seed] }).find((set) => set.ability === ability);
    assert.ok(generated, `${ability} must be selected by the pinned generator`);
    for (const actor of PLAYERS) {
      const battle = battleFor(actor, [generated], team('Snorlax\nAbility: Immunity\n- Splash\n'));
      try {
        const record: string = `|-ability|${actor}a: ${generated.species}|${ability}${suffix}`;
        assert.ok(battle.log.includes(record), record);
        assert.doesNotThrow(() => validateRawProtocolRecord(record));
        assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
      } finally {
        battle.destroy();
      }
    }
  });
}

test('public ability grammar accepts only generated templates and bare compatibility reveal', () => {
  const valid = [
    '|-ability|p1a: Rayquaza|Air Lock',
    '|-ability|p2a: Arcanine|Intimidate|boost',
    '|-ability|p1a: Calyrex|Chilling Neigh|boost',
    '|-ability|p2a: Calyrex|Grim Neigh|boost',
    '|-ability|p1a: Gardevoir|Static|[from] ability: Trace|[of] p2a: Pikachu',
    '|ability|p2a: Rayquaza|Air Lock',
    '|-ability|p1a: Terapagos|Teraform Zero',
    '|ability|p1a: Terapagos|Teraform Zero',
    ...['Cornerstone', 'Hearthflame', 'Teal', 'Wellspring'].map((forme) => `|-ability|p1a: Ogerpon|Embody Aspect (${forme})|boost`),
  ];
  const rejected = [
    '|-ability|p1a: Pikachu|Static|[from] ability: Receiver|[of] p1a: Eevee',
    '|-ability|p1a: Pikachu|Static|[from] ability: Power of Alchemy|[of] p1a: Eevee',
    '|-ability|p1a: Pikachu|Insomnia|[from] move: Worry Seed',
    '|-endability|p1a: Pikachu|Static|[from] move: Worry Seed',
    '|-endability|p1a: Pikachu',
    '|-ability|p1a: Torkoal|Drought|[from] sunnyday|[fail]',
    '|ability|p1a: Pikachu|Static|[from] ability: Trace|[of] p2a: Eevee',
    '|ability|p1a: Pikachu|Static|boost',
    '|-ability|p1a: Pikachu|Static|[from] ability: Trace',
    '|-ability|p1a: Gardevoir|Static|[from] ability: Trace|[of] p1a: Eevee',
    '|-ability|p1a: Gardevoir|Definitely Not An Ability',
    '|ability|p1a: Gardevoir|Definitely Not An Ability',
    '|-ability|p1a: Pikachu|Static',
    '|ability|p1a: Pikachu|Static',
    '|-ability|p1a: Pikachu|Air Lock|boost',
    '|-ability|p1a: Calyrex|As One (Glastrier)|boost',
    '|-ability|p2a: Calyrex|As One (Spectrier)|boost',
    '|-ability|p1a: Terapagos|Teraform Zero|boost',
    '|-ability|p1a: Ogerpon|Embody Aspect (Teal)',
    '|-ability|p1a: Ogerpon|Embody Aspect (Sun)|boost',
    '|-ability|p1a: Gardevoir|Embody Aspect (Teal)|[from] ability: Trace|[of] p2a: Ogerpon',
    '|-ability|p1a: Gardevoir|Teraform Zero|[from] ability: Trace|[of] p2a: Terapagos',
  ];
  for (const record of valid) {
    assert.doesNotThrow(() => validateRawProtocolRecord(record), record);
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
  }
  for (const perspective of PLAYERS) {
    for (const record of rejected) {
      const extractor = new PlayerStateExtractor(`ability-reject-${perspective}-${record}`, 'gen9randombattle', perspective);
      extractor.consumeChunk('|switch|p1a: Pikachu|Pikachu, L80|100/100');
      const before = structuredClone(extractor.getView());
      assert.throws(() => validateRawProtocolRecord(record), record);
      assert.throws(() => projectPipelineProtocolPrefix([record]), record);
      assert.throws(() => extractor.consumeChunk(record), record);
      assert.deepEqual(extractor.getView(), before, record);
    }
  }
});

test('constructed replacement and suppression source forms remain rejected for both actors', () => {
  for (const actor of PLAYERS) {
    const target = opponent(actor);
    const source = team('Muk\nAbility: Stench\n- Worry Seed\n- Gastro Acid\n');
    const defender = team('Snorlax\nAbility: Immunity\n- Splash\n');
    const replacement = battleFor(actor, source, defender);
    const suppression = battleFor(actor, source, defender);
    try {
      replacement.makeChoices('move 1', 'move 1');
      const end = `|-endability|${target}a: Snorlax|Immunity|[from] move: Worry Seed`;
      const change = `|-ability|${target}a: Snorlax|Insomnia|[from] move: Worry Seed`;
      assert.ok(replacement.log.includes(end), end);
      assert.ok(replacement.log.includes(change), change);
      assert.throws(() => validateRawProtocolRecord(end));
      assert.throws(() => validateRawProtocolRecord(change));

      suppression.makeChoices(actor === 'p1' ? 'move 2' : 'move 1', actor === 'p2' ? 'move 2' : 'move 1');
      const suppressed = `|-endability|${target}a: Snorlax`;
      assert.ok(suppression.log.includes(suppressed), suppressed);
      assert.throws(() => validateRawProtocolRecord(suppressed));
    } finally {
      replacement.destroy();
      suppression.destroy();
    }
  }
});

test('ability lifecycle clears hidden transform/form truth and restores only public base evidence', () => {
  for (const perspective of PLAYERS) {
    const extractor = new PlayerStateExtractor(`ability-lifecycle-${perspective}`, 'gen9randombattle', perspective);
    extractor.consumeChunk([
      '|switch|p1a: Ditto|Ditto, L80|100/100',
      '|-ability|p1a: Ditto|Air Lock',
      '|switch|p2a: Garchomp|Garchomp, L80|100/100',
      '|-transform|p1a: Ditto|p2a: Garchomp',
    ].join('\n'));
    let ditto = (perspective === 'p1' ? extractor.getView().self_team : extractor.getView().opponent_team)
      .find((pokemon) => pokemon.name === 'Ditto');
    assert.equal(ditto?.ability, null);
    assert.equal(ditto?.base_ability, 'airlock');
    assert.equal(ditto?.ability_state, 'unknown');

    extractor.consumeChunk([
      '|switch|p1a: Eevee|Eevee, L80|100/100',
      '|switch|p1a: Ditto|Ditto, L80|100/100',
    ].join('\n'));
    ditto = (perspective === 'p1' ? extractor.getView().self_team : extractor.getView().opponent_team)
      .find((pokemon) => pokemon.name === 'Ditto');
    assert.equal(ditto?.ability, 'airlock');
    assert.equal(ditto?.ability_state, 'known');

    extractor.consumeChunk('|-formechange|p1a: Ditto|Ditto-Other');
    ditto = (perspective === 'p1' ? extractor.getView().self_team : extractor.getView().opponent_team)
      .find((pokemon) => pokemon.name === 'Ditto');
    assert.equal(ditto?.ability, null);
    assert.equal(ditto?.base_ability, null);
    assert.equal(ditto?.ability_state, 'unknown');
  }
});

test('malformed ability provenance neither infers hidden truth nor mutates committed extraction', () => {
  for (const perspective of PLAYERS) {
    const extractor = new PlayerStateExtractor(`ability-privacy-${perspective}`, 'gen9randombattle', perspective);
    extractor.consumeChunk('|switch|p2a: Pikachu|Pikachu, L80|100/100');

    const before = structuredClone(extractor.getView());
    assert.throws(() => extractor.consumeChunk('|-ability|p2a: Pikachu|Static|[from] ability: Trace'));
    assert.deepEqual(extractor.getView(), before);
  }
});


test('C22 plain and boost reveal requestless names survive last writer and cleanup', () => {
  for (const actor of PLAYERS) for (const [ability, suffix] of [['Air Lock', ''], ['Intimidate', '|boost']]) {
    const prefix = [`|switch|${actor}a: Source|Rayquaza|100/100`, `|-ability|${actor}a: Source|${ability}${suffix}`];
    const extractor = new PlayerStateExtractor(`reveal-${actor}-${ability}`, 'gen9randombattle', actor);
    extractor.consumeChunk(prefix.join('\n'));
    const view = extractor.getView();
    assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence(prefix, view as any, null));
    for (const [field, value] of [['ability', 'static'], ['ability', null], ['ability_state', 'unknown'], ['ability_state', 'none'], ['ability_suppressed', true]] as const) {
      const candidate = structuredClone(view); (candidate.self_team[0] as any)[field] = value;
      const before = structuredClone(candidate);
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, candidate as any, null), /Public ability/);
      assert.deepEqual(candidate, before);
    }
    for (const field of ['ability', 'ability_state', 'ability_suppressed']) {
      const candidate = structuredClone(view); delete (candidate.self_team[0] as any)[field];
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, candidate as any, null), /Public ability/);
    }
    for (const cleanup of [`|switch|${actor}a: Bench|Eevee|100/100`, `|drag|${actor}a: Bench|Eevee|100/100`, `|faint|${actor}a: Source`]) {
      const cleaned = new PlayerStateExtractor(`reveal-clean-${actor}`, 'gen9randombattle', actor);
      const records = [...prefix, `|-ability|${actor}a: Source|Pressure`, cleanup];
      cleaned.consumeChunk(records.join('\n')); const next = cleaned.getView();
      assert.equal(next.self_team[0].ability, ability.toLowerCase().replace(/ /g, ''));
      assert.doesNotThrow(() => assertPublicAbilityMatchesEvidence(records, next as any, null));
      next.self_team[0].ability = 'pressure';
      assert.throws(() => assertPublicAbilityMatchesEvidence(records, next as any, null), /Public ability/);
    }
  }
});

test('C22 generated Imposter public transform never reveals hidden target ability', () => {
  const generated = Teams.generate('gen9randombattle', {seed: [9,2,3,4]})[4];
  assert.equal(generated.ability, 'Imposter');
  for (const actor of PLAYERS) {
    const battle = battleFor(actor, [generated], team('Pikachu\nAbility: Static\n- Splash'));
    try {
      assert.equal(battle[actor].active[0].ability, 'static');
      for (const perspective of PLAYERS) {
        const extractor = new PlayerStateExtractor(`imposter-public-${actor}-${perspective}`, 'gen9randombattle', perspective);
        extractor.consumeChunk(battle.log.join('\n'));
        const row = (perspective === actor ? extractor.getView().self_team : extractor.getView().opponent_team).find((p) => p.name === 'Ditto')!;
        assert.equal(row.ability, null); assert.equal(row.base_ability, null); assert.equal(row.ability_state, 'unknown');
      }
    } finally {battle.destroy();}
  }
});

test('C22 generated Ogerpon replacement emits finite public template', () => {
  const generated = Teams.generate('gen9randombattle', {seed: [109,2,3,4]}).find((set) => set.ability === 'Defiant')!;
  for (const actor of PLAYERS) {
    const battle = battleFor(actor, [generated], team('Pikachu\nLevel: 1\nAbility: Static\n- Splash'));
    const restored = Battle.fromJSON(structuredClone(battle.toJSON()));
    try {
      const choices = actor === 'p1' ? ['move 2 terastallize', 'move 1'] : ['move 1', 'move 2 terastallize'];
      const cursor = battle.log.length; battle.makeChoices(...choices); restored.makeChoices(...choices);
      assert.deepEqual(battle.toJSON(), restored.toJSON());
      assert.equal(battle[actor].pokemon[0].ability, 'embodyaspectteal');
      assert.equal(battle[actor].pokemon[0].baseAbility, 'embodyaspectteal');
      const record = `|-ability|${actor}a: Ogerpon|Embody Aspect (Teal)|boost`;
      assert.ok(battle.log.slice(cursor).includes(record));
      assert.doesNotThrow(() => validateRawProtocolRecord(record));
      assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
    } finally {battle.destroy(); restored.destroy();}
  }
});


test('C22 owned form branch classifier preserves eligible pairs and invalidates replacement defaults', () => {
  for (const [species, ability] of [['Mimikyu-Busted', 'disguise'], ['Eiscue-Noice', 'iceface'], ['Eiscue', 'iceface'], ['Palafin-Hero', 'zerotohero']]) {
    const owner = {ident: 'p1: Own', ability, base_ability: ability, active: true};
    assert.deepEqual(ownedAbilityAfterSuffix(owner, [`|detailschange|p1a: Own|${species}`]), {ability, base_ability: ability, ability_state: 'known'});
    assert.deepEqual(ownedAbilityAfterSuffix({...owner, ability: 'static'}, [`|detailschange|p1a: Own|${species}`]), {ability: null, base_ability: null, ability_state: 'unknown'});
  }
  const owner = {ident: 'p1: Own', ability: 'static', base_ability: 'imposter', active: true};
  for (const command of ['switch', 'drag']) assert.equal(ownedAbilityAfterSuffix(owner, [`|${command}|p1a: Bench|Eevee|100/100`]).ability, 'imposter');
  assert.deepEqual(ownedAbilityAfterSuffix(owner, ['|-formechange|p1a: Own|Darmanitan-Zen']), {ability: 'static', base_ability: 'imposter', ability_state: 'known'});
});


test('C22 generated Trace respects operative Terapagos permanent default notrace guard', () => {
  const gardevoir = Teams.generate('gen9randombattle', {seed: [2,2,3,4]})[2];
  const terapagos = Teams.generate('gen9randombattle', {seed: [135,2,3,4]})[4];
  for (const actor of PLAYERS) {
    const lead = Teams.generate('gen9randombattle', {seed: [2,2,3,4]})[0];
    const battle = battleFor(actor, [lead, gardevoir], [terapagos]);
    try {
      assert.equal(battle[opponent(actor)].active[0].ability, 'terashell');
      const choices = actor === 'p1' ? ['move 1', 'move 1 terastallize'] : ['move 1 terastallize', 'move 1'];
      battle.makeChoices(...choices);
      battle.makeChoices(...(actor === 'p1' ? ['switch 2', 'move 1'] : ['move 1', 'switch 2']));
      const record = `|-ability|${actor}a: Gardevoir|Teraform Zero|[from] ability: Trace|[of] ${opponent(actor)}a: Terapagos`;
      assert.equal(battle.log.includes(record), false);
      assert.throws(() => validateRawProtocolRecord(record), /outside the dash_trace_copy source-proven domain/);
      assert.equal(battle[actor].active[0].ability, 'trace');
      assert.equal(battle[opponent(actor)].active[0].ability, 'teraformzero');
      assert.equal(battle[opponent(actor)].active[0].getAbility().flags.notrace, 1);
    } finally {battle.destroy();}
  }
});
