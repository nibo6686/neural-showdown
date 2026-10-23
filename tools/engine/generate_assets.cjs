'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const engine = path.join(root, 'sim-core/node_modules/pokemon-showdown');
const pkg = require(path.join(engine, 'package.json'));
const {Dex} = require(engine);
const commit = pkg.engine_commit;
if (!/^[a-f0-9]{40}$/.test(commit || '')) throw new Error('Expected a commit-pinned engine');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const write = (relative, value) => {
  const bytes = JSON.stringify(value) + '\n';
  if (process.argv.includes('--check')) {
    if (fs.readFileSync(path.join(root, relative), 'utf8') !== bytes) throw new Error('Generated asset differs: ' + relative);
  } else fs.writeFileSync(path.join(root, relative), bytes);
  console.log(relative + ' sha256=' + hash(bytes));
};
const dex = Dex.mod('gen9'); dex.includeData();
const species = {}, moves = {}, types = {};
for (const value of dex.species.all()) species[value.id] = {exists: value.exists, types: value.types};
for (const id of Object.keys(dex.data.Moves)) {
  const value = dex.moves.get(id);
  moves[id] = {exists: value.exists, type: value.type, category: value.category, basePower: value.basePower, accuracy: value.accuracy};
}
for (const value of dex.types.all()) types[value.id] = {damageTaken: value.damageTaken};
const integrity = require(path.join(root, 'sim-core/package-lock.json')).packages['node_modules/pokemon-showdown'].integrity;
write(`sim-core/simulator_coverage/lookups/pokemon-showdown-${commit.slice(0, 8)}.json`, {
  schema_version: 'candidate-helper-lookups/v1', package_version: pkg.version,
  provenance: {engine_commit: commit, integrity, scope: 'Lookup values only; not semantic acceptance'},
  data: {species, moves, types, aliases: require(path.join(engine, 'dist/data/aliases.js')).Aliases},
});
// Preserve the reviewed finite grammar and its quarantines; derive its engine-bound
// domain from this engine. Re-pinning does not grant any additional semantic scope.
const template = fs.readFileSync(path.join(root, 'trainer/src/neural/protocol_contract_0_11_11.json'));
if (hash(template) !== 'f2fb0bb8e4910c2c1dfcacd5436c6306c9cacf685a5f5956e1b38e892226b834') throw new Error('Reviewed grammar template changed');
const contract = JSON.parse(template);
contract.provenance.target_revision = commit;
contract.provenance.target_abilities_sha256 = hash(fs.readFileSync(path.join(engine, 'dist/data/abilities.js')));
contract.provenance.engine_integrity = integrity;
contract.provenance.source = 'P0.4 pinned compiled abilities and gen9 set inputs; inherited finite Natural Cure, Trace and Revival grammar';
contract.protocol.simulator.engine_commit = commit;
const sets = require(path.join(engine, 'dist/data/random-battles/gen9/sets.json'));
contract.protocol.validation_rules.ability.payload_domains.dash_trace_copy = [...new Set(Object.values(sets)
  .flatMap(species => species.sets.flatMap(set => set.abilities)))].filter(name => {
    const ability = dex.abilities.get(name); return !ability.flags.notrace && ability.id !== 'noability';
  }).sort();
const historical = JSON.parse(fs.readFileSync(path.join(root,'trainer/src/neural/protocol_contract.json'),'utf8'));
// Item selector literals and required species items are public payload domains,
// never evidence that a particular Pokemon holds an unrevealed item.
const selector = fs.readFileSync(path.join(engine,'data/random-battles/gen9/teams.ts'),'utf8');
const selectedItems = [...selector.matchAll(/['"]([^'"\r\n]+)['"]/g)].map(m=>m[1])
  .filter(name=>dex.items.get(name).exists && dex.items.get(name).name===name);
const itemRules = contract.protocol.validation_rules.item;
itemRules.payloads = [...new Set([...itemRules.payloads,...selectedItems.filter(name=>!dex.items.get(name).isNonstandard),
  ...Object.keys(sets).map(name=>dex.species.get(name)).flatMap(s=>s.requiredItems || (s.requiredItem?[s.requiredItem]:[])).filter(name=>!dex.items.get(name).isNonstandard)])].sort();
