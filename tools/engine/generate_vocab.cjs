'use strict';
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../..');
const {installedNativeProfile}=require(path.join(root,'sim-core/dist/src/version_profile.js'));
const runtime=installedNativeProfile(),{Dex}=require(runtime.package_root),dex=Dex.mod('gen9');dex.includeData();
const unique=values=>['PAD','UNKNOWN','ABSENT',...new Set(values.filter(Boolean).sort())];
const conditions=[...Object.keys(dex.data.Conditions),...dex.moves.all().filter(m=>m.condition).map(m=>m.id),...dex.abilities.all().filter(a=>a.condition).map(a=>a.id)];
if(!fs.readFileSync(path.join(runtime.package_root,'sim/pokemon.ts'),'utf8').includes("id: 'recharge' as ID"))throw new Error('Pinned Recharge request emitter changed');
const vocab={schema_version:'engine-vocab/v1',engine_commit:runtime.engine_commit,special:{PAD:0,UNKNOWN:1,ABSENT:2},
 categories:{action_kinds:unique(['move','movetera','switch','revive','default']),damage_categories:unique(['physical','special','status']),
 species:unique(dex.species.all().flatMap(s=>[s.id,...(s.cosmeticFormes||[]).map(name=>dex.species.get(name).id)])),moves:unique([...dex.moves.all().map(m=>m.id),'recharge']),
 items:unique(dex.items.all().map(i=>i.id)),abilities:unique(dex.abilities.all().map(a=>a.id)),types:unique(dex.types.all().map(t=>t.id)),
 status:unique(['brn','par','slp','frz','psn','tox']),weather:unique(conditions),terrain:unique(conditions),
 pseudo_weather:unique(conditions),side_conditions:unique(conditions),volatiles:unique(conditions)},
 move_data:Object.fromEntries([...dex.moves.all()].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0).map(m=>[m.id,
 {type:m.type,category:m.category,base_power:m.basePower,priority:m.priority,accuracy:m.accuracy===true?1:m.accuracy/100}]))};
const bytes=JSON.stringify(vocab)+'\n',file=path.join(root,'trainer/src/neural/vocab_b8f23c99.json');
if(process.argv.includes('--check')){if(fs.readFileSync(file,'utf8')!==bytes)throw new Error('Vocabulary bytes differ');}
else fs.writeFileSync(file,bytes);
console.log(createHash('sha256').update(bytes).digest('hex'));
