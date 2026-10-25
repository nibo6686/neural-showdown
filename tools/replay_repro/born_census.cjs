'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {Worker, isMainThread, parentPort} = require('node:worker_threads');
const {performance} = require('node:perf_hooks');
const {retry,atomicWrite,Journal,SuspensionClock}=require('./durable_io.cjs');

if (!isMainThread) parentPort.on('message', async task => {
  const started = performance.now();
  try {
    const replay = JSON.parse(fs.readFileSync(task.file, 'utf8'));
    if (replay.id !== task.id) throw new Error('replay/manifest-id-mismatch');
    const result = await require('./replay_session.cjs').replaySession(replay, {collect: false, kdiff: task.kdiff, ownerMoves: task.ownerMoves});
    parentPort.postMessage({...result, seconds: (performance.now() - started) / 1000});
  } catch (error) {
    parentPort.postMessage({id: task.id, born: false, reason: error.message,
      ...(error.replayResult || {}), seconds: (performance.now() - started) / 1000});
  }
});

function summarize(rows, timing) {
  const summary = {replays: rows.length, born: 0, skipped: 0, failures: {}, boundaries: 0,
    matched_records: 0, switch_failure_kinds: {},
    kdiff: rows.some(row => row.kdiff) ? {checks: 0, mismatches: 0, rows: {}} : null, ...timing};
  for (const row of rows) {
    if (row.born) summary.born++;
    else {if (row.skipped) summary.skipped++; const reason = row.reason.split(':')[0]; summary.failures[reason] = (summary.failures[reason] || 0) + 1;}
    summary.boundaries += row.boundaries || 0; summary.matched_records += row.matched_records || 0;
    for (const source of new Set(row.switch_sources || [])) summary.switch_failure_kinds[source] = (summary.switch_failure_kinds[source] || 0) + 1;
    if (row.kdiff) {
      summary.kdiff.checks += row.kdiff.checks; summary.kdiff.mismatches += row.kdiff.mismatches;
      for (const [key, counts] of Object.entries(row.kdiff.rows)) {
        const group = summary.kdiff.rows[key] ||= {checks: 0, unknown: 0, mismatches: 0};
        for (const field of ['checks', 'unknown', 'mismatches']) group[field] += counts[field];
      }
    }
  }
  return summary;
}

/** Journal outcomes remain separate; selection metadata is replaced atomically. */
async function writeBornAdmission(file, outcomes, options) {
  const entries = (await retry(() => fs.promises.readFile(file,'utf8'),options)).trim().split('\n').filter(Boolean).map(JSON.parse);
  const admitted = new Set(entries.filter(row => row.admitted).map(row => row.id)), updates = new Map();
  for (const row of outcomes) {
    if (!admitted.has(row.id) || updates.has(row.id) || typeof row.born !== 'boolean') throw new Error('Invalid born admission outcome');
    updates.set(row.id, {complete: row.born, kdiff_mismatches: row.kdiff?.mismatches ?? null,
      ...(row.reason === undefined ? {} : {reason: row.reason}), ...(row.skipped === undefined ? {} : {skipped: row.skipped})});
  }
  await atomicWrite(file,entries.map(row => JSON.stringify(updates.has(row.id) ? {...row, born_session: updates.get(row.id)} : row)+'\n').join(''),options);
}

