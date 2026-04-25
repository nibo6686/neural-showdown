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
