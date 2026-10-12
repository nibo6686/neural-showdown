'use strict';
/* Prompt 15 probe: per-boundary availability/freshness of the raw addressed request in a real pipeline session. */
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const sim = (n) => require(path.join(root, 'sim-core/dist/src', n));
const { PlayerStateExtractor } = sim('state_extractor.js');
const { LocalBattleEnv } = sim('env_manager.js');
const { createPipelineIntegrationSession } = sim('pipeline_integration.js');
const { canonicalActionFromLegalAction } = sim('canonical_action.js');

let restoring = 0;
const deliveries = []; // {owner, text, restored}
const origHR = PlayerStateExtractor.prototype.handleRequest;
PlayerStateExtractor.prototype.handleRequest = function (json) { deliveries.push({ owner: this.player, text: json, restored: restoring > 0, tracker: this }); return origHR.call(this, json); };
const origReset = LocalBattleEnv.prototype.resetFromSerialized;
LocalBattleEnv.prototype.resetFromSerialized = async function (...a) { restoring++; try { return await origReset.apply(this, a); } finally { restoring--; } };

function describe(session, mark) {
  const b = session.boundary, out = { step: b.step_index, kind: b.kind, owners: {} };
  for (const o of ['p1', 'p2']) {
    const obs = b.perspectives[o].observation;
    const rep = session.environment.getReportedRequest(o);
    const mine = deliveries.filter((d) => d.tracker === session.environment.players[o].tracker);
    const last = mine[mine.length - 1];
    const sinceMark = mine.filter((d) => d.seq > mark);
    out.owners[o] = {
      observation_request_present: !!obs.request, terminated: !!obs.view?.terminated, reported_request: !!rep,
      reported_equals_last_delivery: rep ? JSON.stringify(rep.raw) === last?.text : last === undefined,
      last_delivery_restored: last ? last.restored : null,
      deliveries_since_prev_boundary: sinceMark.length, fresh_since_prev: sinceMark.filter((d) => !d.restored).length,
      last_delivery_is_wait: last ? /^\{"wait":true/.test(last.text) : null,
    };
  }
  return out;
}
(async () => {
  const seeds = (process.argv[2] || '1,2,3,4;11,12,13,14;5,6,7,8').split(';').map((s) => s.split(',').map(Number));
  const report = [];
  for (const seed of seeds) {
    deliveries.length = 0; let seq = 0;
    const origPush = deliveries.push.bind(deliveries); deliveries.push = (d) => { d.seq = ++seq; return origPush(d); };
    const session = await createPipelineIntegrationSession({ battle_id: `p15-${seed.join('-')}`, format: 'gen9randombattle', seed, observation_schema_version: 'observable-battle-state/v2' });
    const trace = [];
    try {
      let mark = 0; trace.push(describe(session, -1)); mark = seq;
      for (let i = 0; i < 250; i++) {
        const b = session.boundary;
        if (b.kind === 'terminal') break;
        let res;
        try {
          if (b.kind === 'joint_actionable') res = await session.step();
          else if (b.kind === 'one_sided_forced_switch' || b.kind === 'one_sided_revival') {
            const actor = ['p1', 'p2'].find((o) => b.perspectives[o].observation.request && !b.perspectives[o].observation.request.wait);
            const req = b.perspectives[actor].observation.request;
            const act = canonicalActionFromLegalAction(req, req.legal_actions.available_indices[0]);
            res = b.kind === 'one_sided_revival' ? await session.stepRevival(act) : await session.stepForcedSwitch(act);
          } else { trace.push({ unsupported: b.kind }); break; }
        } catch (e) { trace.push({ error: e.code || e.message }); break; }
        trace.push(describe(session, mark)); mark = seq;
      }
    } finally { await session.close(); }
    report.push({ seed, boundaries: trace.length, kinds: trace.reduce((a, t) => (t.kind ? (a[t.kind] = (a[t.kind] || 0) + 1, a) : a), {}), trace });
  }
  // summarize invariants
  const sum = { boundaries: 0, owners_with_request: 0, reported_neq_last: 0, last_restored: 0, no_fresh_delivery_with_request: 0, terminal_owner_rows: 0, terminal_with_prior_delivery: 0, kinds: {} };
  for (const r of report) for (const t of r.trace) if (t.kind) {
    sum.boundaries++; sum.kinds[t.kind] = (sum.kinds[t.kind] || 0) + 1;
    for (const o of Object.values(t.owners)) {
      if (t.kind === 'terminal') { sum.terminal_owner_rows++; if (o.last_delivery_restored !== null) sum.terminal_with_prior_delivery++; }
      if (o.reported_request) { sum.owners_with_request++; if (!o.reported_equals_last_delivery) sum.reported_neq_last++; if (o.last_delivery_restored) sum.last_restored++; if (t.step > 0 && o.fresh_since_prev === 0) sum.no_fresh_delivery_with_request++; }
    }
  }
  console.log(JSON.stringify({ summary: sum, per_seed: report.map((r) => ({ seed: r.seed, boundaries: r.boundaries, kinds: r.kinds, tail: r.trace.slice(-2) })) }, null, 1));
})().catch((e) => { console.error(e); process.exitCode = 1; });
