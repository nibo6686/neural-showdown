'use strict';
/* Prompt 16 byte-identity corpus. usage: DIST=<dist root containing src/> node prompt16-corpus.cjs <out.json>
   Records sha256 pins of: (a) 3 seeds x v1/v2 pipeline sessions (boundaries + record bundles, incl. forced switch/revival/terminal when reached),
   (b) every hand-authored witness scenario checkpoint restored into LocalBattleEnv and re-serialized (state fingerprint + simulator-state bytes). */
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const dist = process.env.DIST || path.join(root, 'sim-core/dist');
process.env.NODE_PATH = path.join(root, 'sim-core/node_modules'); require('node:module').Module._initPaths();
const sim = (n) => require(path.join(dist, 'src', n));
const w = require('./perspective-fidelity-prompt13-witness.cjs');
const { LocalBattleEnv } = sim('env_manager.js');
const { createPipelineIntegrationSession } = sim('pipeline_integration.js');
const { canonicalActionFromLegalAction } = sim('canonical_action.js');
const { fingerprintSimulatorState } = sim('transition.js');
const h = (x) => crypto.createHash('sha256').update(typeof x === 'string' ? x : JSON.stringify(x)).digest('hex');
(async () => {
  const pins = {};
  for (const seed of [[1, 2, 3, 4], [11, 12, 13, 14], [5, 6, 7, 8]]) for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2']) {
    const key = `pipeline:${seed.join('-')}:${version.slice(-2)}`, rows = [];
    const session = await createPipelineIntegrationSession({ battle_id: `p16-${seed.join('-')}-${version.slice(-2)}`, format: 'gen9randombattle', seed, observation_schema_version: version });
    const take = (res) => rows.push({ kind: session.boundary.kind, step: session.boundary.step_index, fp: session.boundary.state_fingerprint, branch: session.boundary.branch_id, boundary: h(session.boundary), bundles: res ? h(res.record_bundles) : null });
    try {
      take(null);
      for (let i = 0; i < 250; i++) {
        const b = session.boundary; if (b.kind === 'terminal') break;
        let res;
        try {
          if (b.kind === 'joint_actionable') res = await session.step();
          else { const actor = ['p1', 'p2'].find((o) => b.perspectives[o].observation.request && !b.perspectives[o].observation.request.wait);
            const req = b.perspectives[actor].observation.request; const act = canonicalActionFromLegalAction(req, req.legal_actions.available_indices[0]);
            res = b.kind === 'one_sided_revival' ? await session.stepRevival(act) : await session.stepForcedSwitch(act); }
        } catch (e) { rows.push({ error: e.code || e.message }); break; }
        take(res);
      }
    } finally { await session.close(); }
    pins[key] = { n: rows.length, kinds: [...new Set(rows.map((r) => r.kind))], digest: h(rows), rows };
  }
  for (const [name, sc] of Object.entries(w.SCENARIOS)) {
    const hr = await w.runHarness(sc);
    for (const cp of hr.checkpoints) {
      const env = new LocalBattleEnv(`p16-${name}`, w.FORMAT, w.SEED);
      try {
        await env.resetFromSerialized(structuredClone(cp.snapshot), { include_wait_requests: true });
        const s = env.serializeBattle();
        pins[`scenario:${name}:${cp.label}`] = { fp: fingerprintSimulatorState(s), bytes: h(JSON.stringify(s).replace(/\|t:\|\d+/g, '|t:|')), keys: Object.keys(s).filter((k) => k.startsWith('__')) };
      } finally { await env.close(); }
    }
  }
  fs.writeFileSync(process.argv[2], JSON.stringify(pins, null, 1));
  console.log(Object.entries(pins).length, 'pins; pipeline kinds', JSON.stringify(Object.fromEntries(Object.entries(pins).filter(([k]) => k.startsWith('pipeline')).map(([k, v]) => [k, v.kinds]))));
})().catch((e) => { console.error(e); process.exitCode = 1; });
