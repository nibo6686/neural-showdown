'use strict';
/* Prompt 15 probe: rejected hidden-disabled move (Imprison) re-emits a mutated request; does S01b accept it; does restore regenerate it? */
const w = require('./perspective-fidelity-prompt13-witness.cjs');
if (process.env.P15_MODE) require('./perspective-fidelity-prompt15-active-request-patch.cjs');
const { LocalBattleEnv } = w.sim('env_manager.js');
const { buildRequestKnowledge } = w.sim('request_knowledge.js');
(async () => {
  const h = await w.runHarness(w.SCENARIOS.imprison);
  const cp = h.checkpoints.find((c) => c.label === 'round1');
  const mk = async (snap, id) => { const e = new LocalBattleEnv(id, w.FORMAT, w.SEED); const r = await e.resetFromSerialized(structuredClone(snap), { include_wait_requests: true }); return { e, r }; };
  const { e, r } = await mk(cp.snapshot, 'p15-dis');
  const out = { mode: process.env.P15_MODE || 'none' };
  try {
    const before = r.requests.p1.raw.active[0];
    out.before = { maybeDisabled: before.maybeDisabled, moves: before.moves.map((m) => [m.id, m.disabled, m.disabledSource]) };
    let res;
    for (let n = 1; n <= before.moves.length; n++) {
      res = await e.step({ p1: `move ${n}` });
      const diag = e.diagnostics().players.p1.last_choice_error;
      if (diag) { out.rejected_choice = `move ${n}`; break; }
      break;
    }
    const live = res.requests.p1;
    out.after_live = live && { maybeDisabled: live.raw.active[0].maybeDisabled, moves: live.raw.active[0].moves.map((m) => [m.id, m.disabled, m.disabledSource]), keys: Object.keys(live.raw.active[0].moves[0]) };
    out.live_has_disabledSource = !!live && JSON.stringify(live.raw).includes('disabledSource');
    if (live) {
      try { buildRequestKnowledge('p1', JSON.stringify(live.raw), e.getRequest ? null : null, 'fresh_delivery'); } catch (err) { out.s01b_builder_on_mutated_live = err.code || err.message; }
      const snap = e.captureSeededSnapshot(null);
      const { e: e2, r: r2 } = await mk(snap.simulator_state, 'p15-dis2');
      try { const rr = r2.requests.p1; out.restored = rr && { maybeDisabled: rr.raw.active[0].maybeDisabled, moves: rr.raw.active[0].moves.map((m) => [m.id, m.disabled, m.disabledSource]) }; out.restored_equals_live = rr && JSON.stringify(rr.raw) === JSON.stringify(live.raw); } finally { await e2.close(); }
    }
  } finally { await e.close(); }
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exitCode = 1; });
