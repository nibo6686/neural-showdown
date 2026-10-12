'use strict';
/**
 * Prompt 14 (S01b) test-owned witness. Reuses the Prompt 13 harness (exact addressed `|request|` text from a
 * pinned BattleStream, restored legacy sessions for the unchanged observations) and adds the lead's
 * decision-6 cases. Nothing here is production capture. The CLI prints one JSON document:
 *   { cases: {id: captured case}, records: {id: {p1, p2}} }   (records built by the TS module under test)
 * `records` is only used for TS/Python parity; expected values in tests come from raw text and literals.
 */
const path = require('node:path');
const w13 = require('./perspective-fidelity-prompt13-witness.cjs');

const root = path.resolve(__dirname, '../..');
const OTHER = 'Blissey\n- Splash\n';

const EXTRA_SCENARIOS = {
  // Struggle because the only move is hidden-disabled by foe Imprison (maybeDisabled with Struggle).
  struggle_maybe_disabled: {
    p1: `Snorlax\nAbility: Immunity\n- Splash\n\n${OTHER}`,
    p2: `Alakazam\nAbility: Magic Guard\n- Imprison\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  // Struggle because every move reached PP 0 (Spite drains the only move).
  struggle_all_pp_zero: {
    p1: `Pikachu\nAbility: Static\n- Destiny Bond\n\n${OTHER}`,
    p2: `Shuckle\nAbility: Sturdy\n- Spite\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }, { p1: 'move 1', p2: 'move 1' }],
  },
  outrage_lock: {
    p1: `Snorlax\nAbility: Immunity\n- Outrage\n- Splash\n\n${OTHER}`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  rollout_lock: {
    p1: `Golem\nAbility: Sturdy\n- Rollout\n- Splash\n\n${OTHER}`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  uproar_lock: {
    p1: `Snorlax\nAbility: Immunity\n- Uproar\n- Splash\n\n${OTHER}`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  // Empty bench: switch-in unavailable, so trapped/maybeTrapped are not emitted and must stay unknown.
  maybe_trapped_empty_bench: {
    p1: `Snorlax\nAbility: Immunity\n- Tackle\n- Splash\n`,
    p2: `Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [],
  },
  locked_empty_bench: {
    p1: `Venusaur\nAbility: Chlorophyll\n- Solar Beam\n- Splash\n`,
    p2: `Blissey\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [{ p1: 'move 1', p2: 'move 1' }],
  },
  // Non-ASCII nickname travels in the exact addressed text.
  unicode_names: {
    p1: `Ñandú 日本 (Snorlax)\nAbility: Immunity\n- Tackle\n- Splash\n\n${OTHER}`,
    p2: `Blissey\n- Splash\n- Tackle\n\nSnorlax\nAbility: Immunity\n- Splash\n`,
    rounds: [],
  },
};
Object.assign(w13.SCENARIOS, EXTRA_SCENARIOS);

const EXTRA_CASES = [
  { id: 'struggle_maybe_disabled', scenario: 'struggle_maybe_disabled', checkpoint: 'round1' },
  { id: 'struggle_all_pp_zero', scenario: 'struggle_all_pp_zero', checkpoint: 'round2' },
  { id: 'outrage_lock', scenario: 'outrage_lock', checkpoint: 'round1' },
  { id: 'rollout_lock', scenario: 'rollout_lock', checkpoint: 'round1' },
  { id: 'uproar_lock', scenario: 'uproar_lock', checkpoint: 'round1' },
  { id: 'maybe_trapped_empty_bench', scenario: 'maybe_trapped_empty_bench', checkpoint: 'start' },
  { id: 'locked_empty_bench', scenario: 'locked_empty_bench', checkpoint: 'round1' },
  { id: 'unicode_names', scenario: 'unicode_names', checkpoint: 'start' },
];

async function captureAll14() {
  const cache = {};
  const cases = {};
  for (const def of [...w13.CASES, ...EXTRA_CASES]) cases[def.id] = await w13.captureCase(def, cache);
  return cases;
}

const sim = (name) => require(path.join(root, 'sim-core/dist/src', name));
const FRESH = 'fresh_delivery';

/** Records for parity: every (case, version, owner) built by the TS module from the harness text and the unchanged observation. */
function buildRecords(cases) {
  const { buildRequestKnowledge } = sim('request_knowledge.js');
  const records = {};
  for (const [id, c] of Object.entries(cases)) {
    records[id] = {};
    for (const version of w13.VERSIONS) {
      for (const owner of ['p1', 'p2']) {
        if (id === 'trapped_after_rejection' && owner === 'p1') continue; // observation is the stale restored one; covered by tests
        const observation = c.versions[version].observations[owner];
        const terminal = observation.view.terminated;
        const rawText = terminal || !observation.request ? null : c.raw[owner].json;
        records[id][`${version.slice(-2)}/${owner}`] = buildRequestKnowledge(owner, rawText, observation, FRESH);
      }
    }
  }
  return records;
}

module.exports = { ...w13, EXTRA_CASES, EXTRA_SCENARIOS, captureAll14, buildRecords };
if (require.main === module) {
  (async () => {
    const cases = await captureAll14();
    process.stdout.write(JSON.stringify({ cases, records: process.argv[2] === '--cases-only' ? null : buildRecords(cases) }));
  })().catch((e) => { console.error(e); process.exitCode = 1; });
}
