'use strict';
/* Prompt 15 probe: live LocalBattleEnv rejection -> captured snapshot -> restore; P15_MODE selects patch (default none). */
const w = require('./perspective-fidelity-prompt13-witness.cjs');
if (process.env.P15_MODE) require('./perspective-fidelity-prompt15-active-request-patch.cjs');
const { LocalBattleEnv } = w.sim('env_manager.js');
const flags = (r) => r && r.raw.active && (({ trapped, maybeTrapped }) => ({ trapped, maybeTrapped }))(r.raw.active[0]);
async function envFrom(snapshot, id) {
  const env = new LocalBattleEnv(id, w.FORMAT, w.SEED);
  const res = await env.resetFromSerialized(structuredClone(snapshot), { include_wait_requests: true });
  return { env, res };
}
(async () => {
  const h = await w.runHarness(w.SCENARIOS.shadow_tag_rejected);
  const start = h.checkpoints.find((c) => c.label === 'start').snapshot;
  const { env, res } = await envFrom(start, 'p15-live');
  const out = { mode: process.env.P15_MODE || 'none', start_p1_flags: flags(res.requests.p1) };
  try {
    const r = await env.step({ p1: 'switch 2' });
    out.after_rejection_live_flags = flags(r.requests.p1);
    out.after_rejection_live_text = JSON.stringify(r.requests.p1.raw);
    const snap = env.captureSeededSnapshot(null);
    out.snapshot_fingerprint = snap.state_fingerprint;
    out.snapshot_keys_extra = Object.keys(snap.simulator_state).filter((k) => !['sides','log','field','prngSeed','prng','queue','turn','ended'].includes(k)).filter((k) => k.startsWith('__') || k.includes('terminal'));
    const { env: env2, res: res2 } = await envFrom(snap.simulator_state, 'p15-restored');
    try {
      const rt = JSON.stringify(res2.requests.p1.raw);
      out.restored_flags = flags(res2.requests.p1);
      out.restored_equals_live = rt === out.after_rejection_live_text;
      const snap2 = env2.captureSeededSnapshot(null);
      out.recaptured_fingerprint_equal = snap2.state_fingerprint === snap.state_fingerprint;
      // can the restored env still legally continue? choose default (tackle) for p1, p2 default
      const next = await env2.step({ p1: 'move 1', p2: 'move 1' });
      out.continue_ok = !!next && next.info.turn;
    } finally { await env2.close(); }
  } finally { await env.close(); }
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exitCode = 1; });
