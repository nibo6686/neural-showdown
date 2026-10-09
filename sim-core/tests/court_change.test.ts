import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
const CINDERACE_SEED = [91, 274, 457, 640];
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
type Witness = {
	name: string;
	seed: number[];
	species: string;
	setup_moves: number[];
	conditions: Record<string, number>;
	hazard_entry?: { species: string; records: RegExp[] };
	snow_warning?: boolean;
	source_owned?: boolean;
};

// These are TeamGenerator seeds, not hand-written teams. Each set below is
// emitted by pokemon-showdown@0.11.10 for gen9randombattle and is rechecked
// at runtime before it enters the source-engine witness.
const WITNESSES: Witness[] = [
	{name: 'Spikes', seed: [212, 637, 1062, 1487], species: 'Skarmory', setup_moves: [4], conditions: {spikes: 1}, hazard_entry: {species: 'Ting-Lu', records: [/^\|-damage\|p[12]a: Ting-Lu\|.*\|\[from\] Spikes$/]}},
	{name: 'Stealth Rock', seed: [6, 19, 32, 45], species: 'Iron Treads', setup_moves: [2], conditions: {stealthrock: 1}, hazard_entry: {species: 'Rampardos', records: [/^\|-damage\|p[12]a: Rampardos\|.*\|\[from\] Stealth Rock$/]}},
	{name: 'Sticky Web', seed: [26, 79, 132, 185], species: 'Ribombee', setup_moves: [3], conditions: {stickyweb: 1}, hazard_entry: {species: 'Brute Bonnet', records: [/^\|-activate\|p[12]a: Brute Bonnet\|move: Sticky Web$/, /^\|-unboost\|p[12]a: Brute Bonnet\|spe\|1$/]}},
	{name: 'Reflect and Light Screen', seed: [32, 97, 162, 227], species: 'Meowstic', setup_moves: [2, 3], conditions: {reflect: 1, lightscreen: 1}, source_owned: true},
	{name: 'Aurora Veil', seed: [45, 136, 227, 318], species: 'Abomasnow', setup_moves: [3], conditions: {auroraveil: 1}, snow_warning: true, source_owned: true},
	{name: 'Toxic Spikes', seed: [119, 358, 597, 836], species: 'Ariados', setup_moves: [4, 4], conditions: {toxicspikes: 2}, hazard_entry: {species: 'Electivire', records: [/^\|-status\|p[12]a: Electivire\|tox$/]}},
	{name: 'Tailwind', seed: [110, 331, 552, 773], species: 'Shiftry', setup_moves: [2], conditions: {tailwind: 1}, source_owned: true},
];

const generatedTeam = (seed: number[]) => Teams.generate('gen9randombattle', {seed});
const choices = (actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> => actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};

