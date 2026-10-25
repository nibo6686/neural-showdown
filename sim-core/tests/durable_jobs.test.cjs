'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {spawn,execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),tools=path.join(root,'tools/replay_repro');
const {Journal,retry,SuspensionClock,sleep}=require(path.join(tools,'durable_io.cjs'));
const {runBornCensus}=require(path.join(tools,'born_census.cjs'));
const workerFile=path.join(__dirname,'fixtures/durable_worker.cjs');
const entry=path.join(__dirname,'fixtures/durable_child.cjs');
async function until(check,limit=12000){const start=Date.now();while(Date.now()-start<limit){const value=await check();if(value)return value;await sleep(25);}throw new Error('Fixture condition timed out');}
async function read(file){try{return JSON.parse(await fs.readFile(file,'utf8'));}catch(error){if(error.code==='ENOENT'||error instanceof SyntaxError)return null;throw error;}}
async function rows(file){try{return (await fs.readFile(file,'utf8')).split('\n').slice(0,-1).filter(Boolean).map(JSON.parse);}catch(error){if(error.code==='ENOENT')return [];throw error;}}
async function fixture(count=30,native=false){
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'neural-R1-'));
 execFileSync('git',['init','-q'],{cwd:dir,windowsHide:true,timeout:10000});
 execFileSync('git',['config','core.autocrlf','false'],{cwd:dir,windowsHide:true,timeout:10000});
 await fs.writeFile(path.join(dir,'source'),'fixture\n');execFileSync('git',['add','source'],{cwd:dir,windowsHide:true,timeout:10000});
 execFileSync('git',['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'],{cwd:dir,windowsHide:true,timeout:10000});
 let replay;
 if(native){replay=JSON.parse(await fs.readFile(path.join(__dirname,'fixtures/replay-repro/gen9randombattle-2699618521.json'),'utf8'));
  replay.inputlog=replay.inputlog.split(/\r?\n/).filter(l=>/^>(version|start|player) /.test(l)).concat('>forcewin p2').join('\n');
  const log=replay.log.split(/\r?\n/);replay.log=log.slice(0,log.indexOf('|turn|1')+1).concat('|-message|Fixture forfeited.','|win|Fixture').join('\n');}
 const entries=[];for(let i=0;i<count;i++){const id='case-'+String(i).padStart(3,'0');entries.push({id,admitted:true,turns:1});await fs.writeFile(path.join(dir,id+'.json'),JSON.stringify(native?{...replay,id}:{delay:100}));}
 await fs.writeFile(path.join(dir,'admission.jsonl'),entries.map(JSON.stringify).join('\n')+'\n');return dir;
}
function launch(dir,name='job',extra=[],native=false){
 const journal=path.join(dir,name+'.jsonl'),args=[dir,'--born','--kdiff','--owner-moves','--workers=3','--replay-timeout-ms=10000','--update-admission','--manifest='+journal,...extra];
 const script=`require(${JSON.stringify(path.join(tools,'supervise.cjs'))}).supervise(${JSON.stringify(args)},{cwd:${JSON.stringify(dir)},entry:${JSON.stringify(native?path.join(tools,'census.cjs'):entry)},tickMs:50,restartDelayMs:50,priority:0}).catch(e=>{console.error(e);process.exitCode=1;});`;
 const child=spawn(process.execPath,['-e',script],{cwd:dir,windowsHide:true,stdio:['ignore','pipe','pipe']});
 let output='';child.stdout.on('data',d=>{output+=d;});child.stderr.on('data',d=>{output+=d;});
 const done=new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>resolve({code,output}));});
 return {child,done,journal,status:path.join(dir,name+'.run.json')};
}
async function cleanup(dir,jobs=[]){for(const job of jobs){if(job.child.exitCode===null){job.child.kill();await job.done;}}await fs.rm(dir,{recursive:true,force:true});}

