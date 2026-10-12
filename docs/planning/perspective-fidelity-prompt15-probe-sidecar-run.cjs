'use strict';
/* Prompt 15 probe: prototype retention (test-owned tracker tap) -> S01b TS builder at every real pipeline boundary -> JSON for Python validation.
   usage: node probe-sidecar-run.cjs <out.json> [seeds "a,b,c,d;..."] */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const sim = (n) => require(path.join(root, 'sim-core/dist/src', n));
const { PlayerStateExtractor } = sim('state_extractor.js');
const { LocalBattleEnv } = sim('env_manager.js');
const { createPipelineIntegrationSession } = sim('pipeline_integration.js');
const { canonicalActionFromLegalAction } = sim('canonical_action.js');
const { buildRequestKnowledge } = sim('request_knowledge.js');
let restoring = 0, seq = 0;
const ledger = new Map(); // tracker -> [{seq,text,restored}]
const origHR = PlayerStateExtractor.prototype.handleRequest;
PlayerStateExtractor.prototype.handleRequest = function (json) {
  if (!ledger.has(this)) ledger.set(this, []);
  ledger.get(this).push({ seq: ++seq, text: json, restored: restoring > 0 });
  return origHR.call(this, json);
};
const origReset = LocalBattleEnv.prototype.resetFromSerialized;
LocalBattleEnv.prototype.resetFromSerialized = async function (...a) { restoring++; try { return await origReset.apply(this, a); } finally { restoring--; } };

(async () => {
  const seeds = (process.argv[3] || '1,2,3,4;11,12,13,14;5,6,7,8').split(';').map((s) => s.split(',').map(Number));
  const out = [], stats = { boundaries: 0, built: 0, refused: {}, roundtrip_mismatch: 0, deliveries: 0, terminal_null: 0 };
  for (const seed of seeds) for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2']) {
    const session = await createPipelineIntegrationSession({ battle_id: `p15-${seed.join('-')}-${version.slice(-2)}`, format: 'gen9randombattle', seed, observation_schema_version: version });
    const rows = [];
    const take = () => {
      const b = session.boundary; stats.boundaries++;
      for (const o of ['p1', 'p2']) {
        const obs = JSON.parse(JSON.stringify(b.perspectives[o].observation));
        const list = ledger.get(session.environment.players[o].tracker) || [];
        const last = list[list.length - 1];
        const terminal = !!obs.view.terminated;
        const text = terminal ? null : (last ? last.text : null);
        const provenance = last && !last.restored ? 'fresh_delivery' : 'restored';
        const row = { seed, version, step: b.step_index, owner: o, kind: b.kind, text, provenance, observation: obs };
        try { row.record = buildRequestKnowledge(o, text, obs, terminal ? 'fresh_delivery' : provenance); stats.built++; if (terminal) stats.terminal_null++; }
        catch (e) { row.refused = e.code || e.message; stats.refused[row.refused] = (stats.refused[row.refused] || 0) + 1; }
        rows.push(row);
      }
    };
    try {
      take();
      for (let i = 0; i < 250; i++) {
        const b = session.boundary; if (b.kind === 'terminal') break;
        try {
          if (b.kind === 'joint_actionable') await session.step();
          else { const actor = ['p1', 'p2'].find((o) => b.perspectives[o].observation.request && !b.perspectives[o].observation.request.wait);
            const req = b.perspectives[actor].observation.request; const act = canonicalActionFromLegalAction(req, req.legal_actions.available_indices[0]);
            if (b.kind === 'one_sided_revival') await session.stepRevival(act); else await session.stepForcedSwitch(act); }
        } catch (e) { break; }
        take();
      }
    } finally { await session.close(); }
    for (const [t, l] of ledger) for (const d of l) { stats.deliveries++; if (JSON.stringify(JSON.parse(d.text)) !== d.text) stats.roundtrip_mismatch++; }
    ledger.clear(); out.push(...rows);
  }
  fs.writeFileSync(process.argv[2], JSON.stringify({ stats, rows: out }));
  console.log(JSON.stringify(stats));
})().catch((e) => { console.error(e); process.exitCode = 1; });
