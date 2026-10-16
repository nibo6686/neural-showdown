const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const root='/Users/nbolger/Desktop/neural-showdown',scratch='/private/tmp/neural-prompt29-20261012',out=root+'/docs/planning/perspective-fidelity-prompt35-';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const old=root+'/sim-core/node_modules/pokemon-showdown',artifact=scratch+'/0.11.10/package';
const proofs=JSON.parse(fs.readFileSync(root+'/docs/planning/perspective-fidelity-prompt29-artifacts.json'));
for(const v of ['0.11.10','0.11.11']){const proof=proofs.find(p=>p.scratch?.endsWith(v+'.tgz'));assert.equal(sha(fs.readFileSync(proof.scratch)),proof.sha256);}
const inputs=['dist/sim/dex.js','dist/sim/dex-data.js','dist/sim/dex-species.js','dist/sim/dex-moves.js','dist/data/pokedex.js','dist/data/moves.js','dist/data/typechart.js','dist/data/aliases.js','dist/data/formats-data.js'];
const hashes={};for(const f of inputs){const a=fs.readFileSync(artifact+'/'+f),b=fs.readFileSync(old+'/'+f);assert.deepEqual(a,b,f);hashes[f]=sha(a);}
const {Dex,toID}=require(old),oldDex=require(artifact+'/dist/sim/dex.js').Dex;
function subset(dex){return {species:Object.fromEntries(dex.species.all().map(s=>[s.id,{exists:s.exists,types:[...s.types]}])),moves:Object.fromEntries(dex.moves.all().map(m=>[m.id,{exists:m.exists,type:m.type,category:m.category,basePower:m.basePower,accuracy:m.accuracy}])),types:Object.fromEntries(Object.entries(dex.data.TypeChart).map(([id,row])=>[id,{damageTaken:{...row.damageTaken}}])),aliases:{...dex.data.Aliases}};}
const data=subset(Dex);assert.deepEqual(data,subset(oldDex));
const asset={schema_version:'historical-helper-lookups/v1',package_version:'0.11.10',provenance:{npm_sha256:proofs.find(p=>p.scratch?.endsWith('0.11.10.tgz')).sha256,integrity:proofs.find(p=>p.version==='0.11.10').integrity_verified,gitHead:proofs.find(p=>p.version==='0.11.10').gitHead,inputs:hashes},data};
fs.mkdirSync(root+'/sim-core/simulator_coverage/lookups',{recursive:true});const file=root+'/sim-core/simulator_coverage/lookups/pokemon-showdown-0.11.10.json';fs.writeFileSync(file,JSON.stringify(asset)+'\n');
fs.writeFileSync(out+'lookup-extraction.json',JSON.stringify({artifact_bytes_checked:true,artifact_and_installed_subsets_equal:true,inputs:hashes,counts:{species:Object.keys(data.species).length,moves:Object.keys(data.moves).length,types:Object.keys(data.types).length,aliases:Object.keys(data.aliases).length},asset_sha256:sha(fs.readFileSync(file)),normalizer_source_sha256:sha(fs.readFileSync(old+'/dist/sim/dex-data.js')),target_runtime_loaded:false},null,2)+'\n');
console.log('P35_EXTRACTION',JSON.stringify({old_inputs:inputs.length,subset_parity:true,lookup_sha256:sha(fs.readFileSync(file))}));