test('R1 hard-killed census resumes 30 replay fixtures with identical outcomes', {timeout:45000},async()=>{
 const dir=await fixture(30,true),jobs=[];
 try{
  const baseline=launch(dir,'baseline',[],true);jobs.push(baseline);assert.equal((await baseline.done).code,0);
  const restarted=launch(dir,'restarted',[],true);jobs.push(restarted);
  const running=await until(async()=>{const s=await read(restarted.status);return s?.child_pid&&(await rows(restarted.journal)).length>=3?s:null;});
  process.kill(running.child_pid,'SIGKILL');
  const result=await restarted.done;assert.equal(result.code,0,result.output);
  const status=await read(restarted.status);assert.equal(status.status,'complete');assert.equal(status.restarts,1);
  const sorted=rs=>rs.map(({seconds,...row})=>row).sort((a,b)=>a.id.localeCompare(b.id));
  assert.deepEqual(sorted(await rows(restarted.journal)),sorted(await rows(baseline.journal)));
  const admission=await rows(path.join(dir,'admission.jsonl'));assert.ok(admission.every(r=>r.born_session.complete&&r.born_session.kdiff_mismatches===0));
  // An idempotent complete resume writes no duplicate outcomes.
  const again=launch(dir,'restarted',['--resume'],true);jobs.push(again);assert.equal((await again.done).code,0);assert.equal((await rows(again.journal)).length,30);
  const prior=await fs.readFile(again.status,'utf8'),input=await fs.readFile(path.join(dir,'admission.jsonl'),'utf8');await fs.appendFile(path.join(dir,'admission.jsonl'),JSON.stringify({id:'foreign',admitted:true})+'\n');
  const wrong=launch(dir,'restarted',['--resume'],true);jobs.push(wrong);assert.equal((await wrong.done).code,1);assert.equal(await fs.readFile(again.status,'utf8'),prior);
  await fs.writeFile(path.join(dir,'admission.jsonl'),input);await fs.appendFile(path.join(dir,'source'),'changed\n');
  execFileSync('git',['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qam','changed'],{cwd:dir,windowsHide:true,timeout:10000});
  const wrongCode=launch(dir,'restarted',['--resume'],true);jobs.push(wrongCode);assert.equal((await wrongCode.done).code,1);assert.equal(await fs.readFile(again.status,'utf8'),prior);
 }finally{await cleanup(dir,jobs);}
});

test('R1 exclusive Windows journal lock reports blocked-write and loses no outcomes', {timeout:20000,skip:process.platform!=='win32'},async()=>{
 const dir=await fixture(),jobs=[];let locker;
 try{
  const journal=path.join(dir,'locked.jsonl');await fs.writeFile(journal,'');
  const script="$handle=[IO.File]::Open($args[0],[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);try{Write-Output 'LOCKED';Start-Sleep -Seconds 5}finally{$handle.Dispose()}";
  // Pass the path through the environment; no shell interpolation of file contents.
  const lockerFile=path.join(dir,'lock.ps1');await fs.writeFile(lockerFile,script.replace('$args[0]','$env:R1_LOCK_FILE'));
  locker=spawn('pwsh',['-NoProfile','-File',lockerFile],{windowsHide:true,env:{...process.env,R1_LOCK_FILE:journal},stdio:['ignore','pipe','pipe']});
  await new Promise((resolve,reject)=>{locker.stdout.once('data',resolve);locker.once('error',reject);});
  const job=launch(dir,'locked');jobs.push(job);
  const blocked=await until(async()=>{const s=await read(job.status);return s?.status==='blocked-write'?s:null;});
  assert.ok(['EBUSY','EPERM','EACCES'].includes(blocked.error));
  const result=await job.done;assert.equal(result.code,0,result.output);assert.equal((await rows(journal)).length,30);assert.equal((await read(job.status)).status,'complete');
 }finally{locker?.kill();await cleanup(dir,jobs);}
});

