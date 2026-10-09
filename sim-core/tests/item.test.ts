import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import {Battle, Teams} from 'pokemon-showdown';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {LocalBattleEnv} from '../src/env_manager';
import {validateObservableProtocolPrefix, validateRawProtocolRecord} from '../src/observable_state';
import {createPipelineIntegrationSession} from '../src/pipeline_integration';
import {PROTOCOL_CONTRACT} from '../src/protocol_contract';
import type {PlayerID} from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
type Shape = 'frisk' | 'eat' | 'knock' | 'trick' | 'balloon' | 'powerherb' | 'booster' | 'sash' | 'throat' | 'policy' | 'whiteherb';
const TAGLESS_USE_ITEM_SHAPES = ['powerherb', 'booster', 'sash', 'throat', 'policy', 'whiteherb'] as const;
const team = (text: string) => Teams.import(text)!;
const choices = (actor: PlayerID, own: string, foe: string): Record<PlayerID, string> =>
  actor === 'p1' ? {p1: own, p2: foe} : {p1: foe, p2: own};

// Each forced set is a representative selected by the pinned Gen 9 Random
// Battle singles generator. The custom matchup merely makes its documented
// public `useItem` branch deterministic; it is never projected.
function itemBattle(actor: PlayerID, shape: Shape): Battle {
  let own: ReturnType<typeof team>;
  let foe: ReturnType<typeof team>;
  switch (shape) {
  case 'balloon':
    own = team(`Ballooner (Eevee) @ Air Balloon
Ability: Run Away
- Splash
`);
    foe = team(`Popper (Pikachu) @ Leftovers
Ability: Static
- Tackle
`);
    break;
  case 'frisk':
    own = team(`Frisker (Gothorita) @ Leftovers
Ability: Frisk
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'eat':
    own = team(`Eater (Snorlax) @ Sitrus Berry
Ability: Thick Fat
- Belly Drum
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'knock':
    own = team(`Thief (Meowscarada) @ Leftovers
Ability: Overgrow
- Knock Off
- Splash
`);
    foe = team(`Target (Snorlax) @ Leftovers
Ability: Thick Fat
- Splash
- Tackle
`);
    break;
  case 'trick':
    own = team(`Swapper (Rotom) @ Choice Scarf
Ability: Levitate
- Trick
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'powerherb':
    own = team(`Holder (Armarouge) @ Power Herb
Ability: Flash Fire
- Meteor Beam
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'booster':
    own = team(`Holder (Flutter Mane) @ Booster Energy
Ability: Protosynthesis
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'sash':
    own = team(`Holder (Abra) @ Focus Sash
Ability: Synchronize
- Splash
`);
    foe = team(`Foe (Machamp) @ Leftovers
Ability: No Guard
- Close Combat
- Splash
`);
    break;
  case 'throat':
    own = team(`Holder (Toxtricity) @ Throat Spray
Ability: Punk Rock
- Snarl
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  case 'policy':
    own = team(`Holder (Snorlax) @ Weakness Policy
Ability: Thick Fat
- Splash
`);
    foe = team(`Foe (Machop) @ Leftovers
Ability: Guts
- Brick Break
- Splash
`);
    break;
  case 'whiteherb':
    own = team(`Holder (Cloyster) @ White Herb
Ability: Shell Armor
- Shell Smash
- Splash
`);
    foe = team(`Target (Eevee) @ Leftovers
Ability: Run Away
- Splash
- Tackle
`);
    break;
  }
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? own! : foe!});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? own! : foe!});
  if (shape === 'eat') {
    const prepare = choices(actor, 'move 1', 'move 1');
    battle.makeChoices(prepare.p1, prepare.p2);
  }
  return battle;
}

