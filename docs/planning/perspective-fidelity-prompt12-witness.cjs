'use strict';
/**
 * Prompt 12 test-owned witness. Nothing here is production capture.
 *
 * - Legacy side: a real pinned local PipelineIntegrationSession (one joint step
 *   per observation schema) yields actual bundles/observations/beliefs.
 * - Source side: an independent BattleStream harness replays the same start
 *   payload and the same choices, capturing the generated team arrays, the exact
 *   addressed `|request|` text per owner (before any normalization) and the
 *   spectator ledger. The session is only used to corroborate that ledger.
 * - Audit builder: derives a structurally valid knowledge audit from the capture.
 *   Registry expectations are NOT read from audits; tests feed the capture directly.
 * - Expected DATA record IDs come from the Python validator (independent oracle).
 * Nothing is persisted; the CLI prints one JSON document for the Python tests.
 */
const path = require('node:path');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '../..');
const sim = (name) => require(path.join(root, 'sim-core/dist/src', name));
const ps = () => require(path.join(root, 'sim-core/node_modules/pokemon-showdown'));
const psBattle = () => require(path.join(root, 'sim-core/node_modules/pokemon-showdown/dist/sim/battle'));
const fixtureDir = path.join(root, 'docs/contracts/fixtures/perspective-knowledge-v1');

const SEED = [101, 202, 303, 404];
const FORMAT = 'gen9randombattle';
const VERSIONS = ['observable-battle-state/v1', 'observable-battle-state/v2'];

function offsetSeed(seed, delta) {
  return [(seed[0] + delta) & 0xffff, (seed[1] + delta * 2) & 0xffff, (seed[2] + delta * 3) & 0xffff, (seed[3] + delta * 4) & 0xffff];
}

/** Hand-written (not audit-derived) conversion of a generated PokemonSet array to the wire `set` shape. */
function toWireSets(team) {
  const six = (table) => (table ? { type: 'six_stats', data: { hp: table.hp, atk: table.atk, def: table.def, spa: table.spa, spd: table.spd, spe: table.spe } } : null);
  return team.map((set, index) => ({
    slot: index + 1,
    name: set.name ?? '',
    species: set.species ?? '',
    moves: [...set.moves],
    item: set.item ?? '',
    ability: set.ability ?? '',
    tera_type: set.teraType ?? null,
    level: set.level ?? null,
    gender: set.gender ? set.gender : null,
    shiny: set.shiny ?? null,
    ball: set.ball ?? null,
    nature: set.nature ? set.nature : null,
    evs: six(set.evs),
    ivs: six(set.ivs),
    happiness: set.happiness ?? null,
  }));
}

/** Independent pinned BattleStream harness: exact addressed bytes before any normalization. */
async function runHarness(choiceRounds) {
  const { BattleStream, Teams } = ps();
  const { extractChannelMessages } = psBattle();
  const { projectPipelineProtocolPrefix } = sim('pipeline_integration.js');
  const events = [];
  const stream = new (class extends BattleStream {
    pushMessage(type, data) { events.push([type, data]); super.pushMessage(type, data); }
  })({ keepAlive: true });
  const teams = { p1: Teams.generate(FORMAT, { seed: offsetSeed(SEED, 11) }), p2: Teams.generate(FORMAT, { seed: offsetSeed(SEED, 29) }) };
  const rawLedger = [];
  const requests = { p1: [], p2: [] };
  let consumed = 0;
  const flush = () => {
    const pending = [];
    for (; consumed < events.length; consumed++) {
      const [type, data] = events[consumed];
      if (type === 'update') rawLedger.push(...extractChannelMessages(data, [0])[0]);
      else if (type === 'sideupdate') {
        const at = data.indexOf('\n');
        const owner = data.slice(0, at); const line = data.slice(at + 1);
        if (line.startsWith('|request|')) pending.push([owner, line.slice('|request|'.length)]);
      }
    }
    const cursor = projectPipelineProtocolPrefix(rawLedger).length;
    for (const [owner, json] of pending) requests[owner].push({ sequence: requests[owner].length, cursor, json });
  };
  try {
    const payload = [
      `>start ${JSON.stringify({ formatid: FORMAT, seed: SEED })}`,
      `>player p1 ${JSON.stringify({ name: 'Agent-1', team: Teams.pack(teams.p1) })}`,
      `>player p2 ${JSON.stringify({ name: 'Agent-2', team: Teams.pack(teams.p2) })}`,
    ].join('\n');
    await stream.write(payload); flush();
    for (const round of choiceRounds) {
      await stream.write(`>p1 ${round.p1}\n>p2 ${round.p2}`); flush();
    }
  } finally { stream.destroy(); }
  return { teams, rawLedger, ledger: projectPipelineProtocolPrefix(rawLedger), requests };
}

