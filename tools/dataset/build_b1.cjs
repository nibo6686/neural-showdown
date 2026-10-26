'use strict';
const fs=require('node:fs'),fsp=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const {createHash}=require('node:crypto'),{spawn,execFileSync}=require('node:child_process');
const {Worker,isMainThread,parentPort}=require('node:worker_threads');
const root=path.resolve(__dirname,'../..');
const {Journal,atomicWrite,SuspensionClock,complete,failure}=require('../replay_repro/durable_io.cjs');
const option=(args,name)=>args.find(a=>a.startsWith('--'+name+'='))?.slice(name.length+3);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const python='D:\\Anaconda\\envs\\neuralgpu\\python.exe';

if(!isMainThread){
 let acknowledge;
 parentPort.on('message',async message=>{
  if(message.type==='ack'){acknowledge?.();return;}
  if(message.type!=='battle')return;
  try{
   const {exportReplay}=require('../replay_repro/export_frames.cjs');
   const replay=JSON.parse(fs.readFileSync(message.file,'utf8'));
   if(replay.id!==message.id)throw new Error('dataset/replay-id');
   await exportReplay(replay,frame=>new Promise(resolve=>{acknowledge=resolve;parentPort.postMessage({type:'frame',frame});}));
   parentPort.postMessage({type:'done'});
  }catch(error){parentPort.postMessage({type:'failed',reason:error.message});}
 });
}

function splitIds(ids,seed){
 const order=[...ids].sort((a,b)=>hash(seed+':'+a).localeCompare(hash(seed+':'+b))||a.localeCompare(b));
 return Object.fromEntries(order.map((id,i)=>[id,i<Math.floor(ids.length*.9)?'train':i<Math.floor(ids.length*.95)?'validation':'test']));
}
function labels(replay){
 const {parseReplay}=require('../replay_repro/replay_session.cjs'),{expectedPublic}=require('../replay_repro/public_log.cjs');
 const {players}=parseReplay(replay),ending=expectedPublic(replay).ending;
 if(replay.log.split(/\r?\n/).includes('|tie|'))return {ending,outcomes:{p1:.5,p2:.5}};
 const winners=replay.log.split(/\r?\n/).filter(l=>l.startsWith('|win|'));
 if(winners.length!==1)throw new Error('dataset/missing-outcome');
 const winner=winners[0].slice(5),owner=['p1','p2'].find(p=>players[p].name===winner);
 if(!owner)throw new Error('dataset/unbound-winner');
 return {ending,outcomes:{p1:owner==='p1'?1:0,p2:owner==='p2'?1:0}};
}
function pythonBridge(output){
 const env={...process.env,PYTHONPATH:path.join(root,'trainer/src')};delete env.PYTHONUTF8;delete env.PYTHONIOENCODING;
 const child=spawn(python,['-m','neural.dataset_b1','--output',output],{cwd:root,env,windowsHide:true,stdio:['pipe','pipe','inherit']});
 let sequence=0,buffer='',dead=false;const pending=new Map();
 const rejectAll=error=>{dead=true;for(const item of pending.values()){clearTimeout(item.timer);item.reject(error);}pending.clear();};
 child.on('error',rejectAll);child.on('exit',code=>rejectAll(new Error('Python feature worker exit '+code)));
 child.stdin.on('error',rejectAll);
 child.stdout.on('data',bytes=>{
  buffer+=bytes.toString('utf8');let end;
  while((end=buffer.indexOf('\n'))>=0){
   const response=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);
   const item=pending.get(response.rpc);if(!item)continue;pending.delete(response.rpc);clearTimeout(item.timer);
   response.error?item.reject(new Error('dataset/feature: '+response.error)):item.resolve(response.result);
  }
 });
 return {child,call:message=>new Promise((resolve,reject)=>{
  if(dead)return reject(new Error('Python feature worker unavailable'));
  const rpc=++sequence,timer=setTimeout(()=>{pending.delete(rpc);reject(new Error('Python feature worker RPC timeout'));child.kill();},300000);
  pending.set(rpc,{resolve,reject,timer});child.stdin.write(JSON.stringify({...message,rpc})+'\n');
 }),close:async()=>{child.stdin.end();if(child.exitCode===null&&child.signalCode===null)await new Promise(resolve=>child.once('exit',resolve));}};
}

