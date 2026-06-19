import assert from 'node:assert/strict';
import test from 'node:test';
import { PlayerStateExtractor } from '../src/state_extractor';

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
