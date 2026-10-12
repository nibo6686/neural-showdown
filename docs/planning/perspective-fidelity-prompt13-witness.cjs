'use strict';
/**
 * Prompt 13 (S01a) test-owned witness. Nothing here is production capture.
 *
 * - Source side: an independent pinned BattleStream harness plays hand-authored teams and choices and
 *   captures the exact addressed `|request|` text per owner BEFORE any normalization, plus a privileged
 *   simulator snapshot after every write.
 * - Legacy side: the real PipelineIntegrationSession (v1 and v2) is restored from that snapshot; its
 *   live addressed request (`environment.getRequest(owner).raw`) must equal the harness text, then the
 *   real normalizer/observation/bundle path is read. One joint step yields actual record bundles for
 *   Python validation.
 * Nothing is persisted; the CLI prints one JSON document for the Python tests.
 */
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const sim = (name) => require(path.join(root, 'sim-core/dist/src', name));
const ps = () => require(path.join(root, 'sim-core/node_modules/pokemon-showdown'));

const FORMAT = 'gen9randombattle';
const SEED = [1, 2, 3, 4];
const VERSIONS = ['observable-battle-state/v1', 'observable-battle-state/v2'];

const T = {
  snorlax: (moves, extra = '') => `Snorlax\nAbility: Immunity\n${extra}${moves.map((m) => `- ${m}`).join('\n')}\n`,
};

/** Each scenario: hand-written teams and choice rounds; `checks` name the rounds whose pending requests are examined. */
const SCENARIOS = {
  ordinary: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Rest\n- Curse\n- Body Slam\n\nBlissey\n- Splash\n`,
    p2: `Blissey\n- Splash\n- Tackle\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [],
  },
  choice_lock: {
    p1: `Snorlax @ Choice Band\nAbility: Immunity\n- Tackle\n- Rest\n- Curse\n- Body Slam\n\nBlissey\n- Splash\n`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  encore: {
    p1: `Pikachu\nAbility: Static\n- Tackle\n- Growl\n- Thunder Wave\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Shuckle\nAbility: Sturdy\n- Encore\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  two_turn_lock: {
    p1: `Venusaur\nAbility: Chlorophyll\n- Solar Beam\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  recharge: {
    p1: `Butterfree\nAbility: Compound Eyes\n- Hyper Beam\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  struggle: {
    p1: `Blissey\n- Soft-Boiled\n- Toxic\n- Thunder Wave\n- Protect\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    p2: `Whimsicott\nAbility: Prankster\n- Taunt\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  real_pp_zero: {
    p1: `Pikachu\nAbility: Static\n- Destiny Bond\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Shuckle\nAbility: Sturdy\n- Spite\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }, { p1: 'move 1', p2: 'move 1' }],
  },
  imprison: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Rest\n- Curse\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Alakazam\nAbility: Magic Guard\n- Imprison\n- Tackle\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 4', p2: 'move 1' }],
  },
  shadow_tag: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [],
  },
  mean_look: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Umbreon\nAbility: Synchronize\n- Mean Look\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 2', p2: 'move 1' }],
  },
  shadow_tag_rejected: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'switch 2' }],
  },
  revival_terminal: {
    p1: `Lead (Snorlax)\nAbility: Immunity\n- Memento\n\nPawmot\n- Revival Blessing\n- Splash\n`,
    p2: `Terminus (Snorlax)\nAbility: Immunity\n- Splash\n- Memento\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }, { p1: 'switch 2' }, { p1: 'move 1', p2: 'move 2' }, { p1: 'switch 2' }],
  },
  forced_switch: {
    p1: `Mewtwo\nAbility: Pressure\n- Psystrike\n- Splash\n\nBlissey\n- Splash\n`,
    p2: `Magikarp\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
};

/** Swap the two owners so the same source behaviour is witnessed for the other addressed owner. */
for (const name of ['two_turn_lock', 'recharge', 'struggle', 'imprison', 'shadow_tag', 'mean_look']) {
  const base = SCENARIOS[name];
  SCENARIOS[name + '_mirror'] = { p1: base.p2, p2: base.p1, rounds: base.rounds.map((r) => ({ ...(r.p2 ? { p1: r.p2 } : {}), ...(r.p1 ? { p2: r.p1 } : {}) })) };
}

function pack(text) { const { Teams } = ps(); return Teams.pack(Teams.import(text)); }

