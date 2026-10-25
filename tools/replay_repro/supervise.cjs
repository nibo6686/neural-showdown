'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {createHash}=require('node:crypto');
const {execFileSync,spawn,fork}=require('node:child_process');
const {retry,atomicWrite,SuspensionClock,sleep}=require('./durable_io.cjs');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const option=(args,name)=>args.find(a=>a.startsWith('--'+name+'='))?.slice(name.length+3);
function git(cwd,args){return execFileSync('git',args,{cwd,encoding:'utf8',timeout:10000,windowsHide:true}).trim();}
async function identity(args,cwd) {
  const directory=path.resolve(cwd,args.find(a=>!a.startsWith('--')));
  const source=option(args,'corpus-manifest')||(args.includes('--born')?(option(args,'admitted')||path.join(directory,'admission.jsonl')):null);
  if(!source)throw new Error('Ordinary supervised census requires --corpus-manifest=<immutable input manifest>');
  const bytes=await retry(()=>fs.readFile(path.resolve(cwd,source),'utf8'));
  // born_session is an output checkpoint, not part of the corpus definition.
  const manifest=args.includes('--born')?bytes.trim().split('\n').filter(Boolean).map(JSON.parse).map(({born_session,...row})=>row):bytes;
  return {commit:git(cwd,['rev-parse','HEAD']),corpus_manifest_sha256:hash(JSON.stringify(manifest)),
    configuration:args.filter(arg=>arg!=='--resume')};
}

async function keepAwake() {
  if(process.platform!=='win32')return null;
  const helper=spawn('pwsh',['-NoProfile','-File',path.join(__dirname,'keep_awake.ps1'),'-SupervisorId',String(process.pid)],{windowsHide:true,stdio:['ignore','pipe','pipe']});
  await new Promise((resolve,reject)=>{
    let output='',error='';const timer=setTimeout(()=>{helper.kill();reject(new Error('Keep-awake helper startup timeout'));},15000);
    helper.stderr.on('data',data=>{error+=data;});
    helper.stdout.on('data',data=>{output+=data;if(output.includes('"ready":true')){clearTimeout(timer);resolve();}});
    helper.once('error',cause=>{clearTimeout(timer);reject(cause);});
    helper.once('exit',code=>{clearTimeout(timer);reject(new Error('Keep-awake helper exited '+code+': '+error));});
  });
  return helper;
}

