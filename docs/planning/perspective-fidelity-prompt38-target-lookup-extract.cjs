const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const root='/private/tmp/neural-showdown-native11-prompt38',pkg=root+'/sim-core/node_modules/pokemon-showdown',artifact='/private/tmp/neural-prompt29-20261012/0.11.11/package';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const tgz=fs.readFileSync('/private/tmp/neural-prompt29-20261012/0.11.11.tgz');assert.equal(sha(tgz),'49af14aaed1084887f756372c7386c9987905930cc848ed31e9202c10c592d66');
const files=['dist/sim/dex.js','dist/sim/dex-data.js','dist/sim/dex-species.js','dist/sim/dex-moves.js','dist/data/pokedex.js','dist/data/moves.js','dist/data/typechart.js','dist/data/aliases.js','dist/data/formats-data.js','dist/sim/battle.js','dist/sim/side.js','dist/sim/pokemon.js','dist/sim/state.js','dist/sim/battle-stream.js','dist/data/random-battles/gen9/teams.js','data/random-battles/gen9/sets.json','config/formats.ts'];
const hashes={};for(const f of files){const installed=fs.readFileSync(pkg+'/'+f);assert.deepEqual(installed,fs.readFileSync(artifact+'/'+f),f);hashes[f]=sha(installed);}
const {Dex}=require(pkg);const data={species:Object.fromEntries(Dex.species.all().map(s=>[s.id,{exists:s.exists,types:[...s.types]}])),moves:Object.fromEntries(Dex.moves.all().map(m=>[m.name.toLowerCase().replace(/[^a-z0-9]+/g,''),{exists:m.exists,type:m.type,category:m.category,basePower:m.basePower,accuracy:m.accuracy}])),types:Object.fromEntries(Object.entries(Dex.data.TypeChart).map(([id,row])=>[id,{damageTaken:{...row.damageTaken}}])),aliases:{...require(pkg+'/dist/data/aliases.js').Aliases}};
let materialized=0;
for(const target of Object.values(data.aliases)){
 const key=String(target).toLowerCase().replace(/[^a-z0-9]+/g,'');
 const species=Dex.species.get(target),move=Dex.moves.get(target);
 for(const [table,row] of [[data.species,species.exists?{exists:species.exists,types:[...species.types]}:null],[data.moves,move.exists?{exists:move.exists,type:move.type,category:move.category,basePower:move.basePower,accuracy:move.accuracy}:null]]){
  if(!row)continue;
  if(table[key])assert.deepEqual(table[key],row,'canonical alias projection must not overwrite '+key);
  else {table[key]=row;materialized++;}
 }
}
assert.equal(data.moves.hiddenpowerice.exists,true);
const asset={schema_version:'candidate-helper-lookups/v1',package_version:'0.11.11',provenance:{npm_sha256:sha(tgz),gitHead:'739a5e1fee432ad80ff7136d70cca993be358b59',inputs:hashes,scope:'Lookup values and existing canonical alias-target projections only; not semantic acceptance'},data};
const file=root+'/sim-core/simulator_coverage/lookups/pokemon-showdown-0.11.11.json';fs.writeFileSync(file,JSON.stringify(asset)+'\n');const pin=sha(fs.readFileSync(file));
const vp=root+'/sim-core/src/version_profile.ts';fs.writeFileSync(vp,fs.readFileSync(vp,'utf8').replace(/const TARGET_LOOKUP_SHA256 = '[a-f0-9]+';/,`const TARGET_LOOKUP_SHA256 = '${pin}';`));
fs.writeFileSync('/Users/nbolger/Desktop/neural-showdown/docs/planning/perspective-fidelity-prompt38-target-lookup.json',JSON.stringify({inputs:hashes,lookup_sha256:pin,loaded_path:require.resolve(pkg),materialized_alias_targets:materialized,counts:{species:Object.keys(data.species).length,moves:Object.keys(data.moves).length,types:Object.keys(data.types).length,aliases:Object.keys(data.aliases).length},scope:'finite loaded rule-data extraction; no team generation'},null,2)+'\n');console.log('TARGET_LOOKUP',pin,'checked inputs',files.length);