function pythonValidate(bundle) {
  const code = ['import sys,json', 'from neural.pipeline_json_wire import load_json', 'from neural.pipeline_record import validate_pipeline_bundle',
    'b=load_json(sys.stdin)', 'r=validate_pipeline_bundle(b)', 'print(json.dumps({"record_id":r["record_id"]}))'].join('\n');
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
  env.PYTHONPATH = path.join(root, 'trainer/src');
  const py = spawnSync(process.env.PYTHON || 'D:/Anaconda/envs/neuralgpu/python.exe', ['-c', code], { cwd: root, env, input: JSON.stringify(bundle), encoding: 'utf8', timeout: 60000, maxBuffer: 16 * 1024 * 1024 });
  if (py.error || py.status !== 0) throw new Error('Python legacy validation failed');
  return JSON.parse(py.stdout).record_id;
}

async function capture(version) {
  const { createPipelineIntegrationSession, validatePipelineLinkedRecordBundle } = sim('pipeline_integration.js');
  const { canonicalActionFromLegalAction } = sim('canonical_action.js');
  const battleId = 'prompt12-source-witness-' + version.slice(-2);
  const session = await createPipelineIntegrationSession({ battle_id: battleId, format: FORMAT, seed: SEED, observation_schema_version: version });
  let boundaries, bundles, choices;
  try {
    const first = session.boundary; const actions = {}; choices = { p1: '', p2: '' };
    for (const owner of ['p1', 'p2']) {
      const request = first.perspectives[owner].observation.request;
      const index = request.legal_actions.available_indices[0];
      actions[owner] = canonicalActionFromLegalAction(request, index);
      choices[owner] = request.legal_actions.actions[index].choice;
    }
    const result = await session.step(actions);
    boundaries = [first, result.boundary]; bundles = result.record_bundles;
    const copy = JSON.parse(JSON.stringify(bundles));
    for (const owner of ['p1', 'p2']) validatePipelineLinkedRecordBundle(copy[owner]);
  } finally { await session.close(); }
  const harness = await runHarness([choices]);
  // Corroboration only: harness ledger/cursors must equal the legacy observation prefixes.
  const cursors = [];
  boundaries.forEach((boundary, b) => {
    for (const owner of ['p1', 'p2']) {
      const observation = boundary.perspectives[owner].observation;
      const delivery = harness.requests[owner][b];
      if (!delivery || delivery.cursor !== observation.event_cursor
        || JSON.stringify(harness.ledger.slice(0, delivery.cursor)) !== JSON.stringify(observation.protocol_prefix)) throw new Error('harness/session ledger mismatch');
    }
    cursors.push(harness.requests.p1[b].cursor);
  });
  const recordIds = { p1: pythonValidate(bundles.p1), p2: pythonValidate(bundles.p2) };
  return {
    version, battle_id: battleId, seed: SEED, cursors,
    origin: { battle_key: battleId, format: FORMAT, engine: 'pokemon-showdown@0.11.10', rule_version: 'pk-rules/v1' },
    team_sets: { p1: toWireSets(harness.teams.p1), p2: toWireSets(harness.teams.p2) },
    ledger: harness.ledger, requests: harness.requests,
    bundles, python_record_ids: recordIds,
    // TypeScript adapter output, recorded so the Python tests can assert cross-runtime parity.
    ts_adapter_record_ids: Object.fromEntries(['p1', 'p2'].map((owner) => {
      const b = bundles[owner];
      return [owner, sim('perspective_knowledge_source.js').legacyDataRecordId({ battle_id: b.battle_id, perspective: owner, protocol_prefix: b.input_observation.protocol_prefix,
        observation_id: b.input_observation.observation_id, action_id: b.action.action_id, belief_id: b.input_belief.belief_id, transition_id: b.transition.transition_id })];
    })),
  };
}

