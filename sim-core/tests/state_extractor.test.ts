import assert from 'node:assert/strict';
import test from 'node:test';
import { PlayerStateExtractor } from '../src/state_extractor';

for (const player of ['p1', 'p2'] as const) {
  test(`lifecycle clearing preserves permanent evidence and Illusion replacement for ${player}`, () => {
    const extractor = new PlayerStateExtractor('retention', 'gen9randombattle', player);
    extractor.consumeChunk([
      '|switch|p1a: Zoroark|Zoroark, L80|100/100',
      '|-status|p1a: Zoroark|brn',
      '|-item|p1a: Zoroark|Leftovers',
      '|-boost|p1a: Zoroark|atk|2',
      '|-start|p1a: Zoroark|Substitute',
      '|replace|p1a: Zoroark|Zoroark, L80|100/100 brn',
    ].join('\n'));
    const team = () => player === 'p1' ? extractor.getView().self_team : extractor.getView().opponent_team;
    assert.deepEqual(team()[0].boosts, { atk: 2 });
    assert.deepEqual(team()[0].volatiles, ['substitute']);
    extractor.consumeChunk('|switch|p1a: Snorlax|Snorlax, L80|100/100');
    assert.deepEqual(team()[0].boosts, {});
    assert.deepEqual(team()[0].volatiles, []);
    assert.equal(team()[0].status, 'brn');
    assert.equal(team()[0].item, 'leftovers');
    extractor.consumeChunk('|switch|p1a: Zoroark|Zoroark, L80|100/100 brn');
    assert.deepEqual(team()[0].boosts, {});
    assert.deepEqual(team()[0].volatiles, []);
    assert.equal(team()[0].status, 'brn');
  });
}

test('clearVolatile exception preserves only publicly known Eternamax Dynamax (outside random-battle scope)', () => {
  const extractor = new PlayerStateExtractor('eternamax-retention', 'gen9customgame', 'p1');
  extractor.consumeChunk([
    '|switch|p2a: Eternatus|Eternatus-Eternamax|100/100',
    '|-start|p2a: Eternatus|Dynamax',
    '|-start|p2a: Eternatus|Substitute',
    '|-boost|p2a: Eternatus|atk|2',
    '|faint|p2a: Eternatus',
  ].join('\n'));
  const pokemon = extractor.getView().opponent_team[0];
  assert.deepEqual(pokemon.volatiles, ['dynamax']);
  assert.deepEqual(pokemon.boosts, {});
});

test('state extractor keeps player views public on the opponent side', () => {
  const extractor = new PlayerStateExtractor('env-1', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|player|p1|Agent-1|1|',
    '|player|p2|Agent-2|2|',
    '|teamsize|p1|6',
    '|teamsize|p2|6',
    '|gen|9',
    '|poke|p2|Gliscor|item',
    '|switch|p2a: Gliscor|Gliscor, L76, M|100/100',
    '|request|{"active":[{"moves":[{"move":"Fire Blast","id":"fireblast","pp":8,"maxpp":8,"target":"normal","disabled":false}],"canTerastallize":"Fire"}],"side":{"name":"Agent-1","id":"p1","pokemon":[{"ident":"p1: Typhlosion","details":"Typhlosion, L84, M","condition":"267/267","active":true,"stats":{"atk":146,"def":179,"spa":231,"spd":191,"spe":216},"moves":["fireblast"],"baseAbility":"flashfire","item":"choicescarf","pokeball":"pokeball","ability":"flashfire","teraType":"Fire","terastallized":""}]}}',
  ].join('\n'));

  const view = extractor.getView();
  assert.equal(view.self_team[0].item, 'choicescarf');
  assert.equal(view.opponent_team[0].species, 'Gliscor');
  assert.equal(view.opponent_team[0].item, 'has-item');
  assert.equal(view.opponent_team[0].ability, null);
});

test('state extractor exposes own request details without leaking unrevealed opponent details', () => {
  const extractor = new PlayerStateExtractor('env-privacy', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|player|p1|Alice|1|',
    '|player|p2|Bob|2|',
    '|teamsize|p1|6',
    '|teamsize|p2|6',
    '|poke|p2|Dragonite|item',
    '|poke|p2|Gholdengo|item',
    '|switch|p2a: Dragonite|Dragonite, L80, M|100/100',
    '|request|{"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt","pp":23,"maxpp":24,"target":"normal","disabled":false}],"canTerastallize":"Electric"}],"side":{"name":"Alice","id":"p1","pokemon":[{"ident":"p1: Pikachu","details":"Pikachu, L80, M","condition":"200/200","active":true,"stats":{"atk":146,"def":120,"spa":196,"spd":140,"spe":216},"moves":["thunderbolt"],"baseAbility":"static","ability":"static","item":"choicespecs","teraType":"Electric"},{"ident":"p1: Blissey","details":"Blissey, L80, F","condition":"300/300","active":false,"stats":{},"moves":["softboiled"],"baseAbility":"naturalcure","ability":"naturalcure","item":"leftovers","teraType":"Fairy"}]}}',
  ].join('\n'));

  const view = extractor.getView();
  const request = extractor.getRequest();
  assert.equal(view.opponent_team.length, 2);
  for (const opponent of view.opponent_team) {
    assert.deepEqual(opponent.moves, []);
    assert.deepEqual(opponent.revealed_moves, []);
    assert.equal(opponent.ability, null);
    assert.equal(opponent.tera_type, null);
    assert.ok(opponent.item === null || opponent.item === 'has-item');
    assert.deepEqual(opponent.stats, {});
  }
  assert.equal(request?.side[0].item, 'choicespecs');
  assert.equal(request?.side[0].ability, 'static');
  assert.equal(request?.side[0].tera_type, 'Electric');
  assert.equal(request?.active?.moves[0].pp, 23);
  assert.equal(request?.active?.can_terastallize, true);
  assert.ok(request?.legal_actions.available_indices.includes(0));
  assert.ok(request?.legal_actions.available_indices.includes(4));
  assert.ok(request?.legal_actions.available_indices.includes(8));
});