function generatedWitness(actor: PlayerID, witness: Witness) {
	const cinderace = generatedTeam(CINDERACE_SEED);
	const setter = generatedTeam(witness.seed);
	const changer = cinderace.find(set => set.species === 'Cinderace');
	const source = setter.find(set => set.species === witness.species);
	assert.deepEqual(changer?.moves, ['pyroball', 'highjumpkick', 'suckerpunch', 'courtchange']);
	assert.equal(changer?.ability, 'Libero');
	assert.ok(source, `${witness.name} seed must generate ${witness.species}`);
	for (const move of witness.setup_moves) assert.ok(source!.moves[move - 1], `${witness.name} setup move ${move}`);
	if (witness.snow_warning) assert.equal(source!.ability, 'Snow Warning');
	const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
	battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? cinderace : setter});
	battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? cinderace : setter});
	return {battle, source_index: setter.indexOf(source!) + 1};
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID): Promise<[Session, Session]> {
	const reset = LocalBattleEnv.prototype.resetWithOptions;
	try {
		LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
		return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({battle_id: `court-change-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: 'observable-battle-state/v2'}))) as [Session, Session];
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
	return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {input: JSON.stringify(bundle), encoding: 'utf8', env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')}});
}
function sourceSide(battle: Battle, actor: PlayerID) { return battle.sides[actor === 'p1' ? 1 : 0]; }
function switchChoice(side: any, species?: string) {
	const roster = side.activeRequest.side.pokemon as Array<{active?: boolean; condition: string; details: string}>;
	const slot = roster.findIndex(pokemon => !pokemon.active && !pokemon.condition.endsWith(' fnt') && (!species || pokemon.details.split(',')[0] === species));
	assert.ok(slot >= 0, `must have a legal generated switch${species ? ` to ${species}` : ''}`);
	return `switch ${slot + 1}`;
}
function assertConditions(actual: Record<string, number | undefined>, expected: Record<string, number | undefined>) {
	for (const [condition, value] of Object.entries(expected)) assert.equal(actual[condition], value, condition);
}
function assertPublicOnly(boundary: Awaited<ReturnType<typeof step>>['boundary']) {
	for (const player of PLAYERS) {
		const observation = boundary.perspectives[player].observation;
		const serialized = JSON.stringify(observation);
		assert.ok(!serialized.includes('sideConditions') && !serialized.includes('sourceSlot') && !serialized.includes('duration'));
		assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
	}
}

for (const actor of PLAYERS) {
	for (const witness of WITNESSES) {
		test(`Court Change ${actor}: generated ${witness.name} witness swaps asymmetrically, restores, rolls back, and publishes`, async () => {
			const {battle: direct, source_index} = generatedWitness(actor, witness);
			const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor);
			let restored: Session | undefined;
			try {
				const setup: Record<PlayerID, string>[] = [];
				if (source_index !== 1) setup.push(choices(actor, 'move 3', `switch ${source_index}`));
				for (const move of witness.setup_moves) setup.push(choices(actor, 'move 3', `move ${move}`));
				for (const turn of setup) { direct.makeChoices(turn.p1, turn.p2); await step(session, turn); await step(twin, turn); }
				if (witness.snow_warning) {
					const side = actor === 'p1' ? 'p2' : 'p1';
					assert.ok(direct.log.includes(`|-weather|Snowscape|[from] ability: Snow Warning|[of] ${side}a: Abomasnow`));
				}
				for (const player of PLAYERS) {
					const observation = session.boundary.perspectives[player].observation;
					const actorMap = player === actor ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
					const sourceMap = player === actor ? observation.view.field.side_conditions.opponent : observation.view.field.side_conditions.self;
					assertConditions(actorMap, witness.source_owned ? Object.fromEntries(Object.keys(witness.conditions).map(condition => [condition, undefined])) : witness.conditions);
					assertConditions(sourceMap, witness.source_owned ? witness.conditions : Object.fromEntries(Object.keys(witness.conditions).map(condition => [condition, undefined])));
				}

				// A normal source-side switch proves that the condition is side-owned;
				// Court Change then swaps this generated asymmetric state atomically.
				const court = choices(actor, 'move 4', switchChoice(sourceSide(direct, actor)));
				direct.makeChoices(court.p1, court.p2);
				const result = await step(session, court); const twinResult = await step(twin, court);
				assert.equal(result.transition_id, twinResult.transition_id);
				assert.equal(result.boundary.state_fingerprint, twinResult.boundary.state_fingerprint);
				assert.ok(direct.log.includes('|-swapsideconditions'));
				assert.ok(direct.log.includes(`|-activate|${actor}a: Cinderace|move: Court Change`));
				for (const player of PLAYERS) {
					const observation = result.boundary.perspectives[player].observation;
					const actorMap = player === actor ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
					const sourceMap = player === actor ? observation.view.field.side_conditions.opponent : observation.view.field.side_conditions.self;
					assertConditions(actorMap, witness.source_owned ? witness.conditions : Object.fromEntries(Object.keys(witness.conditions).map(condition => [condition, undefined])));
					assertConditions(sourceMap, witness.source_owned ? Object.fromEntries(Object.keys(witness.conditions).map(condition => [condition, undefined])) : witness.conditions);
					assert.ok(observation.protocol_prefix.includes('|-swapsideconditions'));
					assert.ok(observation.protocol_prefix.includes(`|-activate|${actor}a: Cinderace|move: Court Change`));
					assert.equal(python(result.record_bundles[player]).status, 0);
				}
				assertPublicOnly(result.boundary);

				const runtimeSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
				[restored] = await sessions(runtimeSnapshot, actor);
				assert.equal(restored.boundary.state_fingerprint, result.boundary.state_fingerprint);
				const frozen = JSON.stringify(session.boundary);
				const stale = {p1: select(session, 'p1', court.p1), p2: select(session, 'p2', court.p2)};
				await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
				assert.equal(JSON.stringify(session.boundary), frozen);

				if (witness.hazard_entry) {
					const entry = choices(actor, 'move 3', switchChoice(sourceSide(direct, actor), witness.hazard_entry.species));
					direct.makeChoices(entry.p1, entry.p2);
					const advanced = await step(session, entry); const advancedTwin = await step(twin, entry); const advancedRestored = await step(restored, entry);
					assert.equal(advanced.transition_id, advancedTwin.transition_id);
					assert.equal(advanced.boundary.state_fingerprint, advancedRestored.boundary.state_fingerprint);
					for (const pattern of witness.hazard_entry.records) assert.ok(direct.log.some(record => pattern.test(record)), `${witness.name} later switch-in record`);
					for (const player of PLAYERS) assert.equal(python(advanced.record_bundles[player]).status, 0);
				} else if (witness.conditions.tailwind) {
					let expired = false;
					for (let turn = 0; turn < 4; turn += 1) {
						const next = choices(actor, 'move 3', switchChoice(sourceSide(direct, actor)));
						direct.makeChoices(next.p1, next.p2);
						const advanced = await step(session, next); const advancedTwin = await step(twin, next); const advancedRestored = await step(restored, next);
						assert.equal(advanced.transition_id, advancedTwin.transition_id);
						assert.equal(advanced.boundary.state_fingerprint, advancedRestored.boundary.state_fingerprint);
						const side = actor === 'p1' ? 'p1: One' : 'p2: Two';
						if (advanced.boundary.perspectives[actor].observation.protocol_prefix.includes(`|-sideend|${side}|move: Tailwind`)) {
							expired = true;
							for (const player of PLAYERS) {
								const observation = advanced.boundary.perspectives[player].observation;
								const transferredMap = player === actor ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
								assert.equal(transferredMap.tailwind, undefined);
								assert.equal(python(advanced.record_bundles[player]).status, 0);
							}
							break;
						}
					}
					assert.ok(expired, 'generated Tailwind must expire from the transferred side');
				}
			} finally { direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close(); }
		});
	}
}

test('Court Change accepts only the pinned source records before projection', () => {
	const valid = ['|-swapsideconditions', '|-activate|p1a: Changer|move: Court Change'];
	const invalid = [
		'|swapsideconditions', '|-swapsideconditions|p1: One|p2: Two', '|-swapsideconditions|[silent]',
		'|-swapsideconditions|', '|-swapsideconditions|p1b: One', '|-swapsideconditions|extra',
		'|-activate|p1: Changer|move: Court Change', '|-activate|p1b: Changer|move: Court Change',
		'|-activate|p1a: Changer|move: Court Change|[silent]', '|-activate|p1a: Changer|move: Court  Change',
	];
	for (const record of valid) validateRawProtocolRecord(record);
	for (const record of invalid) assert.throws(() => validateRawProtocolRecord(record), record);
	for (const player of PLAYERS) assert.throws(() => validateObservableProtocolPrefix(invalid, player));
});
