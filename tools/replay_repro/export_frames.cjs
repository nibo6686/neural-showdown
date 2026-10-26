'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const root = path.resolve(__dirname,'../..');
const {canonicalActionFromLegalAction} = require(path.join(root,'sim-core/dist/src/canonical_action'));
const {checkNativeOwnerMovesProjection} = require(path.join(root,'sim-core/dist/src/perspective_knowledge'));

/** Only addressed observations and recipient-bound knowledge enter this wire. */
function decisionFrame({owner,step_index,observation,knowledge,action=null}) {
  if(observation.schema_version !== 'observable-battle-state/v2') throw new Error('decision-frame/v2-observation-required');
  checkNativeOwnerMovesProjection(knowledge.projection);
  if (observation.perspective !== owner || knowledge.projection.owner !== owner || knowledge.projection.boundary !== step_index
      || knowledge.binding.observation_id !== observation.observation_id || knowledge.binding.prefix_cursor !== observation.event_cursor)
    throw new Error('decision-frame/address-binding');
  const request = observation.request;
  const legal_actions = request ? request.legal_actions.available_indices.map(i => canonicalActionFromLegalAction(request,i)) : [];
  if (action !== null && !legal_actions.some(legal => isDeepStrictEqual(legal,action))) throw new Error('decision-frame/noncanonical-action');
  return structuredClone({schema_version:'decision-frame/v1',battle_id:observation.battle_id,step_index,owner,
    observation,knowledge,legal_actions,...(action === null ? {} : {action})});
}

/** Capture a genuinely born self-play session at its current decision cursor. */
function sessionFrames(session,recipients,actions={}) {
  return ['p1','p2'].map(owner => decisionFrame({owner,step_index:session.boundary.step_index,
    observation:session.boundary.perspectives[owner].observation,
    knowledge:session.readOwnerKnowledge(session.getOwnerKnowledgeHandle(recipients[owner]),recipients[owner]),
    action:actions[owner] ?? null}));
}

async function exportReplay(replay,write) {
  return require('./replay_session.cjs').replaySession(replay,{collect:false,ownerMoves:true,observationSchemaVersion:'observable-battle-state/v2',
    onBoundary:async frames => {for(const frame of frames) await write(decisionFrame(frame));}});
}

// Usage: node tools/replay_repro/export_frames.cjs replay.json [...] > frames.jsonl
if(require.main===module) (async()=>{
  if(process.argv.length<3) throw new Error('Replay JSON paths required');
  for(const file of process.argv.slice(2)) await exportReplay(JSON.parse(fs.readFileSync(file,'utf8')),
    frame => new Promise((resolve,reject)=>process.stdout.write(JSON.stringify(frame)+'\n',error=>error?reject(error):resolve())));
})().catch(error=>{console.error(error.message);process.exitCode=1;});
module.exports={decisionFrame,sessionFrames,exportReplay};
