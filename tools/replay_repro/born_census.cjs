'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {Worker, isMainThread, parentPort} = require('node:worker_threads');
const {performance} = require('node:perf_hooks');

if (!isMainThread) parentPort.on('message', async task => {
  const started = performance.now();
  try {
    const replay = JSON.parse(fs.readFileSync(task.file, 'utf8'));
    if (replay.id !== task.id) throw new Error('replay/manifest-id-mismatch');
    const result = await require('./replay_session.cjs').replaySession(replay, {collect: false, kdiff: task.kdiff});
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

async function runBornCensus(args) {
  const option = name => args.find(a => a.startsWith('--' + name + '='))?.slice(name.length + 3);
  const directory = args.find(a => !a.startsWith('--'));
  if (!directory) throw new Error('Replay directory required');
  const workers = Number(option('workers') || 2), deadline = Number(option('replay-timeout-ms') || 120000);
  if (!Number.isInteger(workers) || workers < 1 || workers > 16 || !Number.isSafeInteger(deadline) || deadline < 1000) throw new Error('Invalid born census limits');
  const manifest = option('manifest') || path.join(directory, 'born-admission.jsonl');
  const admitted = option('admitted') || path.join(directory, 'admission.jsonl');
  let entries = fs.readFileSync(admitted, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).filter(row => row.admitted);
  if (option('files')) {const selected = new Set(JSON.parse(fs.readFileSync(option('files'), 'utf8'))); entries = entries.filter(row => selected.has(row.id + '.json'));}
  if (option('limit')) entries = entries.slice(0, Number(option('limit')));
  if (!entries.length) throw new Error('No admitted replay records selected');
  fs.writeFileSync(manifest, '');
  const rows = [], started = performance.now(), activeWorkers = new Set(), timers = new Set(); let next = 0;
  const record = row => {
    fs.appendFileSync(manifest, JSON.stringify(row) + '\n'); rows.push(row);
    if (rows.length % 25 === 0) console.error(`Born ${rows.length}/${entries.length}; passed ${rows.filter(r => r.born).length}`);
  };
  try {await Promise.all(Array.from({length: Math.min(workers, entries.length)}, () => new Promise((resolve, reject) => {
    let worker, timer, active, generation = 0;
    const dispatch = () => {
      clearTimeout(timer); timers.delete(timer);
      while (next < entries.length && entries[next].turns > 500 && process.env.NEURAL_LONG_TESTS !== '1') {
        record({id: entries[next++].id, born: false, skipped: true, reason: 'long-case-opt-in: over 500 turns; NEURAL_LONG_TESTS=1'});
      }
      if (next === entries.length) {worker?.terminate().then(resolve, reject); if (!worker) resolve(); return;}
      active = entries[next++];
      if (!worker) spawn();
      const epoch = generation;
      timer = setTimeout(() => {
        if (epoch !== generation) return;
        generation++; const old = worker; worker = null;
        old.terminate().then(() => {record({id: active.id, born: false, reason: 'replay-time-limit'}); dispatch();}, reject);
      }, deadline);
      timers.add(timer);
      worker.postMessage({id: active.id, file: path.join(directory, active.id + '.json'), kdiff: args.includes('--kdiff')});
    };
    const spawn = () => {
      worker = new Worker(__filename); const epoch = ++generation;
      activeWorkers.add(worker);
      const instance = worker; worker.on('exit', () => activeWorkers.delete(instance));
      worker.on('message', row => {if (epoch !== generation) return; try {record(row); dispatch();} catch (error) {clearTimeout(timer); worker.terminate(); reject(error);}});
      worker.on('error', error => {
        if (epoch !== generation) return;
        clearTimeout(timer); generation++; worker = null;
        try {record({id: active.id, born: false, reason: 'worker-failure: ' + error.message}); dispatch();} catch (failure) {reject(failure);}
      });
    };
    dispatch();
  })));} finally {
    for (const timer of timers) clearTimeout(timer);
    await Promise.allSettled([...activeWorkers].map(worker => worker.terminate()));
  }
  const summary = summarize(rows, {workers, wall_time_seconds: (performance.now() - started) / 1000});
  console.log(JSON.stringify(summary));
  return summary;
}
module.exports = {runBornCensus, summarize};