async function build(args){
 const directory=path.resolve(args.find(a=>!a.startsWith('--'))),files=option(args,'files'),output=path.resolve(option(args,'output'));
 if(!files)throw new Error('--files is required');
 await fsp.mkdir(output,{recursive:true});
 const fileBytes=await fsp.readFile(files),names=JSON.parse(fileBytes),ids=names.map(name=>{
  if(!/^gen9randombattle-\d+\.json$/.test(name))throw new Error('Invalid replay file name');return name.slice(0,-5);
 });
 if(new Set(ids).size!==ids.length)throw new Error('Duplicate battle IDs');
 const workers=Number(option(args,'workers')||3),deadline=Number(option(args,'replay-timeout-ms')||300000),shardSize=Number(option(args,'shard-size')||10000);
 if(!Number.isInteger(workers)||workers<1||workers>5||!Number.isInteger(deadline)||deadline<1000||!Number.isInteger(shardSize)||shardSize<1)throw new Error('Invalid dataset limits');
 const seed=option(args,'seed')||'20261024',splits=splitIds(ids,seed),commit=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',timeout:10000,windowsHide:true}).trim();
 const {VOCAB_SHA256}= {VOCAB_SHA256:hash(await fsp.readFile(path.join(root,'trainer/src/neural/vocab_b8f23c99.json')))};
 const definition={schema_version:'b1-dataset/v1',commit,engine_commit:'b8f23c99629132611ba59e99480cb148ea8c5d3d',frame_schema:'decision-frame/v1',feature_version:'feature-v1',
  vocabulary_sha256:VOCAB_SHA256,sample_list_sha256:hash(fileBytes),split_seed:seed,split_battle_ids:Object.fromEntries(['train','validation','test'].map(s=>[s,ids.filter(id=>splits[id]===s).sort()])),
  label_definitions:{policy:'human canonical action index in legal list',value:'owner win=1 loss=0 tie=0.5; administrative endings count as loss for departing owner',rating:'numeric value plus rating_known; never imputed'}};
 const definitionPath=path.join(output,'definition.json');
 if(args.includes('--resume')){if(JSON.stringify(JSON.parse(await fsp.readFile(definitionPath,'utf8')))!==JSON.stringify(definition))throw new Error('Dataset resume definition mismatch');}
 else {if(fs.existsSync(definitionPath))throw new Error('Dataset already exists; explicit resume required');await atomicWrite(definitionPath,JSON.stringify(definition)+'\n');}
 const notify=message=>{if(process.connected)process.send({type:'status',...message});};
 const journal=new Journal(option(args,'manifest')||path.join(output,'build.jsonl'),{notify});
 const rows=await journal.open(args.includes('--resume')),seen=new Set();
 for(const row of rows){if(!ids.includes(row.id)||seen.has(row.id))throw new Error('Invalid dataset journal');seen.add(row.id);}
 const bridge=pythonBridge(output),pool=new Set();let cursor=0,samples=fs.existsSync(path.join(output,'sample.jsonl'))?fs.readFileSync(path.join(output,'sample.jsonl'),'utf8').trim().split('\n').filter(Boolean).length:0;
 const queue=ids.filter(id=>!seen.has(id));let interrupted=false;
 const interrupt=message=>{if(['stop','interrupt'].includes(message.type)){interrupted=true;for(const worker of pool)void worker.terminate();bridge.child.kill();}};
 const clock=new SuspensionClock();
 const clockTimer=setInterval(()=>{if(clock.sample())interrupt({type:'interrupt'});},1000);
 const disconnected=()=>interrupt({type:'stop'});
 process.on('message',interrupt);process.on('disconnect',disconnected);
 const started=performance.now();
 const progress=()=>notify({job_kind:'dataset-b1',status:'running',completed:rows.length,total:ids.length,
  passed:rows.filter(r=>r.ok).length,examples:rows.reduce((n,r)=>n+r.examples,0),failed:rows.filter(r=>!r.ok).length,interrupted:0});
 progress();
 async function battle(id,worker){
  const replay=JSON.parse(await fsp.readFile(path.join(directory,id+'.json'),'utf8'));
  let metadata;try{metadata=labels(replay);}catch(error){return {id,ok:false,split:splits[id],examples:0,reason:error.message};}
  await bridge.call({type:'begin',id,...metadata,rating:replay.rating??null});
  const result=await new Promise((resolve,reject)=>{
   let chain=Promise.resolve(),settled=false;
   const done=(value,error)=>{if(settled)return;settled=true;clearTimeout(timer);worker.off('message',receive);worker.off('error',onError);worker.off('exit',onExit);error?reject(error):resolve(value);};
   const onError=error=>done(null,error),onExit=code=>done(null,new Error('Replay worker exited '+code));
   const timer=setTimeout(()=>{
    if(clock.sample()){interrupt({type:'interrupt'});done(null,new Error('Dataset suspended; retry in-flight battle'));}
    else {done({reason:'dataset/replay-time-limit'});void worker.terminate();}
   },deadline);
   const receive=message=>{
    if(message.type==='frame'){
     chain=chain.then(async()=>{
      const frame=message.frame;
      // K never crosses the feature-worker boundary. A capped debug sample is the only raw-frame storage.
      const {knowledge,...input}=frame;
      await bridge.call({type:'frame',frame:input});
      if(samples<50){samples++;fs.appendFileSync(path.join(output,'sample.jsonl'),JSON.stringify(frame)+'\n');}
      worker.postMessage({type:'ack'});
     }).catch(error=>{if(error.message.startsWith('dataset/feature:')){done({reason:error.message,restart_worker:true});void worker.terminate();}else done(null,error);});
    }else chain.then(()=>done(message.type==='failed'?{reason:message.reason}:{})).catch(error=>done(null,error));
   };
   worker.on('message',receive);worker.once('error',onError);worker.once('exit',onExit);worker.postMessage({type:'battle',id,file:path.join(directory,id+'.json')});
  });
  if(result.reason){await bridge.call({type:'abort',id});return {id,ok:false,split:splits[id],examples:0,reason:result.reason,restart_worker:!!result.restart_worker};}
  const saved=await bridge.call({type:'end',id});return {id,ok:true,split:splits[id],examples:saved.examples};
 }
 try{
  await Promise.all(Array.from({length:workers},async()=>{
   const fresh=()=>{const worker=new Worker(__filename,{resourceLimits:{maxOldGenerationSizeMb:1024}});pool.add(worker);return worker;};
   let worker=fresh();
   while(cursor<queue.length){
    const id=queue[cursor++];if(interrupted)throw new Error('Dataset interrupted');
    let row;
    for(let attempt=1;attempt<=2;attempt++){
     row=await battle(id,worker);
     if(row.reason==='dataset/replay-time-limit'||row.restart_worker){pool.delete(worker);worker=fresh();}
     if(row.reason!=='dataset/replay-time-limit')break;
     row.attempts=attempt;if(attempt===2)break;
    }
    await journal.append(row);rows.push(row);progress();
   }
  }));
  const compact=await bridge.call({type:'finalize',rows,shard_size:shardSize});
  const result={...definition,...compact,failures:rows.filter(r=>!r.ok),battles:rows.length,wall_time_seconds:(performance.now()-started)/1000};
  await atomicWrite(path.join(output,'manifest.json'),JSON.stringify(result,null,2)+'\n');return result;
 }finally{
  clearInterval(clockTimer);process.off('message',interrupt);process.off('disconnect',disconnected);await Promise.all([...pool].map(worker=>worker.terminate()));await bridge.close();await journal.close();
 }
}

if(isMainThread&&require.main===module){
 const args=process.argv.slice(2);
 if(args.includes('--supervise')){
  if(!option(args,'manifest'))args.push('--manifest='+path.resolve(option(args,'output'),'build.jsonl'));
  if(!option(args,'corpus-manifest'))args.push('--corpus-manifest='+path.resolve(option(args,'files')));
  require('../replay_repro/supervise.cjs').supervise(args.filter(a=>a!=='--supervise'),{entry:__filename,priority:os.constants.priority.PRIORITY_NORMAL}).catch(failure);
 }else if(process.connected)build(args).then(complete).catch(failure);
 else throw new Error('Run dataset jobs with --supervise');
}
module.exports={build,splitIds,labels};