/** Supervise only infrastructure. Replay failures remain final journal outcomes. */
async function supervise(args,{cwd=process.cwd(),entry=path.join(__dirname,'census.cjs'),tickMs=15000,restartDelayMs=1000,maxRestarts=20,priority=os.constants.priority.PRIORITY_BELOW_NORMAL}={}) {
  const directory=args.find(a=>!a.startsWith('--'));if(!directory)throw new Error('Replay directory required');
  const journal=path.resolve(cwd,option(args,'manifest')||path.join(directory,args.includes('--born')?'born-admission.jsonl':'admission.jsonl'));
  const prefix=journal.replace(/\.jsonl$/,''),statusFile=path.resolve(cwd,option(args,'status')||prefix+'.run.json'),summaryFile=path.resolve(cwd,option(args,'summary')||prefix+'.summary.json');
  const lock=prefix+'.supervisor.lock';let lockHandle,helper,child,stopping=false,ownedRun=false,timer,stopTimer,writing=Promise.resolve(),dirty=false,writeActive=false;
  let state={schema:'corpus-supervisor/v1',pid:process.pid,status:'running',restarts:0,working_directory:path.resolve(cwd),journal,started_utc:new Date().toISOString()};
  const flush=()=>{
    dirty=true;if(writeActive)return writing;writeActive=true;
    writing=(async()=>{try {while(dirty){dirty=false;state.heartbeat_utc=new Date().toISOString();await atomicWrite(statusFile,JSON.stringify(state,null,2)+'\n');}}finally{writeActive=false;}})();
    return writing;
  };
  const stop=()=>{stopping=true;if(child?.connected)child.send({type:'stop'});stopTimer??=setTimeout(()=>child?.kill(),15000);};
  try {
    try{lockHandle=await fs.open(lock,'wx');}catch(error){
      if(error.code!=='EEXIST')throw error;
      const previous=JSON.parse(await fs.readFile(lock,'utf8'));
      try{process.kill(previous.pid,0);throw new Error('Supervisor already running: '+previous.pid);}catch(cause){if(cause.code!=='ESRCH')throw cause;}
      await fs.unlink(lock);lockHandle=await fs.open(lock,'wx');
    }
    await lockHandle.writeFile(JSON.stringify({pid:process.pid}));await lockHandle.sync();
    helper=await keepAwake();state.keep_awake_pid=helper?.pid??null;
    const pinned=await identity(args,cwd);
    git(cwd,['diff','--exit-code','HEAD','--']);
    let previous;
    try{previous=JSON.parse(await fs.readFile(statusFile,'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}
    if(previous){
      if(!args.includes('--resume'))throw new Error('Existing supervised run requires explicit --resume');
      for(const key of ['commit','corpus_manifest_sha256','configuration'])if(JSON.stringify(previous[key])!==JSON.stringify(pinned[key]))throw new Error('Resume identity mismatch: '+key);
      state.restarts=previous.restarts;state.started_utc=previous.started_utc;
    }else if(args.includes('--resume'))throw new Error('Cannot resume without the pinned run status');
    else {try{if((await fs.stat(journal)).size)throw new Error('Refusing to overwrite an existing journal');}catch(error){if(error.code!=='ENOENT')throw error;}}
    Object.assign(state,pinned);ownedRun=true;
    os.setPriority(process.pid,priority);
    process.on('SIGTERM',stop);process.on('SIGINT',stop);
    const clock=new SuspensionClock({tickMs,gapMs:Math.max(60000,tickMs*4)});
    timer=setInterval(()=>{
      if(helper&&(helper.exitCode!==null||helper.signalCode!==null)){state.error='Keep-awake helper exited unexpectedly';stop();}
      if(clock.sample()){state.suspensions=(state.suspensions||0)+1;if(child?.connected)child.send({type:'interrupt'});}
      flush().catch(error=>{console.error(error);stop();});
    },tickMs);
    await flush();
    for(;;){
      if(stopping)throw new Error('Supervisor stopped by operator');
      const current=await identity(args,cwd);git(cwd,['diff','--exit-code','HEAD','--']);
      for(const key of ['commit','corpus_manifest_sha256'])if(current[key]!==pinned[key])throw new Error('Restart identity mismatch: '+key);
      const childArgs=args.filter(arg=>!/^--(?:status|summary|corpus-manifest)=/.test(arg)&&arg!=='--resume');
      if(previous||state.restarts)childArgs.push('--resume');
      let result;
      const outcome=await new Promise((resolve,reject)=>{
        child=fork(entry,childArgs,{cwd,windowsHide:true,stdio:['ignore','pipe','pipe','ipc']});
        state.child_pid=child.pid;state.status='running';delete state.error;
        os.setPriority(child.pid,priority);
        child.stdout.on('data',data=>process.stdout.write(data));child.stderr.on('data',data=>process.stderr.write(data));
        child.on('message',message=>{
          if(message.type==='complete')result=message.summary;
          else if(message.type==='status'){
            const changed=state.status!==message.status;Object.assign(state,message);delete state.type;
            if(message.write_recovered){delete state.error;delete state.path;delete state.blocked_ms;delete state.write_attempts;}
            if(changed)flush().catch(reject);
          }
        });
        child.once('error',error=>resolve({code:null,signal:null,error:error.message}));child.once('exit',(code,signal)=>resolve({code,signal}));
        flush().catch(reject);
      });
      state.child_pid=null;state.last_exit=outcome;
      if(outcome.code===0&&result){
        await atomicWrite(summaryFile,JSON.stringify(result)+'\n');state.status='complete';state.summary=result;state.ended_utc=new Date().toISOString();await flush();return result;
      }
      if(stopping)throw new Error('Supervisor stopped by operator');
      if(state.restarts>=maxRestarts)throw new Error('Restart limit reached ('+maxRestarts+')');
      state.restarts++;state.status='restarting';state.error='Census exited without successful completion';await flush();
      await sleep(Math.min(60000,restartDelayMs*2**Math.min(state.restarts-1,6)));
    }
  } catch(error) {
    if(ownedRun){state.status='gave-up';state.error=error.message;state.ended_utc=new Date().toISOString();await flush();}
    throw error;
  } finally {
    clearInterval(timer);clearTimeout(stopTimer);process.removeListener('SIGTERM',stop);process.removeListener('SIGINT',stop);
    if(child?.exitCode===null&&child.signalCode===null){child.kill();await new Promise(resolve=>child.once('exit',resolve));}
    helper?.kill();if(helper&&helper.exitCode===null&&helper.signalCode===null)await new Promise(resolve=>helper.once('exit',resolve));
    if(lockHandle){await lockHandle.close();await fs.unlink(lock);}
  }
}
module.exports={supervise,identity,keepAwake};
if(require.main===module)supervise(process.argv.slice(2)).catch(error=>{console.error(error);process.exitCode=1;});
