#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const simRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(simRoot, '..');
const trainerSource = path.join(repoRoot, 'trainer', 'src');
const expectedBase = '3ddc5fc3060e8da287425e4d08a71a2ffd77184a';
const expectedPatchHash = '968e3f9318e6b67e6585afec1c74e1f4442ef875a11fd47164eb6e71f0140018';
const format = 'gen9randombattle';
const players = ['p1', 'p2'];

const { canonicalActionFromLegalAction } = require('../dist/src/canonical_action.js');
const { projectBeliefState } = require('../dist/src/belief_state.js');
const { LocalBattleEnv } = require('../dist/src/env_manager.js');
const { runPipelineEpisode, summarizeEpisodeBoundary } = require('../dist/src/pipeline_episode.js');
const {
  classifyPipelineBoundary,
  classifyPipelineRequestState,
  createPipelineIntegrationSession,
  PipelineIntegrationError,
  projectPipelineProtocolPrefix,
  projectPipelineStepResult,
} = require('../dist/src/pipeline_integration.js');
const { toSeededSnapshotRef } = require('../dist/src/transition.js');

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const options = {};
  for (let index = 0; index < rest.length; index += 2) {
    const key = rest[index];
    if (!key?.startsWith('--') || rest[index + 1] === undefined) throw new Error(`Invalid argument near ${key || '<end>'}.`);
    options[key.slice(2)] = rest[index + 1];
  }
  return { command, options };
}

function run(executable, args, options = {}) {
  const result = spawnSync(executable, args, { cwd: repoRoot, encoding: 'utf8', ...options });
  if (result.status !== 0) throw new Error(result.stderr || `${executable} exited ${result.status}`);
  return result.stdout.trim();
}

