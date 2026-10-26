// Shared real producer for the Python round-trip and leakage tests.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../../..');
(async()=>{
 const {exportReplay}=require(path.join(root,'tools/replay_repro/export_frames.cjs'));
 const output=process.argv[2];fs.mkdirSync(output,{recursive:true});
 for(const id of ['2695493840','2695512325','2695618222']){
  const file=path.join(output,id+'.jsonl');fs.writeFileSync(file,'');
  await exportReplay(JSON.parse(fs.readFileSync(path.join(root,'sim-core/tests/fixtures/replay-real/gen9randombattle-'+id+'.json'),'utf8')),
   frame=>fs.appendFileSync(file,JSON.stringify(frame)+'\n'));
 }
 const cases=await require(path.join(root,'sim-core/dist/tests/helpers/decision_frame_cases.js')).invarianceCases();
 for(const {viewer,variants} of cases)for(const [i,frames] of variants.entries())
  fs.writeFileSync(path.join(output,viewer+'-'+i+'.jsonl'),frames.map(frame=>JSON.stringify(frame)+'\n').join(''));
})().catch(error=>{console.error(error);process.exitCode=1;});
