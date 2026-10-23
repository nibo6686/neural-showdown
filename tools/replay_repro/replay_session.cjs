'use strict';
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const {PipelineIntegrationSession} = require(path.join(root, 'sim-core/dist/src/pipeline_integration'));
const {canonicalActionFromLegalAction} = require(path.join(root, 'sim-core/dist/src/canonical_action'));
const {isEngineSeed} = require(path.join(root, 'sim-core/dist/src/engine_seed'));
const {keep, expectedPublic} = require('./public_log.cjs');
const owners = ['p1', 'p2'];

/** Resolve names/IDs as emitted in input logs, but submit only a unique canonical action. */
function replayAction(request, choice) {
  if (!request) throw new Error('replay/non-mapping-choice: no current request');
  const candidates = request.legal_actions.actions.filter(Boolean).filter(action => {
    if (action.choice === choice) return true;
    const move = /^move ([a-z0-9]+)( terastallize)?$/.exec(choice);
    if (!move || /^\d+$/.test(move[1])) return false;
    const slot = request.active?.moves.find(row => row.id === move[1])?.slot;
    if (!move[2] && request.active?.moves.length === 1 && request.active.moves[0].id === move[1]
      && request.legal_actions.available_indices.length === 1 && action.choice === 'default') return true;
    return slot !== undefined && action.choice === `move ${slot}${move[2] || ''}`;
  });
  if (candidates.length !== 1) throw new Error(`replay/non-mapping-choice: ${request.player} ${choice} (${candidates.length} matches)`);
  return canonicalActionFromLegalAction(request, candidates[0].index);
}

function parseReplay(replay) {
  if (!replay || typeof replay.id !== 'string' || typeof replay.inputlog !== 'string' || typeof replay.log !== 'string') throw new Error('replay/invalid-input');
  const lines = replay.inputlog.split(/\r?\n/).filter(Boolean);
  const version = lines.filter(l => l.split(' ')[0] === '>version');
  if (version.length !== 1 || !/^>version [a-f0-9]{40}$/.test(version[0])) throw new Error('replay/invalid-version');
  const starts = lines.filter(l => l.startsWith('>start '));
  if (starts.length !== 1) throw new Error('replay/invalid-start');
  if (lines.filter(l => l.split(' ')[0] === '>player').length !== 2) throw new Error('replay/invalid-player');
  const start = JSON.parse(starts[0].slice(7));
  if (start.formatid !== 'gen9randombattle' || !isEngineSeed(start.seed)) throw new Error('replay/unsupported-creation');
  const players = {};
  for (const owner of owners) {
    const rows = lines.filter(l => l.startsWith(`>player ${owner} `));
    if (rows.length !== 1) throw new Error('replay/invalid-player');
    const player = JSON.parse(rows[0].slice(11));
    if (lines.indexOf(rows[0]) < lines.indexOf(starts[0])) throw new Error('replay/invalid-creation-order');
    if (typeof player.name !== 'string' || !player.name || !isEngineSeed(player.seed) || Object.hasOwn(player, 'team')) throw new Error('replay/unsupported-player-creation');
    players[owner] = {name: player.name, seed: player.seed};
  }
  const choices = [];
  for (const line of lines) {
    const command = line.split(' ')[0];
    if (['>version', '>start', '>player', '>chat'].includes(command)) continue;
    if (command === '>p1' || command === '>p2') {
      if (owners.some(owner => lines.indexOf(line) < lines.findIndex(l => l.startsWith(`>player ${owner} `)))) throw new Error('replay/invalid-creation-order');
      choices.push({owner: command.slice(1), choice: line.slice(4)});
    }
    else if (['>forcewin', '>forcelose', '>forcetie'].includes(command)) {
      if (!/^>(?:(?:forcewin|forcelose) p[12]|forcetie)$/.test(line)) throw new Error('replay/invalid-administrative-ending');
      if (expectedPublic(replay).ending === 'normal') throw new Error('replay/unsupported-administrative-ending');
      choices.push({ending: true});
    } else throw new Error('replay/unsupported-input-command: ' + command);
  }
  return {start, players, choices, server_commit: version[0].slice(9)};
}