/** Pinned BattleStream harness: exact addressed bytes before normalization, plus a snapshot per write. */
async function runHarness(scenario) {
  const { BattleStream } = ps();
  const events = [];
  const stream = new (class extends BattleStream {
    pushMessage(type, data) { events.push([type, data]); super.pushMessage(type, data); }
  })({ keepAlive: true });
  const requests = { p1: [], p2: [] };
  const errors = [];
  const checkpoints = [];
  let consumed = 0;
  const flush = (label) => {
    for (; consumed < events.length; consumed++) {
      const [type, data] = events[consumed];
      if (type !== 'sideupdate') continue;
      const at = data.indexOf('\n');
      const owner = data.slice(0, at);
      for (const line of data.slice(at + 1).split('\n')) {
        if (line.startsWith('|request|')) requests[owner].push({ sequence: requests[owner].length, json: line.slice('|request|'.length) });
        else if (line.startsWith('|error|')) errors.push({ owner, line });
      }
    }
    checkpoints.push({ label, pending: { p1: requests.p1.length - 1, p2: requests.p2.length - 1 }, snapshot: stream.battle ? structuredClone(stream.battle.toJSON()) : null });
  };
  try {
    await stream.write([
      `>start ${JSON.stringify({ formatid: FORMAT, seed: SEED })}`,
      `>player p1 ${JSON.stringify({ name: 'Agent-1', team: pack(scenario.p1) })}`,
      `>player p2 ${JSON.stringify({ name: 'Agent-2', team: pack(scenario.p2) })}`,
    ].join('\n'));
    flush('start');
    for (const [index, round] of scenario.rounds.entries()) {
      await stream.write(['p1', 'p2'].filter((p) => round[p]).map((p) => `>${p} ${round[p]}`).join('\n'));
      flush(`round${index + 1}`);
    }
  } finally { stream.destroy(); }
  return { requests, errors, checkpoints };
}

/** Cases: the scenario checkpoint whose pending addressed requests are examined. */
const CASES = [
  { id: 'ordinary_slots', scenario: 'ordinary', checkpoint: 'start' },
  { id: 'choice_lock_soft', scenario: 'choice_lock', checkpoint: 'round1' },
  { id: 'encore_soft', scenario: 'encore', checkpoint: 'round1' },
  { id: 'two_turn_locked_move', scenario: 'two_turn_lock', checkpoint: 'round1' },
  { id: 'recharge', scenario: 'recharge', checkpoint: 'round1' },
  { id: 'struggle_fallback', scenario: 'struggle', checkpoint: 'round1' },
  { id: 'real_pp_zero', scenario: 'real_pp_zero', checkpoint: 'round2' },
  { id: 'maybe_disabled_imprison', scenario: 'imprison', checkpoint: 'round1', step: { p1: 'move:Splash' }, rejectProbe: { p1: 'move:Tackle' } },
  { id: 'maybe_trapped_shadow_tag', scenario: 'shadow_tag', checkpoint: 'start' },
  { id: 'trapped_after_rejection', scenario: 'shadow_tag_rejected', checkpoint: 'round1', restoredRequestDiffersFromLive: true },
  { id: 'known_trapped_mean_look', scenario: 'mean_look', checkpoint: 'round1' },
  { id: 'waiting_and_forced_switch', scenario: 'forced_switch', checkpoint: 'round1' },
  { id: 'revival_selection_and_waiting', scenario: 'revival_terminal', checkpoint: 'round3', playThroughRevival: true },
  { id: 'terminal_requestless', scenario: 'revival_terminal', checkpoint: 'round4' },
  { id: 'two_turn_locked_move_mirror', scenario: 'two_turn_lock_mirror', checkpoint: 'round1' },
  { id: 'recharge_mirror', scenario: 'recharge_mirror', checkpoint: 'round1' },
  { id: 'struggle_fallback_mirror', scenario: 'struggle_mirror', checkpoint: 'round1' },
  { id: 'maybe_disabled_imprison_mirror', scenario: 'imprison_mirror', checkpoint: 'round1', step: { p2: 'move:Splash' }, rejectProbe: { p2: 'move:Tackle' } },
  { id: 'maybe_trapped_shadow_tag_mirror', scenario: 'shadow_tag_mirror', checkpoint: 'start' },
  { id: 'known_trapped_mean_look_mirror', scenario: 'mean_look_mirror', checkpoint: 'round1' },
];

async function sessionFrom(snapshot, version, battleId) {
  const { LocalBattleEnv } = sim('env_manager.js');
  const { createPipelineIntegrationSession } = sim('pipeline_integration.js');
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(snapshot), options); };
    return await createPipelineIntegrationSession({ battle_id: battleId, format: FORMAT, seed: SEED, observation_schema_version: version });
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}

/** First legal action per actor (ordinary requests: lowest available index; locked requests: the simulator `default`). */
function firstActions(boundary, labels = {}) {
  const { canonicalActionFromLegalAction } = sim('canonical_action.js');
  const actions = {};
  for (const owner of ['p1', 'p2']) {
    const request = boundary.perspectives[owner].observation.request;
    let index = request.legal_actions.available_indices[0];
    if (labels[owner]) index = request.legal_actions.actions.findIndex((a) => a && a.label === labels[owner]);
    if (index < 0) throw new Error('requested label is not legal');
    actions[owner] = canonicalActionFromLegalAction(request, index);
  }
  return actions;
}

