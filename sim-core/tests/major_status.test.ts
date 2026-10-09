import assert from 'node:assert/strict';
import test from 'node:test';
import { validateRawProtocolRecord } from '../src/observable_state';
import { PlayerStateExtractor } from '../src/state_extractor';

const applyForms = [
  '|-status|p1a: Target|brn',
  '|-status|p2a: Target|slp|[from] move: Rest',
  '|-status|p1a: Target|brn|[from] item: Flame Orb',
  '|-status|p2a: Target|tox|[from] item: Toxic Orb',
  '|-status|p1a: Target|par|[from] ability: Effect Spore|[of] p2a: Source',
  '|-status|p2a: Target|brn|[from] ability: Flame Body|[of] p1a: Source',
  '|-status|p1a: Target|par|[from] ability: Static|[of] p2a: Source',
  '|-status|p2a: Target|tox|[from] ability: Toxic Chain|[of] p1a: Source',
  '|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p2a: Source',
  '|-status|p2a: Target|slp|[from] move: Sleep Powder',
  '|-status|p1a: Target|slp|[from] move: Hypnosis',
  '|-status|p2a: Target|slp|[from] move: Spore',
];

const cureForms = [
  '|-curestatus|p1a: Target|brn|[msg]',
  '|-curestatus|p2a: Target|tox|[from] ability: Natural Cure',
  '|-curestatus|p1a: Target|frz|[from] move: Flare Blitz',
  '|-curestatus|p2a: Target|frz|[from] move: Fusion Flare',
  '|-curestatus|p1a: Target|frz|[from] move: Pyro Ball',
  '|-curestatus|p2a: Target|frz|[from] move: Sacred Fire',
  '|-curestatus|p1a: Target|frz|[from] move: Scald',
  '|-curestatus|p2a: Target|frz|[from] move: Scorching Sands',
  '|-curestatus|p1a: Target|frz|[from] move: Hydro Steam',
  '|-curestatus|p2a: Target|frz|[from] move: Matcha Gotcha',
  '|-curestatus|p1a: Target|frz|[from] move: Steam Eruption',
];

test('CE-04F2 admits only pinned public major-status source forms', () => {
  for (const line of [...applyForms, ...cureForms]) {
    assert.doesNotThrow(() => validateRawProtocolRecord(line), line);
  }
  for (const line of [
    '|-status|p1a: Target|fnt',
    '|-status|p1a: Target|slp|[from] move: Recover',
    '|-status|p1a: Target|brn|[from] item: Toxic Orb',
    '|-status|p1a: Target|brn|[from] ability: Static|[of] p2a: Source',
    '|-status|p1a: Target|par|[from] ability: Static|[of] p1a: Source',
    '|-curestatus|p1a: Target|brn',
    '|-curestatus|p1a: Target|frz|[from] move: Flamethrower',
    '|-curestatus|p1a: Target|frz|[msg]|[silent]',
    '|status|p1a: Target|brn|[msg]',
    '|status|p1a: Target|brn',
    '|curestatus|p2a: Target|tox',
    '|-status|p1a: Target|slp|[from] move: Yawn',
    '|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p1a: Source',
    '|-status|p1: Target|brn',
  ]) assert.throws(() => validateRawProtocolRecord(line));
});

for (const perspective of ['p1', 'p2'] as const) {
  test(`CE-04F2 applies, replaces, cures, preserves, and clears public status for ${perspective}`, () => {
    const self = perspective === 'p1' ? 'p1a: Target' : 'p2a: Target';
    const foe = perspective === 'p1' ? 'p2a: Source' : 'p1a: Source';
    const extractor = new PlayerStateExtractor(`major-status-${perspective}`, 'gen9randombattle', perspective);
    extractor.consumeChunk([
      '|turn|1',
      `|switch|${self}|Target|100/100`,
      `|switch|${foe}|Source|100/100`,
      `|-status|${self}|brn`,
      '|turn|2',
      `|-status|${self}|par`,
    ].join('\n'));
    let target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.status, 'par');
    assert.equal(target.status_source, 'protocol');
    assert.equal(target.status_started_turn, 2);

    extractor.consumeChunk(`|-curestatus|${self}|par|[msg]`);
    target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.status, null);
    assert.equal(target.status_source, 'protocol');
    assert.equal(target.status_started_turn, null);

    extractor.consumeChunk([
      `|-status|${self}|brn`,
      `|switch|${foe.replace('Source', 'Other')}|Other|100/100`,
      `|switch|${self}|Target|90/100 brn`,
    ].join('\n'));
    target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.status, 'brn', 'switch condition preserves a public current status');

    extractor.consumeChunk(`|-damage|${self}|80/100`);
    target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.status, null, 'a statusless public HP condition is positive clear evidence');

    extractor.consumeChunk([`|-status|${self}|tox`, `|-damage|${self}|0 fnt`].join('\n'));
    target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.status, 'tox', 'the fnt HP precursor does not clear status before the faint boundary');

    extractor.consumeChunk(`|faint|${self}`);
    target = extractor.getView().self_team.find((pokemon) => pokemon.ident === self)!;
    assert.equal(target.fainted, true);
    assert.equal(target.status, null, 'faint maps the internal fnt sentinel out of major-status state');
  });
}