test('R1 simulated wall jump reruns in-flight replay without a timeout outcome', {timeout:10000},async()=>{
 const dir=await fixture(1),attempts=path.join(dir,'attempts');let jump=0;
 try{
  await fs.writeFile(path.join(dir,'case-000.json'),JSON.stringify({attempts,firstDelay:500,delay:10}));
  const clock=new SuspensionClock({gapMs:1000,wall:()=>Date.now()+jump});
  const run=runBornCensus([dir,'--workers=1','--replay-timeout-ms=1000','--manifest='+path.join(dir,'jump.jsonl')],{workerFile,clock,tickMs:10});
  await until(async()=>{try{return (await fs.stat(attempts)).size>0;}catch{return false;}});jump=3600000;
  const summary=await run;assert.equal(summary.born,1);assert.deepEqual(summary.failures,{});assert.equal(clock.epoch,1);
  assert.equal((await fs.readFile(attempts,'utf8')).trim().split('\n').length,2);
 }finally{await cleanup(dir);}
});

test('R1 genuine timeouts are final only after one retry', {timeout:10000},async()=>{
 const dir=await fixture(2);
 try{
  for(const [i,hang] of ['first','always'].entries())await fs.writeFile(path.join(dir,'case-00'+i+'.json'),JSON.stringify({hang,attempts:path.join(dir,'attempts'+i)}));
  const summary=await runBornCensus([dir,'--workers=2','--replay-timeout-ms=1000','--manifest='+path.join(dir,'timeout.jsonl')],{workerFile,tickMs:10});
  assert.equal(summary.born,1);assert.equal(summary.failures['replay-time-limit'],1);
  const failed=(await rows(path.join(dir,'timeout.jsonl'))).find(r=>!r.born);assert.equal(failed.attempts,2);
  for(let i=0;i<2;i++)assert.equal((await fs.readFile(path.join(dir,'attempts'+i),'utf8')).trim().split('\n').length,2);
 }finally{await cleanup(dir);}
});

test('R1 keep-awake helper exits by PID when its supervisor is killed', {timeout:12000,skip:process.platform!=='win32'},async()=>{
 const script=`require(${JSON.stringify(path.join(tools,'supervise.cjs'))}).keepAwake().then(h=>{console.log(h.pid);setInterval(()=>{},1000);});`;
 const parent=spawn(process.execPath,['-e',script],{windowsHide:true,stdio:['ignore','pipe','pipe']});let helper;
 try{
  helper=await new Promise((resolve,reject)=>{parent.stdout.once('data',data=>resolve(Number(String(data).trim())));parent.once('error',reject);});
  assert.ok(Number.isInteger(helper));process.kill(helper,0);parent.kill('SIGKILL');
  await until(()=>{try{process.kill(helper,0);return false;}catch(error){return error.code==='ESRCH';}},6000);
 }finally{parent.kill();if(helper)try{process.kill(helper);}catch{}}
});

test('R1 retries sharing errors beyond a minute and repairs only a torn journal tail',async()=>{
 let calls=0;const delays=[],statuses=[];
 assert.equal(await retry(()=>{if(++calls<23)throw Object.assign(new Error('locked'),{code:['EBUSY','EPERM','EACCES'][calls%3]});return 7;},{delay:async ms=>{delays.push(ms);},notify:s=>statuses.push(s)}),7);
 assert.ok(delays.reduce((a,b)=>a+b,0)>60000);assert.equal(statuses[0].status,'blocked-write');assert.equal(statuses.at(-1).status,'running');
 await assert.rejects(retry(()=>{throw Object.assign(new Error('invalid'),{code:'EINVAL'});}),/invalid/);
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'neural-R1-journal-')),file=path.join(dir,'rows.jsonl');
 try{let j=new Journal(file);await j.open(false);await j.append({id:'a'});await j.close();await fs.appendFile(file,'{"id":"torn');
  j=new Journal(file);assert.deepEqual(await j.open(true),[{id:'a'}]);await j.append({id:'b'});await j.close();assert.deepEqual(await rows(file),[{id:'a'},{id:'b'}]);
  await fs.appendFile(file,'malformed\n');j=new Journal(file);await assert.rejects(j.open(true),SyntaxError);assert.equal(j.handle,undefined);
 }finally{await cleanup(dir);}
});
