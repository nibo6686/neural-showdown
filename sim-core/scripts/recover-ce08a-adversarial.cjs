// Recover the exact long-fixture envelope only; never invoke actor publication.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {createPipelineIntegrationSession} = require('../dist/src/pipeline_integration');
const {continuePipelineEpisode} = require('../dist/src/pipeline_episode');
const {canonicalActionFromLegalAction} = require('../dist/src/canonical_action');
const {PUBLIC_STAGES_SCHEMA_VERSION} = require('../dist/src/observable_state');
const {createPipelineEpisodeEvidence, sealPipelineEpisodeEvidence, episodeEvidenceContentDigest,
  validatePipelineEpisodeEvidence} = require('../dist/src/pipeline_episode_evidence');
const players = ['p1', 'p2'];
const out = path.resolve(__dirname, '../../artifacts/validation/ce08a-adversarial-recovery-2026-10-09');
fs.mkdirSync(out, {recursive: true});
const baseline = JSON.parse(fs.readFileSync(path.resolve(__dirname,
  '../../artifacts/validation/ce08a-current-source-2026-10-09/metadata.json'), 'utf8'));
const repo = path.resolve(__dirname, '../..');
const sourceHashes = {...baseline.hashes};
for (const [file, hash] of Object.entries(sourceHashes)) {
  assert.equal(createHash('sha256').update(fs.readFileSync(path.join(repo, file))).digest('hex'), hash, file);
}
sourceHashes[path.relative(repo, __filename)] = createHash('sha256').update(fs.readFileSync(__filename)).digest('hex');
const manifest = {source_hashes: sourceHashes, payloads: {}, phases: [], generated_once: true};
function note(phase) {
  const entry = {phase, timestamp: new Date().toISOString()};
  manifest.phases.push(entry); console.log(entry.timestamp, phase);
  fs.writeFileSync(path.join(out, 'recovery.json'), JSON.stringify(manifest, null, 2) + '\n');
}
function save(name, value) {
  const file = path.join(out, name); assert.equal(fs.existsSync(file), false, `refuse to replace ${file}`);
  const bytes = JSON.stringify(value);
  fs.writeFileSync(file + '.partial', bytes); fs.renameSync(file + '.partial', file);
  manifest.payloads[name] = {sha256: createHash('sha256').update(bytes).digest('hex'), bytes: Buffer.byteLength(bytes)};
  note(`persisted ${name}`);
}
function canonicalIdentity(envelope) {
  const {evidence_id, ...content} = envelope;
  assert.equal(evidence_id, `episode-evidence-${episodeEvidenceContentDigest(content)}`);
  const origin = {schema_version: envelope.origin.schema_version, run_id: envelope.run_id,
    battle_id: envelope.battle_id, ruleset: envelope.ruleset, source_ref: envelope.source_ref,
    kind: envelope.origin.kind, boundary: envelope.origin.boundary};
  assert.equal(envelope.origin.origin_id, `episode-origin-${episodeEvidenceContentDigest(origin)}`);
  for (const commit of envelope.commits) assert.equal(commit.origin_id, envelope.origin.origin_id);
}
function reseal(envelope) {const {evidence_id, ...content} = envelope; return sealPipelineEpisodeEvidence(content);}
async function main() {
  assert.equal(fs.existsSync(path.join(out, 'valid-envelope.json')), false,
    'payload already exists; do not regenerate the battle');
  note('source-chain regeneration started; no publication');
  const started = Date.now();
  const config = {battle_id: 'episode-source-turn-limit-tie', format: 'gen9randombattle',
    seed: [31,37,41,43], observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION};
  const session = await createPipelineIntegrationSession(config), initial = session.boundary;
  function first(player) {
    const request = initial.perspectives[player].observation.request;
    const action = request.legal_actions.actions.find(a => a?.choice.startsWith('switch '));
    assert.ok(action); return canonicalActionFromLegalAction(request, action.index);
  }
  const firstCommit = await session.step({p1: first('p1'), p2: first('p2')});
  const transition = firstCommit.record_bundles.p1.transition;
  const predecessor = createPipelineEpisodeEvidence({run_id: `episode-${'0'.repeat(64)}`,
    battle_id: config.battle_id, ruleset: config.format, kind: 'fresh_episode',
    boundaries: [initial, firstCommit.boundary], transitions: [{actors: players, transition: {
      schema_version: transition.schema_version, transition_id: transition.transition_id,
      parent_branch_id: transition.parent_branch_id, branch_id: transition.branch_id,
      input_state_fingerprint: transition.input_state_fingerprint, output_state_fingerprint: transition.output_state_fingerprint,
      simulator_revision: transition.simulator_revision, step_index: transition.step_index,
    }}]});
  canonicalIdentity(predecessor); save('predecessor.json', predecessor);
  const originalStep = session.step.bind(session);
  session.step = async actions => {
    const commit = await originalStep(actions);
    if (commit.boundary.step_index % 100 === 0) note(`${commit.boundary.step_index} commits; ${Date.now()-started}ms`);
    return commit;
  };
  const result = await continuePipelineEpisode(session, {limits: {max_transitions:1050,max_attempts:1050},
    policy_id: 'source-legal-switch-stall/v1', predecessor_evidence: predecessor,
    action_order: observation => {
      const actions = observation.request.legal_actions;
      const switches = actions.actions.filter(a => a?.choice.startsWith('switch ')).map(a => a.index);
      return [...switches, ...actions.available_indices.filter(i => !switches.includes(i))];
    }});
  assert.equal(result.status, 'completed'); assert.equal(result.stop.code, 'episode/v1/terminal');
  assert.equal(result.faithful_complete_episode, true);
  const valid = result.evidence_envelope;
  assert.equal(valid.closure.terminal.winner, 'tie');
  assert.equal(valid.closure.origin_coverage, 'original_initial_requests');
  assert.equal(valid.closure.complete_capture, true); assert.deepEqual(valid.closure.predecessor, predecessor);
  save('valid-envelope.json', valid);
  const outcome = structuredClone(valid); outcome.closure.terminal.winner = 'p1';
  const wrongOutcome = reseal(outcome); save('wrong-outcome.json', wrongOutcome);
  const origin = structuredClone(valid); origin.origin.kind = 'fresh_episode';
  origin.origin.origin_id = `episode-origin-${episodeEvidenceContentDigest({
    schema_version: origin.origin.schema_version, run_id: origin.run_id, battle_id: origin.battle_id,
    ruleset: origin.ruleset, source_ref: origin.source_ref, kind: origin.origin.kind, boundary: origin.origin.boundary})}`;
  for (const commit of origin.commits) commit.origin_id = origin.origin.origin_id;
  const forgedOrigin = reseal(origin); save('forged-origin.json', forgedOrigin);
  note('all payloads durable; checking canonical identities and dependent joins');
  canonicalIdentity(valid); canonicalIdentity(wrongOutcome); canonicalIdentity(forgedOrigin);
  const expected = {run_id:result.run_id,battle_id:result.battle_id,ruleset:result.ruleset,
    policy_id:result.policy_id,limits:result.limits,origin_kind:valid.origin.kind,initial_boundary:result.initial_boundary};
  validatePipelineEpisodeEvidence(valid, result.records, expected);
  // Undo each intended semantic mutation; exact equality proves no stale unrelated joins.
  const outcomeRestored = structuredClone(wrongOutcome); outcomeRestored.closure.terminal.winner = 'tie';
  assert.deepEqual(reseal(outcomeRestored), valid);
  const originRestored = structuredClone(forgedOrigin); originRestored.origin.kind = valid.origin.kind;
  originRestored.origin.origin_id = valid.origin.origin_id;
  for (const commit of originRestored.commits) commit.origin_id = valid.origin.origin_id;
  assert.deepEqual(reseal(originRestored), valid);
  for (const [name,candidate,rule] of [['wrong-outcome',wrongOutcome,/terminal/],['forged-origin',forgedOrigin,/origin|predecessor/]]) {
    const before = episodeEvidenceContentDigest(candidate), committedBefore = episodeEvidenceContentDigest(valid);
    let error; try {validatePipelineEpisodeEvidence(candidate,result.records,expected);} catch(e) {error=e;}
    assert.ok(error); assert.match(error.message,rule);
    assert.equal(episodeEvidenceContentDigest(candidate),before);
    assert.equal(episodeEvidenceContentDigest(valid),committedBefore);
    manifest[name] = {typescript_error:error.message,canonical_identity:true,unchanged_other_joins:true,immutable:true};
    note(`${name} canonical/join and TypeScript rejection checks passed`);
  }
  manifest.native_and_recovery_seconds = (Date.now()-started)/1000;
  manifest.segment_actor_rows = result.records.p1.length + result.records.p2.length;
  manifest.predecessor_actor_rows = 2;
  manifest.final_outcome = valid.closure.terminal.winner;
  manifest.baseline_sources_unchanged = Object.entries(baseline.hashes).every(([file,hash]) =>
    createHash('sha256').update(fs.readFileSync(path.join(repo,file))).digest('hex')===hash);
  assert.equal(manifest.baseline_sources_unchanged,true);
  note('recovery complete; actor-publication evidence reused, no sweep executed');
}
main().catch(error => {manifest.error=String(error.stack);note('recovery failed; do not regenerate');process.exitCode=1;});