/** Local paired replay consumer. Each addressed frame contains only its owner's private K. */
async function replaySession(replay, {collect = true, kdiff = false, onBoundary, maxBoundaries = 2000} = {}) {
  const {start, players, choices, server_commit} = parseReplay(replay), expected = expectedPublic(replay);
  const recipients = {p1: {}, p2: {}};
  const session = await PipelineIntegrationSession.create({battle_id: replay.id, format: start.formatid,
    seed: start.seed, player_generation: players, knowledge_recipients: recipients});
  const boundaries = [];
  let differential;
  let count = 0, cursor = 0, matched = 0;
  try {
    differential = kdiff ? require('./knowledge_diff.cjs').createKnowledgeDiff(session) : null;
    while (true) {
      const boundary = session.boundary;
      if (++count > maxBoundaries) throw new Error('replay/long-case-boundary-limit');
      const actual = session.rawPrefix.filter(keep);
      // Server replay uploads may select either native split alternative. The
      // spectator must still be one of the same record's exact emitted forms.
      const alternatives = [];
      const native = session.environment.battleStream.battle.log;
      for (let i = 0; i < native.length; i++) {
        if (native[i].startsWith('|split|')) {
          const forms = [native[++i], native[++i]];
          if (forms.some(keep)) alternatives.push(forms);
        } else if (keep(native[i])) alternatives.push([native[i]]);
      }
      while (matched < actual.length) {
        if (actual[matched] !== expected.lines[matched] && !(alternatives[matched]?.includes(actual[matched]) && alternatives[matched]?.includes(expected.lines[matched]))) throw new Error(`replay/public-log-diverged: record ${matched}: ${actual[matched]} != ${expected.lines[matched]}`);
        matched++;
      }
      const actions = {};
      const actors = owners.filter(owner => {
        const request = boundary.perspectives[owner].observation.request;
        return request && !request.wait && request.legal_actions.available_indices.length > 0;
      });
      const ending = choices[cursor]?.ending;
      if (!ending && boundary.kind !== 'terminal') {
        for (let i = 0; i < actors.length; i++) {
          const input = choices[cursor++];
          if (!input || input.ending || !actors.includes(input.owner) || actions[input.owner]) throw new Error('replay/missing-or-duplicate-owner-choice');
          actions[input.owner] = replayAction(boundary.perspectives[input.owner].observation.request, input.choice);
        }
      }
      const frames = owners.map(owner => ({owner, step_index: boundary.step_index,
        observation: boundary.perspectives[owner].observation,
        knowledge: session.readOwnerKnowledge(session.getOwnerKnowledgeHandle(recipients[owner]), recipients[owner]),
        action: actions[owner] ?? null}));
      differential?.compare(session, frames);
      if (collect) boundaries.push(frames);
      if (onBoundary) await onBoundary(frames);
      if (ending || boundary.kind === 'terminal') break;
      if (boundary.kind === 'joint_actionable') await session.step(actions);
      else if (boundary.kind === 'one_sided_revival') await session.stepRevival(Object.values(actions)[0]);
      else if (boundary.kind === 'one_sided_forced_switch') await session.stepForcedSwitch(Object.values(actions)[0]);
      else throw new Error('replay/unsupported-boundary: ' + boundary.kind);
    }
    if (choices[cursor]?.ending) cursor++;
    if (cursor !== choices.length) throw new Error('replay/unconsumed-input-choices');
    if (matched !== expected.lines.length) throw new Error(`replay/public-log-incomplete: ${matched}/${expected.lines.length}`);
    const result = {id: replay.id, server_commit, born: true, boundaries: count, matched_records: matched, ending: expected.ending,
      ...(collect ? {decisions: boundaries} : {}), ...(differential ? {kdiff: differential.result()} : {})};
    return result;
  } catch (error) {
    error.replayResult = {...(error.switch_sources ? {switch_sources: error.switch_sources} : {}), boundaries: count, matched_records: matched, ...(differential ? {kdiff: differential.result()} : {})};
    throw error;
  } finally {await session.close();}
}
module.exports = {replaySession, replayAction, parseReplay};