function initialChoice(shape: Shape): string {
  return shape === 'eat' ? 'move 2' : 'move 1';
}
function opposingChoice(shape: Shape): string {
  return shape === 'eat' ? 'move 2' : 'move 1';
}
function expectedRecord(actor: PlayerID, shape: Shape): string {
  const opponent = actor === 'p1' ? 'p2' : 'p1';
  switch (shape) {
  case 'frisk': return `|-item|${opponent}a: Target|Leftovers|[from] ability: Frisk|[of] ${actor}a: Frisker`;
  case 'eat': return `|-enditem|${actor}a: Eater|Sitrus Berry|[eat]`;
  case 'knock': return `|-enditem|${opponent}a: Target|Leftovers|[from] move: Knock Off|[of] ${actor}a: Thief`;
  case 'trick': return `|-item|${opponent}a: Target|Choice Scarf|[from] move: Trick`;
  case 'balloon': return `|-enditem|${actor}a: Ballooner|Air Balloon`;
  case 'powerherb': return `|-enditem|${actor}a: Holder|Power Herb`;
  case 'booster': return `|-enditem|${actor}a: Holder|Booster Energy`;
  case 'sash': return `|-enditem|${actor}a: Holder|Focus Sash`;
  case 'throat': return `|-enditem|${actor}a: Holder|Throat Spray`;
  case 'policy': return `|-enditem|${actor}a: Holder|Weakness Policy`;
  case 'whiteherb': return `|-enditem|${actor}a: Holder|White Herb`;
  }
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID, shape: Shape): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `item-${shape}-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}
function select(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find(candidate => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}
async function step(session: Session, next: Record<PlayerID, string>) {
  return session.step({p1: select(session, 'p1', next.p1), p2: select(session, 'p2', next.p2)});
}
function python(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}
function publicOnly(boundary: Awaited<ReturnType<typeof step>>['boundary']) {
  for (const player of PLAYERS) {
    const serialized = JSON.stringify(boundary.perspectives[player].observation);
    assert.ok(!serialized.includes('itemState') && !serialized.includes('lastItem') && !serialized.includes('itemSource'));
    assert.ok(!serialized.includes('"item":"Leftovers"') || boundary.perspectives[player].observation.protocol_prefix.some(line => line.includes('Leftovers')),
      'a public item value must have matching public evidence');
    assert.ok(!boundary.perspectives[player].observation.protocol_prefix.some(line => line.startsWith('|request|') || line.startsWith('|split|')));
  }
}

test('pinned item emitters provide generated reveal, transfer, and every reachable tagless non-Gem useItem form', () => {
  for (const shape of ['frisk', 'eat', 'knock', 'trick', 'balloon', ...TAGLESS_USE_ITEM_SHAPES] as Shape[]) {
    const direct = itemBattle('p1', shape);
    try {
      if (shape !== 'frisk') {
        const next = choices('p1', initialChoice(shape), opposingChoice(shape));
        direct.makeChoices(next.p1, next.p2);
      }
      assert.ok(direct.log.includes(expectedRecord('p1', shape)), `${shape} must emit ${expectedRecord('p1', shape)}`);
    } finally { direct.destroy(); }
  }
});

for (const actor of PLAYERS) {
  for (const shape of ['frisk', 'eat', 'knock', 'trick', 'balloon', ...TAGLESS_USE_ITEM_SHAPES] as Shape[]) {
    test(`item ${shape} ${actor}: public state, restore, rollback, and publish`, async () => {
      const direct = itemBattle(actor, shape);
      const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, shape);
      let restored: Session | undefined;
      try {
        const next = choices(actor, initialChoice(shape), opposingChoice(shape));
        direct.makeChoices(next.p1, next.p2);
        const transitioned = await step(session, next);
        const transitionedTwin = await step(twin, next);
        assert.equal(transitioned.transition_id, transitionedTwin.transition_id);
        assert.equal(transitioned.boundary.state_fingerprint, transitionedTwin.boundary.state_fingerprint);
        const expected = expectedRecord(actor, shape);
        for (const player of PLAYERS) {
          const observation = transitioned.boundary.perspectives[player].observation;
          assert.ok(observation.protocol_prefix.includes(expected));
          if (shape === 'balloon' || (TAGLESS_USE_ITEM_SHAPES as readonly Shape[]).includes(shape)) {
            const observedTeam = player === actor ? observation.view.self_team : observation.view.opponent_team;
            const holder = observedTeam.find(pokemon => pokemon.name === (shape === 'balloon' ? 'Ballooner' : 'Holder'));
            assert.ok(holder, JSON.stringify(observedTeam));
            if (player === actor) {
              assert.equal(holder.item, null, JSON.stringify(holder));
              assert.equal(holder.last_item, expected.split('|')[3].toLowerCase().replaceAll(' ', ''), JSON.stringify(holder));
              assert.equal(holder.item_state, shape === 'balloon' ? 'removed' : 'consumed', JSON.stringify(holder));
            } else {
              // Public evidence is shared, while owner-only item history remains omitted.
              assert.ok(!('item' in holder) && !('last_item' in holder) && !('item_state' in holder));
            }
          }
          assert.equal(python(transitioned.record_bundles[player]).status, 0);
        }
        publicOnly(transitioned.boundary);

        const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
        [restored] = await sessions(snapshot, actor, shape);
        assert.equal(restored.boundary.state_fingerprint, transitioned.boundary.state_fingerprint);
        const continuation = choices(actor, ['trick', 'eat', 'powerherb'].includes(shape) ? 'move 2' : 'move 1', shape === 'sash' ? 'move 2' : 'move 1');
        direct.makeChoices(continuation.p1, continuation.p2);
        const after = await step(session, continuation);
        const afterTwin = await step(twin, continuation);
        const afterRestored = await step(restored, continuation);
        assert.equal(after.transition_id, afterTwin.transition_id);
        assert.equal(after.boundary.state_fingerprint, afterTwin.boundary.state_fingerprint);
        assert.equal(after.boundary.state_fingerprint, afterRestored.boundary.state_fingerprint);
        for (const player of PLAYERS) assert.equal(python(after.record_bundles[player]).status, 0);

        const frozen = JSON.stringify(session.boundary);
        const stale = {p1: select(session, 'p1', continuation.p1), p2: select(session, 'p2', continuation.p2)};
        await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
        assert.equal(JSON.stringify(session.boundary), frozen);
      } finally {
        direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close();
      }
    });
  }
}

test('item grammar rejects invented payloads, non-active targets, provenance repair, and leakage before projection', () => {
  const edible = ['Aguav Berry', 'Chesto Berry', 'Custap Berry', 'Figy Berry', 'Iapapa Berry', 'Leppa Berry', 'Lum Berry', 'Mago Berry', 'Passho Berry', 'Rindo Berry', 'Salac Berry', 'Sitrus Berry', 'Wiki Berry'];
  const enditemForms = (PROTOCOL_CONTRACT.validation_rules.item as {dash_enditem_forms: Array<{tags: string[]; payloads?: string[]}>}).dash_enditem_forms;
  assert.deepEqual(enditemForms.find(form => form.tags.length === 0)?.payloads, ['Air Balloon', 'Booster Energy', 'Focus Sash', 'Power Herb', 'Throat Spray', 'Weakness Policy', 'White Herb']);
  assert.deepEqual(enditemForms.find(form => form.tags.length === 1 && form.tags[0] === '[eat]')?.payloads, edible);
  const valid = [
    '|-item|p2a: Target|Leftovers|[from] ability: Frisk|[of] p1a: Frisker',
    '|-item|p2a: Target|Choice Scarf|[from] move: Trick',
    '|-item|p2a: Target|White Herb|[from] move: Recycle',
    '|-enditem|p2a: Target|Sitrus Berry|[eat]',
    '|-enditem|p2a: Target|Aguav Berry|[eat]',
    '|-enditem|p2a: Target|Air Balloon',
    '|-enditem|p2a: Target|Booster Energy',
    '|-enditem|p2a: Target|Focus Sash',
    '|-enditem|p2a: Target|Power Herb',
    '|-enditem|p2a: Target|Throat Spray',
    '|-enditem|p2a: Target|Weakness Policy',
    '|-enditem|p2a: Target|White Herb',
    '|-enditem|p2a: Target|Leftovers|[from] move: Knock Off|[of] p1a: Thief',
    '|item|p1a: Holder|Leftovers',
  ];
  const invalid = [
    '|-item|p2a: Target|Definitely Not An Item|[from] move: Trick',
    '|-item|p2: Target|Leftovers|[from] move: Trick',
    '|-item|p2a: Target|Leftovers|[from] ability: Frisk|[of] p2a: Ally',
    '|-enditem|p2a: Target|Leftovers|[of] p1a: Thief|[from] move: Knock Off',
    '|-enditem|p2a: Target|Sitrus Berry|[eat]|[from] move: Trick',
    '|-enditem|p2a: Target|Choice Scarf|[eat]',
    '|-enditem|p2a: Target|Air Balloon|[eat]',
    '|-enditem|p2a: Target|Choice Scarf',
    '|-enditem|p2a: Target|Leftovers',
    '|-enditem|p2: Target|Air Balloon',
    '|-enditem|p2a: Target| Air Balloon',
    '|-enditem|p2a: Target|Air Balloon|[silent]',
    '|-enditem|p2a: Target|Air Balloon|extra',
    '|-item|p2a: Target| Leftovers|[from] move: Trick',
    '|-item|p2a: Target|Leftovers|[from] move: Trick|[of] p1a: Source',
    '|-item|p2a: Target|Leftovers|[from] move: Recycle',
    '|-item|p2a: Target|White Herb|[from] move: Recycle|[silent]',
    '|item|p1a: Holder|Leftovers|[from] ability: Frisk',
  ];
  for (const record of valid) validateRawProtocolRecord(record);
  for (const record of invalid) assert.throws(() => validateRawProtocolRecord(record));
  for (const player of PLAYERS) {
    assert.throws(() => validateObservableProtocolPrefix(invalid, player));
  }
});