test('state extractor merges active-slot protocol idents with request team idents', () => {
  const extractor = new PlayerStateExtractor('env-boosts', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|request|{"active":[{"moves":[{"move":"Draco Meteor","id":"dracometeor","pp":8,"maxpp":8,"target":"normal","disabled":false}]}],"side":{"name":"Alice","id":"p1","pokemon":[{"ident":"p1: Exeggutor","details":"Exeggutor-Alola, L89, M","condition":"314/314","active":true,"stats":{"spa":273},"moves":["dracometeor"],"baseAbility":"harvest","ability":"harvest","item":"sitrusberry","teraType":"Fire"}]}}',
    '|move|p1a: Exeggutor|Draco Meteor|p2a: Hydrapple',
    '|-unboost|p1a: Exeggutor|spa|2',
    '|request|{"active":[{"moves":[{"move":"Draco Meteor","id":"dracometeor","pp":7,"maxpp":8,"target":"normal","disabled":false}]}],"side":{"name":"Alice","id":"p1","pokemon":[{"ident":"p1: Exeggutor","details":"Exeggutor-Alola, L89, M","condition":"289/314","active":true,"stats":{"spa":273},"moves":["dracometeor"],"baseAbility":"harvest","ability":"harvest","item":"sitrusberry","teraType":"Fire"}]}}',
  ].join('\n'));

  const view = extractor.getView();
  assert.equal(view.self_team.length, 1);
  assert.equal(view.self_team[0].active, true);
  assert.equal(view.self_team[0].boosts.spa, -2);
});

test('state extractor exposes public current type changes separately from species', () => {
  const extractor = new PlayerStateExtractor('env-types', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|switch|p2a: Charizard|Charizard, L80, M|100/100',
    '|-start|p2a: Charizard|typechange|Water|[from] move: Soak',
  ].join('\n'));

  const view = extractor.getView();
  assert.equal(view.opponent_team[0].species, 'Charizard');
  assert.deepEqual(view.opponent_team[0].types, ['Water']);
});

test('state extractor distinguishes removed and consumed items and ability suppression', () => {
  const removed = new PlayerStateExtractor('env-item-removed', 'gen9randombattle', 'p1');
  removed.consumeChunk([
    '|switch|p2a: Charizard|Charizard, L80, M|100/100',
    '|-item|p2a: Charizard|Heavy-Duty Boots',
    '|-enditem|p2a: Charizard|Heavy-Duty Boots|[from] move: Knock Off',
    '|-ability|p2a: Charizard|Blaze',
    '|-ability|p2a: Charizard|Insomnia|[from] move: Worry Seed',
    '|-endability|p2a: Charizard',
  ].join('\n'));

  const mon = removed.getView().opponent_team[0];
  assert.equal(mon.item, null);
  assert.equal(mon.last_item, 'heavydutyboots');
  assert.equal(mon.item_state, 'removed');
  assert.equal(mon.base_ability, 'blaze');
  assert.equal(mon.ability, 'insomnia');
  assert.equal(mon.ability_state, 'suppressed');
  assert.equal(mon.ability_suppressed, true);

  const consumed = new PlayerStateExtractor('env-item-consumed', 'gen9randombattle', 'p1');
  consumed.consumeChunk([
    '|switch|p2a: Pikachu|Pikachu, L80, M|100/100',
    '|-item|p2a: Pikachu|Sitrus Berry',
    '|-enditem|p2a: Pikachu|Sitrus Berry|[eat]',
  ].join('\n'));
  assert.equal(consumed.getView().opponent_team[0].item_state, 'consumed');
});

