'use strict';
/* Prompt 15 probe (test-owned, read-only against production code): restored-branch stale request diagnosis. */
const path = require('node:path');
const w = require('./perspective-fidelity-prompt13-witness.cjs');
const { LocalBattleEnv } = w.sim('env_manager.js');

async function restore(snapshot) {
  const env = new LocalBattleEnv({ id: 'p15-restore', format: w.FORMAT, seed: w.SEED });
  const res = await env.resetFromSerialized(structuredClone(snapshot), { include_wait_requests: true });
  return { env, res };
}
(async () => {
  const h = await w.runHarness(w.SCENARIOS.shadow_tag_rejected);
  const cp = h.checkpoints.find((c) => c.label === 'round1');
  const live = h.requests.p1.map((r) => r.json);
  const out = { harness_p1_deliveries: live.length, harness_errors: h.errors };
  const LL = JSON.parse(live[live.length - 1]); out.live_last_p1 = null;
  out.live_prev_active0_flags = (({trapped,maybeTrapped}) => ({trapped,maybeTrapped}))(JSON.parse(live[live.length - 2]).active[0]);
  out.snapshot_side_keys = Object.keys(cp.snapshot.sides[0]);
  out.snapshot_has_activeRequest_key = Object.prototype.hasOwnProperty.call(cp.snapshot.sides[0], 'activeRequest');
  out.snapshot_activeRequest = cp.snapshot.sides[0].activeRequest;
  const { env, res } = await restore(cp.snapshot);
  try {
    const r = res.requests.p1;
    const rt = r ? JSON.stringify(r.raw) : null;

    out.restored_equals_live_last = rt === live[live.length - 1];
    out.restored_equals_live_prev = rt === live[live.length - 2];
    out.restored_active0_flags = r && (({trapped,maybeTrapped}) => ({trapped,maybeTrapped}))(r.raw.active[0]);
    out.live_active0_flags = (({trapped,maybeTrapped}) => ({trapped,maybeTrapped}))(LL.active[0]);
    // restored sim-side state
    const battle = env.battleStream.battle;
    out.sim_side0_activeRequest_flags = (({trapped,maybeTrapped}) => ({trapped,maybeTrapped}))(battle.sides[0].activeRequest.active[0]);
    out.sim_pokemon_trapped_flags = { trapped: battle.sides[0].active[0].trapped, maybeTrapped: battle.sides[0].active[0].maybeTrapped };
    // the snapshot re-serialized from the restored env
    const again = env.serializeBattle();
    out.reserialized_has_activeRequest_key = Object.prototype.hasOwnProperty.call(again.sides[0], 'activeRequest');

  } finally { await env.close(); }
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exitCode = 1; });