itemRules.dash_item_forms.push({tags:['[from] ability: Harvest'],payloads:itemRules.payloads.filter(name=>dex.items.get(name).isBerry)});
// Exact native emitter forms: abilities.ts Pickpocket, pokemon.ts cureStatus,
// conditions.ts slp.onStart, items.ts Power Herb, battle.ts attrLastMove/makeRequest.
const abilitiesSource = fs.readFileSync(path.join(engine,'data/abilities.ts'),'utf8');
if (!abilitiesSource.includes("this.add('-enditem', source, yourItem, '[silent]', '[from] ability: Pickpocket', `[of] ${source}`)")) throw new Error('Pickpocket emitter changed');
itemRules.dash_enditem_forms.push({tags:['[silent]','[from] ability: Pickpocket','[of] self-active']});
itemRules.dash_item_forms.push({tags:['[from] ability: Pickpocket','[of] opposing-active']});
if(!abilitiesSource.includes("this.add('-item', source, yourItem, '[from] ability: Magician', `[of] ${pokemon}`)"))throw new Error('Magician emitter changed');
itemRules.dash_item_forms.push({tags:['[from] ability: Magician','[of] opposing-pokemon']});
const movesSource=fs.readFileSync(path.join(engine,'data/moves.ts'),'utf8');
for(const label of [...new Set([...movesSource.matchAll(/this\.add\('-enditem', target, item\.name, '\[from\] stealeat', '\[move\] ([^']+)'/g)].map(m=>m[1]))].sort()) {
  itemRules.dash_enditem_forms.push({tags:['[from] stealeat','[move] '+label,'[of] opposing-active'],payloads:itemRules.payloads.filter(name=>dex.items.get(name).isBerry)});
}
contract.protocol.validation_rules.ability.payload_domains.dash_boost=[...new Set([...contract.protocol.validation_rules.ability.payload_domains.dash_boost,
  ...dex.abilities.all().filter(a=>!a.isNonstandard&&a.gen<=9&&Object.values(a).some(v=>typeof v==='function'&&/this\.boost\(/.test(v.toString()))).map(a=>a.name)])].sort();
const statusRules = contract.protocol.validation_rules.major_status;
statusRules.bench_cure_tags = ['[msg]','[silent]'];
for (const move of dex.moves.all().filter(move=>move.status==='slp'||move.secondary?.status==='slp'||move.secondaries?.some(s=>s.status==='slp')).sort((a,b)=>a.name.localeCompare(b.name))) {
  const tags=['[from] move: '+move.name];
  if (!statusRules.apply_forms.some(form=>JSON.stringify(form.tags)===JSON.stringify(tags))) statusRules.apply_forms.push({tags,statuses:['slp']});
}
contract.protocol.validation_rules.anim.optional_tags = ['[miss]'];
contract.protocol.validation_rules.anim.no_target_tag = '[notarget]';
const formatsSource=fs.readFileSync(path.join(engine,'dist/sim/dex-formats.js'),'utf8');
const maxTeamSize=Number(/if \(this\.maxTeamSize > (\d+)\)/.exec(formatsSource)?.[1]);
if(!maxTeamSize)throw new Error('Missing source team size limit');
contract.protocol.validation_rules.teampreview = {team_sizes:Array.from({length:maxTeamSize},(_,i)=>i+1)};
contract.protocol.validation_rules.partial_trap = {move_names: [...new Set(dex.moves.all()
  .filter(move=>move.volatileStatus==='partiallytrapped').map(move=>move.name))].sort()};
const restored = new Set(['-start','-end','-sidestart','-sideend','-weather','-fieldstart','-fieldend','cant','heal','-swapsideconditions']);
contract.protocol.supported_commands = historical.supported_commands.slice();
contract.protocol.recognized_unsupported_commands = contract.protocol.recognized_unsupported_commands.filter(e=>!restored.has(e.token));
contract.semantic_dispositions.effect_lifecycle = 'source-reviewed classes; uncovered deltas unsupported-fail-closed';
contract.semantic_dispositions.partial_trap = 'public-damage-only; binding-source-and-duration-untyped';
contract.semantic_dispositions.chilly_reception = 'exact-premajor-prepare; transient-state-raw-only';
contract.semantic_dispositions.heal_failure = 'historical-raw-shapes; no inferred attribution';
// Restoring a family does not turn its valid old shape into a negative fixture.
// Keep malformed controls and the separately quarantined Court Change control.
contract.protocol.rejection_fixtures = contract.protocol.rejection_fixtures.filter(e=>!restored.has(e.record.split('|')[1]) || e.kind==='malformed' || e.record.split('|')[1]==='-swapsideconditions');
const examples = {'-start':'|-start|p1a: Pikachu|aquaring','-end':'|-end|p1a: Pikachu|aquaring',
  '-sidestart':'|-sidestart|p1: Alice|move: Toxic Spikes','-sideend':'|-sideend|p1: Alice|Toxic Spikes',
  '-weather':'|-weather|none','-fieldstart':'|-fieldstart|move: Gravity','-fieldend':'|-fieldend|move: Gravity',
  cant:'|cant|p1a: Pikachu|move: Disable',heal:'|heal|p1a: Pikachu|100/100','-swapsideconditions':'|-swapsideconditions'};
for (const token of restored) {
  const record=examples[token], fixture=structuredClone(contract.protocol.record_fixtures[0]);
  const index=contract.protocol.valid_record_controls.length;
  const control={...contract.protocol.valid_record_controls[0],token,record,
    evidence:'P0.5b source-compared historical grammar control'};
  contract.protocol.valid_record_controls.push(control);
  Object.assign(fixture,{token,record,evidence:control.evidence,fixture_reference:`control:${index}`});
  contract.protocol.record_fixtures.push(fixture);
}
contract.protocol.rejection_fixtures = contract.protocol.rejection_fixtures.filter(e=>!(e.kind==='unproved_semantic_family'&&e.record.startsWith('|-heal|')));
contract.protocol.rejection_fixtures.push({record:'|-swapsideconditions',kind:'unproved_semantic_family'});
contract.semantic_dispositions.magician='finite-public-item-transfer; current item and removal history only';
for(const fixture of contract.protocol.rejection_fixtures)if(fixture.record.includes('[from] ability: Magician')) {fixture.record='|-item|p1a: Gardevoir|Leftovers|[from] ability: Magician|[of] p1a: Blissey';fixture.kind='malformed';}
write(`trainer/src/neural/protocol_contract_${commit.slice(0, 8)}.json`, contract);
console.log('abilities_sha256=' + contract.provenance.target_abilities_sha256);
