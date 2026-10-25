'use strict';
const fs=require('node:fs');
const {parentPort}=require('node:worker_threads');
parentPort.on('message',async task=>{
  const input=JSON.parse(fs.readFileSync(task.file,'utf8'));
  let attempt=1;
  if(input.attempts){fs.appendFileSync(input.attempts,'attempt\n');attempt=fs.readFileSync(input.attempts,'utf8').trim().split('\n').length;}
  if(input.hang==='always'||input.hang==='first'&&attempt===1)return;
  await new Promise(resolve=>setTimeout(resolve,input.firstDelay&&attempt===1?input.firstDelay:input.delay||25));
  parentPort.postMessage({id:task.id,born:true,boundaries:1,matched_records:1,seconds:0,
    ...(task.kdiff?{kdiff:{checks:1,mismatches:0,rows:{fixture:{checks:1,unknown:0,mismatches:0}},examples:[]}}:{})});
});
