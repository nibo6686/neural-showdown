const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root='/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/native11-recovery-2026-10-14/candidate';
if(!process.argv[2]){
 const {spawnSync}=require('node:child_process');const out=[];
 for(const mode of ['before','candidate']){const r=spawnSync(process.execPath,[__filename,mode],{encoding:'utf8',timeout:150000,env:process.env});assert.equal(r.status,0,mode+': '+r.stderr);out.push(r.stdout);}
 assert.equal(out[0],out[1]);console.log('P57_DEFAULT_PARITY '+JSON.stringify({fresh_processes:2,bounded_transitions:1,constructed_native_fixture:true,opt_in_disabled:true,literal_episode_output_equal:true,bytes:Buffer.byteLength(out[0]),sha256:crypto.createHash('sha256').update(out[0]).digest('hex'),clock:'fixed presentation clock; no identity authority'}));process.exit(0);
}
Date.now=()=>1792010000000;
if(process.argv[2]==='before'){
 const Module=require('node:module'),ts=require(root+'/sim-core/node_modules/typescript'),load=Module._extensions['.js'];
 Module._extensions['.js']=function(module,file){const name=path.basename(file,'.js');if(path.dirname(file)===root+'/sim-core/dist/src'&&['pipeline_episode','pipeline_integration'].includes(name)){const raw=fs.readFileSync('/private/tmp/neural-prompt57/'+name+'.ts.before','utf8');return module._compile(ts.transpileModule(raw,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,file);}return load(module,file);};
}
const {Teams}=require(root+'/sim-core/node_modules/pokemon-showdown');let count=0;
Teams.generate=()=>Teams.import((count++===0?'Alpha':'Beta')+' (Magikarp)\nAbility: Swift Swim\n- Splash');
const {runPipelineEpisode}=require(root+'/sim-core/dist/src/pipeline_episode');
runPipelineEpisode({battle_id:'P57-default-parity',format:'gen9randombattle',seed:[1,2,3,4],limits:{max_transitions:1,max_attempts:1,max_rejections_per_boundary:1}}).then(result=>{assert.equal(result.counts.committed_transitions,1);assert.equal(result.faithful_complete_episode,false);assert.ok(!JSON.stringify(result).includes('native-owner-identifiers'));process.stdout.write(JSON.stringify(result));}).catch(e=>{console.error(e);process.exitCode=1;});
