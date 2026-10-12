'use strict';
/**
 * Prompt 15 TEST-OWNED prototype (never production): in-process monkeypatch of LocalBattleEnv that
 *  - detect mode: records, per serializeBattle() of a live (non-ended) battle, whether any side's live
 *    activeRequest differs from the request Showdown would regenerate on restore;
 *  - fix mode: additionally carries those (and only those) requests in a sibling key
 *    `__active_request_overrides` that resetFromSerialized strips and re-applies after Battle.fromJSON.
 * Use: node --require <this> ... with P15_MODE=detect|fix and optional P15_LOG=<file> (appended JSONL).
 */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const { LocalBattleEnv } = require(path.join(root, 'sim-core/dist/src/env_manager.js'));
const { Battle } = require(path.join(root, 'sim-core/node_modules/pokemon-showdown'));
const KEY = '__active_request_overrides';
const mode = process.env.P15_MODE || 'detect';
const log = (o) => { if (process.env.P15_LOG) fs.appendFileSync(process.env.P15_LOG, JSON.stringify(o) + '\n'); };

function diffs(serialized, battle) {
  const clone = Battle.fromJSON(structuredClone(serialized));
  const out = {};
  try {
    for (const [i, side] of battle.sides.entries()) {
      if (!side.activeRequest) continue;
      const a = JSON.stringify(side.activeRequest), b = JSON.stringify(clone.sides[i].activeRequest);
      if (a !== b) out[side.id] = { live: side.activeRequest, regenerated: clone.sides[i].activeRequest };
    }
  } finally { clone.destroy(); }
  return out;
}

const origSerialize = LocalBattleEnv.prototype.serializeBattle;
LocalBattleEnv.prototype.serializeBattle = function () {
  const serialized = origSerialize.call(this);
  const battle = this.battleStream && this.battleStream.battle;
  if (!battle || battle.ended) { log({ ev: 'serialize', ended: !!(battle && battle.ended), diff: [] }); return serialized; }
  const d = diffs(serialized, battle);
  log({ ev: 'serialize', ended: false, diff: Object.keys(d), ...(Object.keys(d).length ? { stack: new Error().stack.split(String.fromCharCode(10)).slice(2, 9).map((s) => s.trim()), differing_fields: Object.fromEntries(Object.entries(d).map(([k, v]) => [k, Object.keys(v.live).filter((f) => JSON.stringify(v.live[f]) !== JSON.stringify(v.regenerated[f]))])) } : {}) });
  if (mode === 'fix' && Object.keys(d).length) {
    return { ...serialized, [KEY]: Object.fromEntries(Object.entries(d).map(([k, v]) => [k, v.live])) };
  }
  return serialized;
};

const origReset = LocalBattleEnv.prototype.resetFromSerialized;
LocalBattleEnv.prototype.resetFromSerialized = async function (serialized, options) {
  if (serialized && serialized[KEY]) {
    const { [KEY]: overrides, ...rest } = serialized;
    const orig = Battle.fromJSON;
    Battle.fromJSON = function (s) {
      const b = orig.call(Battle, s);
      for (const side of b.sides) if (overrides[side.id]) side.activeRequest = structuredClone(overrides[side.id]);
      return b;
    };
    try { return await origReset.call(this, rest, options); } finally { Battle.fromJSON = orig; }
  }
  return origReset.call(this, serialized, options);
};
module.exports = { KEY };