async function captureCase(def, harnessCache) {
  const { normalizeRequest, buildLegalActionSet } = sim('action_codec.js');
  const { validatePipelineLinkedRecordBundle } = sim('pipeline_integration.js');
  if (!harnessCache[def.scenario]) harnessCache[def.scenario] = await runHarness(SCENARIOS[def.scenario]);
  const harness = harnessCache[def.scenario];
  const checkpoint = harness.checkpoints.find((c) => c.label === def.checkpoint);
  const raw = {};
  for (const owner of ['p1', 'p2']) {
    const delivery = harness.requests[owner][checkpoint.pending[owner]];
    raw[owner] = delivery ? { sequence: delivery.sequence, json: delivery.json } : null;
  }
  const history = {};
  for (const owner of ['p1', 'p2']) history[owner] = harness.requests[owner].slice(0, checkpoint.pending[owner] + 1).map((r) => r.json);
  const out = { id: def.id, scenario: def.scenario, checkpoint: def.checkpoint, raw, raw_history: history, harness_errors: harness.errors, versions: {} };
  for (const version of VERSIONS) {
    const session = await sessionFrom(checkpoint.snapshot, version, `prompt13-${def.id}-${version.slice(-2)}`);
    try {
      const boundary = session.boundary;
      const entry = { boundary_kind: boundary.kind, observations: {}, live_raw_equals_harness: {}, direct_normalization: {}, bundles: null };
      for (const owner of ['p1', 'p2']) {
        const observation = boundary.perspectives[owner].observation;
        entry.observations[owner] = JSON.parse(JSON.stringify(observation));
        const live = session.environment.getRequest(owner);
        const liveText = live && live.raw ? JSON.stringify(live.raw) : null;
        entry.live_raw_equals_harness[owner] = raw[owner] ? liveText === raw[owner].json : liveText === null;
        if (raw[owner]) {
          const parsed = JSON.parse(raw[owner].json);
          const normalized = normalizeRequest(owner, parsed);
          const { raw: _raw, ...withoutRaw } = normalized;
          entry.direct_normalization[owner] = JSON.parse(JSON.stringify(withoutRaw));
          entry.direct_normalization[owner].legal_actions_from_raw = JSON.parse(JSON.stringify(buildLegalActionSet(parsed)));
        } else entry.direct_normalization[owner] = null;
      }
      if (boundary.kind === 'joint_actionable') {
        const result = await session.step(firstActions(boundary, def.step));
        const copy = JSON.parse(JSON.stringify(result.record_bundles));
        for (const owner of ['p1', 'p2']) validatePipelineLinkedRecordBundle(copy[owner]);
        entry.bundles = JSON.parse(JSON.stringify(result.record_bundles));
      }
      out.versions[version] = entry;
    } finally { await session.close(); }
    if (def.playThroughRevival) {
      // Play the owner-only revival selection to the terminal boundary: the terminal observation carries no request.
      const { canonicalActionFromLegalAction } = sim('canonical_action.js');
      const played = await sessionFrom(checkpoint.snapshot, version, `prompt13-${def.id}-terminal-${version.slice(-2)}`);
      try {
        const request = played.boundary.perspectives.p1.observation.request;
        const result = await played.stepRevival(canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]));
        out.versions[version].after_revival = {
          boundary_kind: result.boundary.kind,
          observations: Object.fromEntries(['p1', 'p2'].map((o) => [o, JSON.parse(JSON.stringify(result.boundary.perspectives[o].observation))])),
        };
      } finally { await played.close(); }
    }
    if (def.rejectProbe) {
      // The request's own legal action is rejected by the simulator: hidden Imprison is not in the emitted request.
      const probe = await sessionFrom(checkpoint.snapshot, version, `prompt13-${def.id}-reject-${version.slice(-2)}`);
      try {
        await probe.step(firstActions(probe.boundary, def.rejectProbe));
        out.versions[version].reject_probe = { rejected: false };
      } catch (error) {
        out.versions[version].reject_probe = { rejected: true, code: error.code, detail: error.message };
      } finally { await probe.close(); }
    }
  }
  return out;
}

async function captureAll() {
  const cache = {};
  const cases = {};
  for (const def of CASES) cases[def.id] = await captureCase(def, cache);
  return cases;
}

module.exports = { FORMAT, SEED, VERSIONS, SCENARIOS, CASES, runHarness, captureCase, captureAll, sessionFrom, sim, ps, pack };
if (require.main === module) {
  (async () => {
    const mode = process.argv[2];
    if (mode === '--raw') {
      const only = process.argv[3];
      for (const [name, scenario] of Object.entries(SCENARIOS)) {
        if (only && only !== name) continue;
        const h = await runHarness(scenario);
        console.log('=====', name, JSON.stringify(h.errors));
        for (const owner of ['p1', 'p2']) h.requests[owner].forEach((r) => console.log(owner, r.sequence, r.json.length > 1500 ? r.json.slice(0, 1500) + '...' : r.json));
      }
    } else process.stdout.write(JSON.stringify(await captureAll()));
  })().catch((e) => { console.error(e); process.exitCode = 1; });
}