function sha256(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function normalizedSourceBytes(file) {
  const bytes = fs.readFileSync(file);
  const text = bytes.toString('utf8');
  if (!Buffer.from(text, 'utf8').equals(bytes)) throw new Error(`Reviewed source is not valid UTF-8: ${file}`);
  return Buffer.from(text.replace(/\r\n/g, '\n'), 'utf8');
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function stableJson(value) {
  return `${JSON.stringify(stable(value), null, 2)}\n`;
}

function normalizeProtocol(records) {
  return records.map((line) => /^\|t:\|\d+$/.test(line) ? '|t:|<timestamp>' : line.replace(/\r\n?/g, '\n'));
}

function pythonExecutable() {
  return process.env.PYTHON || 'python3';
}

function pythonJson(args, input) {
  const result = spawnSync(pythonExecutable(), args, {
    cwd: repoRoot,
    env: { ...process.env, PYTHONPATH: trainerSource },
    input: input === undefined ? undefined : JSON.stringify(input),
    encoding: 'utf8',
  });
  if (result.status !== 0) throw new Error(result.stderr || `Python exited ${result.status}`);
  return JSON.parse(result.stdout);
}

function validateRecord(bundle) {
  return pythonJson(['-m', 'neural.pipeline_record'], bundle);
}

function choose(boundary, player, predicate) {
  const request = boundary.perspectives[player].observation.request;
  assert.ok(request, `Missing ${player} request.`);
  const legal = request.legal_actions.actions.find((candidate) => candidate && predicate(candidate.choice));
  assert.ok(legal, `Missing requested ${player} action.`);
  return canonicalActionFromLegalAction(request, legal.index);
}

function firstAction(boundary, player) {
  const request = boundary.perspectives[player].observation.request;
  assert.ok(request);
  return canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
}

function transitionSummary(result, pythonRecords = {}) {
  return {
    transition_id: result.transition_id,
    boundary: summarizeEpisodeBoundary(result.boundary),
    records: Object.fromEntries(Object.entries(result.record_bundles).map(([player, bundle]) => [player, {
      schema_version: bundle.schema_version,
      action: bundle.action,
      input_observation_id: bundle.input_observation.observation_id,
      input_belief_id: bundle.input_belief.belief_id,
      successor_observation_id: bundle.successor_observation.observation_id,
      successor_belief_id: bundle.successor_belief.belief_id,
      record_id: pythonRecords[player]?.record_id,
    }])),
  };
}

async function jointTransitionScenario() {
  const input = { battle_id: 'cross-platform-joint-v1', format, seed: [101, 202, 303, 404] };
  const session = await createPipelineIntegrationSession(input);
  try {
    const initial = summarizeEpisodeBoundary(session.boundary);
    const actions = Object.fromEntries(players.map((player) => [player, firstAction(session.boundary, player)]));
    const result = await session.step(actions);
    const records = Object.fromEntries(players.map((player) => [player, validateRecord(result.record_bundles[player])]));
    return { input, initial, actions, output: transitionSummary(result, records), expected: { boundary_kind: 'joint_actionable' } };
  } finally {
    await session.close();
  }
}

async function forcedSwitchScenario() {
  const input = { battle_id: 'cross-platform-forced-ko-v1', format, seed: [101, 202, 303, 404], selection: 'ascending-request-indices/v1' };
  const session = await createPipelineIntegrationSession(input);
  try {
    const setupTransitionIds = [];
    while (session.boundary.kind === 'joint_actionable' && setupTransitionIds.length < 20) {
      setupTransitionIds.push((await session.step()).transition_id);
    }
    assert.equal(session.boundary.kind, 'one_sided_forced_switch');
    const actor = players.find((player) => session.boundary.perspectives[player].observation.request?.force_switch === true);
    assert.ok(actor);
    const waiting = actor === 'p1' ? 'p2' : 'p1';
    const before = summarizeEpisodeBoundary(session.boundary);
    const action = firstAction(session.boundary, actor);
    const result = await session.stepForcedSwitch(action);
    const record = validateRecord(result.record_bundles[actor]);
    return {
      input,
      setup_transition_ids: setupTransitionIds,
      actor,
      waiting,
      before,
      action,
      output: transitionSummary(result, { [actor]: record }),
      expected: { before_kind: 'one_sided_forced_switch', after_kind: 'joint_actionable', actor_record_only: true },
    };
  } finally {
    await session.close();
  }
}

async function naturalRejectionScenario() {
  const input = { battle_id: 'cross-platform-natural-reject-v1', format, seed: [46, 101, 202, 303] };
  const session = await createPipelineIntegrationSession(input);
  try {
    const setupActions = {
      p1: choose(session.boundary, 'p1', (choice) => choice === 'switch 3'),
      p2: choose(session.boundary, 'p2', (choice) => choice === 'switch 6'),
    };
    const setup = await session.step(setupActions);
    const committed = summarizeEpisodeBoundary(session.boundary);
    const attemptedActions = {
      p1: choose(session.boundary, 'p1', (choice) => choice.startsWith('move ')),
      p2: choose(session.boundary, 'p2', (choice) => choice === 'switch 2'),
    };
    let rejectionCode = null;
    try {
      await session.step(attemptedActions);
    } catch (error) {
      if (!(error instanceof PipelineIntegrationError)) throw error;
      rejectionCode = error.code;
    }
    assert.equal(rejectionCode, 'pipeline/v1/rejected-action');
    const afterRejection = summarizeEpisodeBoundary(session.boundary);
    assert.deepEqual(afterRejection, committed);
    const recoveryActions = {
      p1: choose(session.boundary, 'p1', (choice) => choice.startsWith('move ')),
      p2: choose(session.boundary, 'p2', (choice) => choice.startsWith('move ')),
    };
    const recovery = await session.step(recoveryActions);
    const records = Object.fromEntries(players.map((player) => [player, validateRecord(recovery.record_bundles[player])]));
    return {
      input,
      setup_actions: setupActions,
      setup_transition_id: setup.transition_id,
      committed,
      attempted_actions: attemptedActions,
      rejection: { code: rejectionCode, rollback_identity_equal: true },
      recovery_actions: recoveryActions,
      recovery: transitionSummary(recovery, records),
      expected: { rejection_code: 'pipeline/v1/rejected-action', recovery_boundary_kind: 'joint_actionable' },
    };
  } finally {
    await session.close();
  }
}

async function terminalRestorationScenario() {
  const input = {
    battle_id: 'cross-platform-terminal-v1', format, seed: [101, 202, 303, 404],
    controllers: { p1: { controller: 'random', random_seed: 0x51a7 }, p2: { controller: 'random', random_seed: 0xc0de } },
  };
  const env = new LocalBattleEnv(input.battle_id, format, input.seed, input.controllers);
  try {
    const result = await env.resetWithOptions({ view_players: players, include_log_delta: true, include_possible_roles: false, include_wait_requests: true });
    assert.equal(result.terminated, true);
    const rawPrefix = projectPipelineProtocolPrefix(result.log_delta);
    const prefix = normalizeProtocol(rawPrefix);
    const snapshot = env.captureSeededSnapshot(null);
    const snapshotRef = toSeededSnapshotRef(snapshot, input.battle_id);
    const observations = projectPipelineStepResult(result, input.battle_id, rawPrefix);
    assert.equal(classifyPipelineBoundary(observations), 'terminal');
    const identities = Object.fromEntries(players.map((player) => {
      const belief = projectBeliefState({ observation: observations[player], simulator_snapshot: snapshotRef });
      return [player, {
        observation_id: observations[player].observation_id,
        belief_id: belief.belief_id,
        protocol_prefix_hash: observations[player].protocol_prefix_hash,
        request_state: classifyPipelineRequestState(observations[player]),
      }];
    }));
    const restored = new LocalBattleEnv('cross-platform-terminal-restore-v1', format, input.seed);
    try {
      const replay = await restored.resetFromSerialized(snapshot.simulator_state, { include_wait_requests: true });
      const restoredSnapshot = restored.captureSeededSnapshot(null);
      assert.equal(restoredSnapshot.state_fingerprint, snapshot.state_fingerprint);
      assert.equal(restoredSnapshot.branch_id, snapshot.branch_id);
      return {
        input,
        protocol_prefix: prefix,
        output: {
          winner: result.winner,
          terminated: result.terminated,
          requests: result.requests,
          snapshot_ref: snapshotRef,
          identities,
          restored: {
            winner: replay.winner,
            terminated: replay.terminated,
            requests: replay.requests,
            state_fingerprint: restoredSnapshot.state_fingerprint,
            branch_id: restoredSnapshot.branch_id,
          },
        },
        expected: { boundary_kind: 'terminal', restored_equal: true },
      };
    } finally {
      await restored.close();
    }
  } finally {
    await env.close();
  }
}

async function unicodeRecordScenario() {
  const input = { battle_id: 'cross-platform-unicode-v1', format, seed: [101, 202, 303, 404], perspective: 'p1' };
  const session = await createPipelineIntegrationSession(input);
  try {
    const result = await session.step();
    const bundle = result.record_bundles.p1;
    const record = validateRecord(bundle);
    const unicodeLines = bundle.input_observation.protocol_prefix.filter((line) => /[^\x00-\x7f]/.test(line));
    assert.ok(unicodeLines.some((line) => line.includes('Pokémon')));
    return {
      input,
      unicode_lines: unicodeLines,
      action: bundle.action,
      output: {
        protocol_prefix_hash: bundle.input_observation.protocol_prefix_hash,
        observation_id: bundle.input_observation.observation_id,
        belief_id: bundle.input_belief.belief_id,
        transition_id: bundle.transition.transition_id,
        record_id: record.record_id,
        data_prefix_hash: record.observation_prefix_hash,
      },
      expected: { utf8_text: 'Pokémon', python_validation: 'accepted' },
    };
  } finally {
    await session.close();
  }
}

async function boundedEpisodeScenario() {
  const input = {
    battle_id: 'episode-regression', format, seed: [101, 202, 303, 404],
    policy_id: 'ascending-request-indices/v1', limits: { max_transitions: 256, max_attempts: 512, max_rejections_per_boundary: 3 },
  };
  const result = await runPipelineEpisode({ battle_id: input.battle_id, format, seed: input.seed });
  assert.equal(result.status, 'completed');
  const recordIdentities = Object.fromEntries(players.map((player) => [player, {
    bundle_count: result.records[player].length,
    forced_switch_count: result.records[player].filter((bundle) => bundle.schema_version === 'pipeline-forced-switch-record/v1').length,
    action_ids: result.records[player].map((bundle) => bundle.action.action_id),
    input_observation_ids: result.records[player].map((bundle) => bundle.input_observation.observation_id),
    successor_observation_ids: result.records[player].map((bundle) => bundle.successor_observation.observation_id),
    last_record_id: validateRecord(result.records[player].at(-1)).record_id,
  }]));
  return {
    input,
    output: {
      schema_version: result.schema_version,
      run_id: result.run_id,
      status: result.status,
      stop: result.stop,
      counts: result.counts,
      faithful_complete_episode: result.faithful_complete_episode,
      initial_boundary: result.initial_boundary,
      final_boundary: result.final_boundary,
      transition_ids: result.transition_ids,
      records: recordIdentities,
    },
    expected: { status: 'completed', stop_code: 'episode/v1/terminal', committed_transitions: 55, faithful_complete_episode: false },
  };
}

async function environmentEvidence() {
  const python = pythonJson(['-c', [
    'import json, os, platform, sys',
    'print(json.dumps({"executable": sys.executable, "version": platform.python_version(), "prefix": sys.prefix, "conda_prefix": os.environ.get("CONDA_PREFIX")}))',
  ].join(';')]);
  let npmVersion = null;
  try {
    npmVersion = process.platform === 'win32'
      ? run('cmd.exe', ['/d', '/c', 'npm.cmd --version'])
      : run(process.env.NPM || 'npm', ['--version']);
  } catch {
    npmVersion = process.env.npm_config_user_agent || null;
  }
  return {
    platform: process.platform,
    architecture: process.arch,
    os_release: os.release(),
    node_version: process.version,
    npm_version: npmVersion,
    python_command_from_node: pythonExecutable(),
    python,
  };
}

async function generate(options) {
  if (!options.output || !options.patch) throw new Error('generate requires --output and --patch.');
  const patchPath = path.resolve(options.patch);
  const patchHash = sha256(fs.readFileSync(patchPath));
  assert.equal(patchHash, expectedPatchHash, 'Review patch hash mismatch.');
  const head = run('git', ['rev-parse', 'HEAD']);
  assert.equal(head, expectedBase, 'Base commit mismatch.');
  run(process.execPath, [path.join(simRoot, 'scripts', 'check-simulator-coverage.cjs')]);
  const manifest = JSON.parse(fs.readFileSync(path.join(simRoot, 'simulator_coverage', 'pokemon-showdown-0.11.10-gen9randombattle.json'), 'utf8'));
  const localSourceHashes = Object.fromEntries([...manifest.local_coverage_sources.files].sort().map((name) => [
    name,
    sha256(normalizedSourceBytes(path.join(simRoot, name))),
  ]));
  const scenarios = {
    joint_transition: await jointTransitionScenario(),
    one_sided_forced_switch: await forcedSwitchScenario(),
    natural_rejection_recovery: await naturalRejectionScenario(),
    terminal_restoration: await terminalRestorationScenario(),
    unicode_record: await unicodeRecordScenario(),
    bounded_episode: await boundedEpisodeScenario(),
  };
  const bundle = {
    schema_version: 'simulator-record-comparison/v1',
    source: {
      base_commit: head,
      review_patch_sha256: patchHash,
      local_coverage_sha256: manifest.local_coverage_sources.sha256,
      local_coverage_file_count: manifest.local_coverage_sources.files.length,
      local_coverage_files: localSourceHashes,
      pokemon_showdown_version: manifest.simulator.version,
    },
    environment: await environmentEvidence(),
    machine_specific_fields: [
      '/environment/platform', '/environment/architecture', '/environment/os_release',
      '/environment/node_version', '/environment/npm_version', '/environment/python_command_from_node',
      '/environment/python/executable', '/environment/python/version', '/environment/python/prefix', '/environment/python/conda_prefix',
    ],
    normalization: {
      protocol_timestamps: 'Records matching ^\\|t:\\|\\d+$ become |t:|<timestamp>.',
      line_endings: 'Protocol records normalize CRLF and bare CR to LF; reviewed source hashing normalizes CRLF pairs only.',
      omitted_fields: [],
    },
    faithful_complete_episode: false,
    scenarios,
  };
  const outputPath = path.resolve(options.output);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, stableJson(bundle), 'utf8');
  process.stdout.write(`${JSON.stringify({ output: outputPath, scenarios: Object.keys(scenarios), sha256: sha256(fs.readFileSync(outputPath)) })}\n`);
}

function differences(reference, candidate, pointer = '') {
  if (Object.is(reference, candidate)) return [];
  if (Array.isArray(reference) && Array.isArray(candidate)) {
    const found = [];
    const length = Math.max(reference.length, candidate.length);
    for (let index = 0; index < length; index += 1) found.push(...differences(reference[index], candidate[index], `${pointer}/${index}`));
    return found;
  }
  if (reference && candidate && typeof reference === 'object' && typeof candidate === 'object' && !Array.isArray(reference) && !Array.isArray(candidate)) {
    const found = [];
    for (const key of [...new Set([...Object.keys(reference), ...Object.keys(candidate)])].sort()) {
      const escaped = key.replace(/~/g, '~0').replace(/\//g, '~1');
      found.push(...differences(reference[key], candidate[key], `${pointer}/${escaped}`));
    }
    return found;
  }
  return [{ path: pointer || '/', reference, candidate }];
}

function compare(options) {
  if (!options.reference || !options.candidate) throw new Error('compare requires --reference and --candidate.');
  const reference = JSON.parse(fs.readFileSync(path.resolve(options.reference), 'utf8'));
  const candidate = JSON.parse(fs.readFileSync(path.resolve(options.candidate), 'utf8'));
  const all = differences(reference, candidate);
  const machineFields = new Set(reference.machine_specific_fields || []);
  const machineSpecific = all.filter((difference) => [...machineFields].some((field) => difference.path === field || difference.path.startsWith(`${field}/`)));
  const actionable = all.filter((difference) => !machineSpecific.includes(difference));
  const report = {
    schema_version: 'simulator-record-comparison-report/v1',
    equal_portable_results: actionable.length === 0,
    actionable_differences: actionable,
    machine_specific_differences: machineSpecific,
  };
  process.stdout.write(stableJson(report));
  if (actionable.length) process.exitCode = 1;
}

async function main() {
  const { command, options } = parseArgs(process.argv.slice(2));
  if (command === 'generate') return generate(options);
  if (command === 'compare') return compare(options);
  throw new Error('Usage: simulator-record-comparison.cjs generate --patch PATH --output PATH | compare --reference PATH --candidate PATH');
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
