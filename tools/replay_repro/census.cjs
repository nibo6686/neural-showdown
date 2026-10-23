'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {Worker, isMainThread, workerData} = require('node:worker_threads');
const {performance} = require('node:perf_hooks');
const {main} = require('./index.cjs');

if (!isMainThread) {
  main(workerData.directory,true,true,workerData.options).catch(error=>{console.error(error);process.exitCode=1;});
} else if (require.main === module && process.argv.includes('--born')) {
  require('./born_census.cjs').runBornCensus(process.argv.slice(2)).catch(error=>{console.error(error);process.exitCode=1;});
} else if (require.main === module) {
  const args=process.argv.slice(2), option=name=>args.find(a=>a.startsWith('--'+name+'='))?.slice(name.length+3);
  const directory=args.find(a=>!a.startsWith('--'));
  const workers=Number(option('workers')||2), limit=option('limit')?Number(option('limit')):undefined;
  const manifest=option('manifest')||path.join(directory,'admission.jsonl');
  if(!Number.isInteger(workers)||workers<1||workers>16)throw new Error('Invalid worker count');
  const files=option('files')?JSON.parse(fs.readFileSync(option('files'),'utf8')):undefined;
  const started=performance.now();
  (async()=>{
    const shards=Array.from({length:workers},(_,i)=>manifest+`.part-${i}`);
    const pool=[];
    try {await Promise.all(shards.map((file,i)=>new Promise((resolve,reject)=>{
      const worker=new Worker(__filename,{workerData:{directory,options:{manifest:file,files,shardIndex:i,shardCount:workers,limit:limit?Math.ceil(limit/workers):undefined,quiet:true}}});
      pool.push(worker);
      worker.on('error',reject);worker.on('exit',code=>code?reject(new Error(`Census worker ${i} exited ${code}`)):resolve());
    })));} catch(error) {
      await Promise.allSettled(pool.map(worker=>worker.terminate()));
      throw error;
    }
    const rows=shards.flatMap(file=>fs.readFileSync(file,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse)).sort((a,b)=>a.id.localeCompare(b.id));
    fs.writeFileSync(manifest,rows.map(row=>JSON.stringify(row)).join('\n')+'\n');
    for(const file of shards)fs.unlinkSync(file);
    const summary=summarizeAdmission(rows,{workers,wall_time_seconds:(performance.now()-started)/1000});
    console.log(JSON.stringify(summary));
  })().catch(error=>{console.error(error);process.exitCode=1;});
}


function summarizeAdmission(rows, timing={}) {
  const mainRows=rows.filter(row=>/^gen9randombattle-/.test(row.id));
  const summary={replays:rows.length,main_server_replays:mainRows.length,other_server_replays:rows.length-mainRows.length,
    admitted:mainRows.filter(r=>r.admitted).length,by_commit:Object.create(null),exclusions:{},other_server_exclusions:{},failure_kinds:{},diff_mismatches:0,checks:0,...timing};
  for(const row of rows){
    if(!/^gen9randombattle-/.test(row.id)) {
      if(row.reason)summary.other_server_exclusions[row.reason]=(summary.other_server_exclusions[row.reason]||0)+1;
      continue;
    }
    const group=summary.by_commit[row.server_commit??'unknown']||={replays:0,admitted:0};group.replays++;if(row.admitted)group.admitted++;
    if(row.reason)summary.exclusions[row.reason]=(summary.exclusions[row.reason]||0)+1;
    for(const kind of row.failure_kinds||[])summary.failure_kinds[kind]=(summary.failure_kinds[kind]||0)+1;
    summary.diff_mismatches+=row.diff_mismatch_count||0;summary.checks+=row.checks||0;
  }
  const ratings=mainRows.filter(r=>r.admitted&&typeof r.rating==='number').map(r=>r.rating).sort((a,b)=>a-b);
  summary.admitted_ratings={reported:ratings.length,missing:summary.admitted-ratings.length,min:ratings[0]??null,q1:ratings[Math.floor(ratings.length*.25)]??null,median:ratings[Math.floor(ratings.length*.5)]??null,q3:ratings[Math.floor(ratings.length*.75)]??null,max:ratings.at(-1)??null};
  return summary;
}
module.exports={summarizeAdmission};