async function runBornCensus(args, {workerFile=__filename,clock=new SuspensionClock(),tickMs=1000}={}) {
  const option = name => args.find(a => a.startsWith('--' + name + '='))?.slice(name.length + 3);
  const directory = args.find(a => !a.startsWith('--'));
  if (!directory) throw new Error('Replay directory required');
  const workers = Number(option('workers') || 2), deadline = Number(option('replay-timeout-ms') || 120000);
  const memory = option('worker-memory-mb') === undefined ? undefined : Number(option('worker-memory-mb'));
  if (!Number.isInteger(workers) || workers < 1 || workers > 16 || !Number.isSafeInteger(deadline) || deadline < 1000) throw new Error('Invalid born census limits');
  if (memory !== undefined && (!Number.isSafeInteger(memory) || memory < 64 || memory > 8192)) throw new Error('Invalid worker memory limit');
  const notify = data => {if(process.connected)process.send({type:'status',...data});};
  const io={notify},manifest=option('manifest')||path.join(directory,'born-admission.jsonl'),admitted=option('admitted')||path.join(directory,'admission.jsonl');
  let entries=(await retry(()=>fs.promises.readFile(admitted,'utf8'),io)).trim().split('\n').filter(Boolean).map(JSON.parse).filter(row=>row.admitted);
  if(option('files')){const selected=new Set(JSON.parse(await fs.promises.readFile(option('files'),'utf8')));entries=entries.filter(row=>selected.has(row.id+'.json'));}
  if(option('limit'))entries=entries.slice(0,Number(option('limit')));
  if(!entries.length)throw new Error('No admitted replay records selected');
  const selectedCount=entries.length,selected=new Set(entries.map(row=>row.id)),journal=new Journal(manifest,io);
  const jobs=new Set(),pool=new Set();let stopping=false,next=0,records=Promise.resolve(),timer,lanes=[];
  const interrupt=reason=>{for(const job of [...jobs])job.cancel(reason);};
  const stop=()=>{stopping=true;interrupt('stopped');};
  const control=message=>{if(message.type==='interrupt')interrupt('interrupted');if(message.type==='stop')stop();};
  if(selected.size!==entries.length)throw new Error('Duplicate admitted replay IDs');
  const rows=await journal.open(args.includes('--resume')),completed=new Set();
  const started=performance.now();
  try {
    for(const row of rows){
      if(!selected.has(row.id)||completed.has(row.id)||typeof row.born!=='boolean'||args.includes('--kdiff')&&row.born&&!row.kdiff)throw new Error('Invalid resumed born outcome');
      completed.add(row.id);
    }
    entries=entries.filter(row=>!completed.has(row.id));
    const counts={passed:rows.filter(r=>r.born).length,failed:rows.filter(r=>!r.born).length,k_checks:rows.reduce((n,r)=>n+(r.kdiff?.checks||0),0),k_mismatches:rows.reduce((n,r)=>n+(r.kdiff?.mismatches||0),0)};
    const progress=()=>notify({status:'running',completed:rows.length,total:selectedCount,interrupted:clock.epoch,...counts});
    const record=row=>{
      records=records.then(async()=>{
        await journal.append(row);rows.push(row);counts[row.born?'passed':'failed']++;counts.k_checks+=row.kdiff?.checks||0;counts.k_mismatches+=row.kdiff?.mismatches||0;
        if(args.includes('--update-admission')&&rows.length%250===0)await writeBornAdmission(admitted,rows,io);
        progress();if(rows.length%25===0)console.error(`Born ${rows.length}/${selectedCount}; passed ${rows.filter(r=>r.born).length}`);
      });return records;
    };
    const checkClock=()=>{if(clock.sample()){interrupt('interrupted');notify({status:'running',suspension_detected:true});return true;}return false;};
    timer=setInterval(()=>{if(!checkClock())for(const job of [...jobs])if(performance.now()-job.started>=deadline)job.cancel('timeout');},tickMs);
    process.on('message',control);process.on('SIGTERM',stop);process.on('SIGINT',stop);process.on('disconnect',stop);progress();
    const task=(entry,lane)=>new Promise((resolve,reject)=>{
      let finished=false;const worker=lane.worker;
      const finish=(result,error)=>{if(finished)return;finished=true;jobs.delete(job);worker.removeListener('message',message);worker.removeListener('error',failed);worker.removeListener('exit',exited);error?reject(error):resolve(result);};
      const job={started:performance.now(),cancel:reason=>{if(finished)return;lane.worker=null;const termination=worker.terminate();finish({interrupted:reason,termination});}};
      const message=row=>{checkClock();if(!finished){if(row.id!==entry.id)return finish(null,new Error('Worker returned a foreign replay ID'));finish({row});}};
      const failed=error=>finish(null,error),exited=code=>finish(null,new Error('Worker exited unexpectedly: '+code));
      jobs.add(job);worker.on('message',message);worker.on('error',failed);worker.on('exit',exited);
      worker.postMessage({id:entry.id,file:path.join(directory,entry.id+'.json'),kdiff:args.includes('--kdiff'),ownerMoves:args.includes('--owner-moves')});
    });
    await Promise.all(lanes=Array.from({length:Math.min(workers,entries.length)},async()=>{
      const lane={worker:null};
      try {while(next<entries.length){
        const entry=entries[next++];let timeouts=0;
        if(entry.turns>500&&process.env.NEURAL_LONG_TESTS!=='1'){await record({id:entry.id,born:false,skipped:true,reason:'long-case-opt-in: over 500 turns; NEURAL_LONG_TESTS=1'});continue;}
        for(;;){
          if(stopping)throw new Error('Census stopped by operator or supervisor disconnect');
          if(!lane.worker){lane.worker=new Worker(workerFile,memory===undefined?{}:{resourceLimits:{maxOldGenerationSizeMb:memory}});const instance=lane.worker;pool.add(instance);instance.on('exit',()=>pool.delete(instance));}
          const result=await task(entry,lane);
          if(result.interrupted){
            await result.termination;
            if(result.interrupted==='timeout'&&++timeouts===2){await record({id:entry.id,born:false,reason:'replay-time-limit',attempts:2});break;}
            if(result.interrupted!=='timeout')timeouts=0;
            continue;
          }
          await record(result.row);break;
        }
      }} finally {if(lane.worker)await lane.worker.terminate();}
    }));
    const summary=summarize(rows,{workers,wall_time_seconds:(performance.now()-started)/1000});
    if(args.includes('--update-admission'))await writeBornAdmission(admitted,rows,io);
    console.log(JSON.stringify(summary));return summary;
  } finally {
    clearInterval(timer);process.removeListener('message',control);process.removeListener('SIGTERM',stop);process.removeListener('SIGINT',stop);process.removeListener('disconnect',stop);
    stopping=true;interrupt('stopped');await Promise.allSettled([...pool].map(worker=>worker.terminate()));await Promise.allSettled(lanes);
    try {await records;if(args.includes('--update-admission'))await writeBornAdmission(admitted,rows,io);} finally {await journal.close();}
  }
}
module.exports = {runBornCensus, summarize, writeBornAdmission};