/** Structurally valid audit derived from the capture (never from a registry). */
function buildAudit(w, form, options = {}) {
  const { knowledgeIdentity } = sim('perspective_knowledge.js');
  const nonactor = options.nonactor ?? [];
  const profiles = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'profiles.json'), 'utf8'));
  const profile = profiles.find((p) => p.name === 'owner-loadout-complete/v1');
  const rows = {};
  const kinds = ['origin', 'source', 'prefix', 'evidence', 'certificate', 'fact', 'starting', 'current', 'request', 'knowledge', 'profile', 'verdict', 'boundary', 'binding'];
  for (const kind of kinds) rows[kind] = new Map();
  const seal = (row) => {
    const sealed = { ...row, id: knowledgeIdentity(row) };
    rows[row.kind].set(sealed.id, sealed);
    return sealed.id;
  };
  const origin = seal({ kind: 'origin', ...(options.origin ?? w.origin) });
  rows.profile.set(profile.id, profile);
  const owners = ['p1', 'p2'];
  const boundaryCount = w.cursors.length;
  const prefixes = new Map();
  const publicFor = (cursor) => {
    if (!prefixes.has(cursor)) {
      const records = w.ledger.slice(0, cursor);
      const source = seal({ kind: 'source', origin, source_type: 'public_prefix', owner: null, provider: 'indexed-public/v1', delivery_seq: null, delivery_cursor: null, phase: 'chronological', team: [], records, raw_request: null });
      const prefix = seal({ kind: 'prefix', origin, parser: 'indexed-public/v1', records });
      const evidence = seal({ kind: 'evidence', origin, owner: null, scope: 'public', source, prefix, record_indices: [], team_slot: null, writer: 'boundary/v1' });
      prefixes.set(cursor, { source, prefix, evidence });
    }
    return prefixes.get(cursor);
  };
  const starting = {};
  for (const owner of owners) {
    if (options.sourceless) { // source-less incomplete canary: no original authority is asserted
      starting[owner] = seal({ kind: 'starting', origin, owner, policy: 'simulator-causal/v1', source: null, revision: 0, parent: null, facts: [], crosswalk: [] });
      continue;
    }
    const set = w.team_sets[owner];
    const source = seal({ kind: 'source', origin, source_type: 'owner_initialization', owner, provider: 'addressed-team-provider/v1', delivery_seq: 0, delivery_cursor: 0, phase: 'before_effects', team: set, records: [], raw_request: null });
    const evidence = seal({ kind: 'evidence', origin, owner, scope: 'original', source, prefix: null, record_indices: [], team_slot: 1, writer: 'submitted-set/v1' });
    const fact = seal({ kind: 'fact', owner, subject: `${owner}:roster:1`, family: 'K01', property: 'roster_species', state: 'known', value: { type: 'text', data: set[0].species }, reason: 'none', freshness: 'immutable', precision: 'exact', observed_at: 0, evidence: [evidence], certificate: null, effect_key: null });
    starting[owner] = seal({ kind: 'starting', origin, owner, policy: 'simulator-causal/v1', source, revision: 0, parent: null, facts: [fact], crosswalk: [] });
  }
  const families = Array.from({ length: 20 }, (_, i) => ({ family: 'K' + String(i + 1).padStart(2, '0'), result: 'unsupported', reason: 'unimplemented_family' }));
  const previousCurrent = { p1: null, p2: null };
  const boundaries = [];
  const knowledgeByBoundary = [];
  for (let b = 0; b < boundaryCount; b++) {
    const cursor = w.cursors[b];
    const pub = publicFor(cursor);
    const type = b === 0 ? 'initial' : 'mid';
    const perOwner = {};
    for (const owner of owners) {
      const delivery = w.requests[owner][b];
      const raw = JSON.parse(delivery.json);
      const requestSource = seal({ kind: 'source', origin, source_type: 'owner_request', owner, provider: 'addressed-request/v1', delivery_seq: delivery.sequence, delivery_cursor: delivery.cursor, phase: 'chronological', team: [], records: [], raw_request: { json: delivery.json } });
      const request = seal({ kind: 'request', origin, owner, source: requestSource, prefix: pub.prefix, sequence: delivery.sequence, cursor: delivery.cursor, actionable: raw.wait !== true, facts: [] });
      const fact = seal({ kind: 'fact', owner, subject: `${owner}:side`, family: 'K20', property: 'boundary_kind', state: 'known', value: { type: 'text', data: type }, reason: 'none', freshness: 'current', precision: 'exact', observed_at: cursor, evidence: [pub.evidence], certificate: null, effect_key: null });
      const current = seal({ kind: 'current', origin, owner, prefix: pub.prefix, cursor, parent: previousCurrent[owner], facts: [fact] });
      previousCurrent[owner] = current;
      const knowledge = seal({ kind: 'knowledge', origin, owner, policy: 'simulator-causal/v1', starting: starting[owner], current, request, boundary: b });
      const verdict = seal({ kind: 'verdict', knowledge, profile: profile.id, families, result: 'incomplete' });
      perOwner[owner] = { knowledge, verdict };
    }
    knowledgeByBoundary.push(perOwner);
  }
  const legacyFor = (owner, b) => {
    const perspective = w.bundles[owner];
    return b === 0
      ? { observation: perspective.input_observation.observation_id, belief: perspective.input_belief.belief_id }
      : { observation: perspective.successor_observation.observation_id, belief: perspective.successor_belief.belief_id };
  };
  let parent = null;
  for (let b = 0; b < boundaryCount; b++) {
    const bindings = owners.map((owner) => {
      const legacy = legacyFor(owner, b);
      const actor = b > 0 && !nonactor.includes(owner) ? w.python_record_ids[owner] : null;
      return { owner, knowledge: knowledgeByBoundary[b][owner].knowledge, verdict: knowledgeByBoundary[b][owner].verdict, observation_id: legacy.observation, belief_id: legacy.belief, actor_record_id: actor };
    });
    parent = seal({ kind: 'boundary', origin, index: b, cursor: w.cursors[b], boundary_type: b === 0 ? 'initial' : 'mid', parent, restored_from: null, bindings });
    boundaries.push(parent);
  }
  for (let b = 1; b < boundaryCount; b++) {
    for (const owner of owners) {
      const before = legacyFor(owner, b - 1), after = legacyFor(owner, b);
      const actor = !nonactor.includes(owner);
      seal({ kind: 'binding', origin, owner, input_index: b - 1, successor_index: b, input_knowledge: knowledgeByBoundary[b - 1][owner].knowledge, successor_knowledge: knowledgeByBoundary[b][owner].knowledge, input_observation: before.observation, successor_observation: after.observation, input_belief: before.belief, successor_belief: after.belief, transition: actor ? w.bundles[owner].transition.transition_id : null, actor_record: actor ? w.python_record_ids[owner] : null });
    }
  }
  const tables = {};
  for (const kind of kinds) {
    const sorted = [...rows[kind].values()].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    tables[kind] = form === 'compact' ? Object.fromEntries(sorted.map((row) => [row.id, row])) : sorted;
  }
  const audit = { kind: 'audit', schema: 'perspective-knowledge/v1', form, origin, required_profile: profile.id, target_boundary: boundaries.at(-1), tables };
  audit.id = knowledgeIdentity(audit);
  return audit;
}

async function main() {
  const output = {};
  for (const version of VERSIONS) {
    const w = await capture(version);
    w.audits = { ordinary: buildAudit(w, 'ordinary'), full: buildAudit(w, 'full'), compact: buildAudit(w, 'compact') };
    w.nonactor_audit = buildAudit(w, 'ordinary', { nonactor: ['p2'] });
    w.sourceless_audit = buildAudit(w, 'ordinary', { sourceless: true });
    output[version] = w;
  }
  process.stdout.write(JSON.stringify(output));
}

module.exports = { SEED, FORMAT, VERSIONS, capture, buildAudit, runHarness, toWireSets };
if (require.main === module) main().catch((error) => { console.error(error.message); process.exitCode = 1; });
