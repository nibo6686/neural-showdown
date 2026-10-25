'use strict';
const path=require('node:path');
const root=path.resolve(__dirname,'../../..');
const {runBornCensus}=require(path.join(root,'tools/replay_repro/born_census.cjs'));
const {complete,failure}=require(path.join(root,'tools/replay_repro/durable_io.cjs'));
runBornCensus(process.argv.slice(2),{workerFile:path.join(__dirname,'durable_worker.cjs'),tickMs:25}).then(complete).catch(failure);