test('state extractor preserves base/current species, illusion display, and status evidence', () => {
  const extractor = new PlayerStateExtractor('env-species-status', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|turn|1',
    '|switch|p1a: Ditto|Ditto, L80|100/100',
    '|switch|p2a: Garchomp|Garchomp, L80, M|100/100',
    '|-transform|p1a: Ditto|p2a: Garchomp',
    '|-status|p1a: Ditto|brn',
    '|turn|3',
  ].join('\n'));

  const ditto = extractor.getView().self_team[0];
  assert.equal(ditto.base_species, 'Ditto');
  assert.equal(ditto.current_species, 'Garchomp');
  assert.equal(ditto.transformed, true);
  assert.equal(ditto.status, 'brn');
  assert.equal(ditto.status_source, 'protocol');
  assert.equal(ditto.status_turns_public, 2);

  const illusion = new PlayerStateExtractor('env-illusion', 'gen9randombattle', 'p1');
  illusion.consumeChunk([
    '|switch|p2a: Dragonite|Dragonite, L80, M|100/100',
    '|replace|p2a: Zoroark|Zoroark, L80, M|100/100',
  ].join('\n'));
  const revealed = illusion.getView().opponent_team[0];
  assert.equal(revealed.base_species, 'Zoroark');
  assert.equal(revealed.current_species, 'Zoroark');
  assert.equal(revealed.displayed_species, 'Dragonite');
  assert.equal(revealed.illusion_revealed, true);
  assert.equal(revealed.displayed_species_uncertain, false);
});

test('state extractor exposes Tera and named field state with perspective-normalized sides', () => {
  const p1 = new PlayerStateExtractor('env-tera-field-p1', 'gen9randombattle', 'p1');
  const p2 = new PlayerStateExtractor('env-tera-field-p2', 'gen9randombattle', 'p2');
  const protocol = [
    '|switch|p1a: Charizard|Charizard, L80, M|100/100',
    '|switch|p2a: Blastoise|Blastoise, L80, M|100/100',
    '|-terastallize|p1a: Charizard|Fire',
    '|-weather|RainDance',
    '|-fieldstart|move: Electric Terrain',
    '|-fieldstart|move: Trick Room',
    '|-fieldstart|move: Gravity',
    '|-sidestart|p1: Player|move: Reflect',
    '|-sidestart|p1: Player|move: Tailwind',
    '|-sidestart|p1: Player|move: Spikes',
    '|-sidestart|p1: Player|move: Spikes',
  ].join('\n');
  p1.consumeChunk(protocol);
  p2.consumeChunk(protocol);

  const p1View = p1.getView();
  const p2View = p2.getView();
  assert.equal(p1View.self_team[0].terastallized, true);
  assert.equal(p1View.self_team[0].tera_type, 'Fire');
  assert.deepEqual(p1View.self_team[0].types, ['Fire']);
  assert.equal(p1View.field.weather, 'raindance');
  assert.equal(p1View.field.terrain, 'electricterrain');
  assert.ok(p1View.field.pseudo_weather.includes('trickroom'));
  assert.ok(p1View.field.pseudo_weather.includes('gravity'));
  assert.equal(p1View.field.side_conditions.self.reflect, 1);
  assert.equal(p1View.field.side_conditions.self.tailwind, 1);
  assert.equal(p1View.field.side_conditions.self.spikes, 2);
  assert.equal(p2View.field.side_conditions.opponent.reflect, 1);
  assert.equal(p2View.field.side_conditions.opponent.tailwind, 1);
  assert.equal(p2View.field.side_conditions.opponent.spikes, 2);
});

test('volatile start/end records preserve confusion lifecycle for both perspectives without leaking requests', () => {
  const p1 = new PlayerStateExtractor('volatile-p1', 'gen9randombattle', 'p1');
  const p2 = new PlayerStateExtractor('volatile-p2', 'gen9randombattle', 'p2');
  const publicPrefix = [
    '|teamsize|p1|6', '|teamsize|p2|6',
    '|poke|p2|Pikachu', '|poke|p2|Gholdengo', '|switch|p2a: Pikachu|Pikachu, L80|100/100',
    '|-start|p2a: Pikachu|confusion',
    '|-start|p2a: Pikachu|substitute',
  ].join('\n');
  p1.consumeChunk(publicPrefix);
  p2.consumeChunk(publicPrefix);
  p1.consumeChunk('|-end|p2a: Pikachu|confusion');
  p2.consumeChunk('|-end|p2a: Pikachu|confusion');

  assert.deepEqual(p1.getView().opponent_team[0].volatiles, ['substitute']);
  assert.deepEqual(p2.getView().self_team[0].volatiles, ['substitute']);
  assert.equal(p1.getView().opponent_team.length, 2);
  assert.equal(p1.getView().team_size.p2, 6);
  assert.equal(p1.getView().opponent_team[0].status, null);
  assert.equal(p1.getView().opponent_team[0].status_source, 'protocol');
  assert.equal(p1.getView().opponent_team[1].status, null);
  assert.equal(p1.getView().opponent_team[1].status_source, 'unknown');

  const request = new PlayerStateExtractor('volatile-request', 'gen9randombattle', 'p1');
  request.consumeChunk('|request|{"active":[],"side":{"id":"p1","pokemon":[{"ident":"p1: Pikachu","details":"Pikachu, L80","condition":"100/100","active":true,"moves":[],"stats":{}}]}}');
  assert.equal(request.getView().self_team[0].status, null);
  assert.equal(request.getView().self_team[0].status_source, 'request');
});
