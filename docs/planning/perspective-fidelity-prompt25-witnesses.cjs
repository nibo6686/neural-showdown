const fs = require('node:fs');
const assert = require('node:assert/strict');
const { BattleStream } = require('../../sim-core/node_modules/pokemon-showdown');
const { PipelineIntegrationSession: Session } = require('../../sim-core/dist/src/pipeline_integration');
const { LocalBattleEnv: Env } = require('../../sim-core/dist/src/env_manager');
const { PlayerStateExtractor: Extractor } = require('../../sim-core/dist/src/state_extractor');
const owners = ['p1', 'p2'], producers = { p1: [], p2: [] }, receipts = { p1: [], p2: [] };
const push = BattleStream.prototype.pushMessage, consume = Extractor.prototype.consumeChunk;
const reset = Env.prototype.resetWithOptions, step = Env.prototype.stepSeededTransition;
let settled, session;
const tokens = new Map();
function diagnosticToken(value) {
  if (!tokens.has(value)) tokens.set(value, `diagnostic-token-${tokens.size + 1}`);
  return tokens.get(value);
}
function literal(row) {
  return { ...row, producer_occurrence: diagnosticToken(row.producer_occurrence), request_utf8_hex: Buffer.from(row.request_record, 'utf8').toString('hex') };
}
BattleStream.prototype.pushMessage = function(type, data) {
  if (type === 'sideupdate' && typeof data === 'string') {
    const i = data.indexOf('\n'), owner = data.slice(0, i), record = data.slice(i + 1);
    if (owners.includes(owner) && record.startsWith('|request|')) producers[owner].push(record);
  }
  return push.call(this, type, data);
};
Extractor.prototype.consumeChunk = function(chunk) {
  for (const record of chunk.split('\n')) if (record.startsWith('|request|')) receipts[this.player].push(record);
  return consume.call(this, chunk);
};
Env.prototype.resetWithOptions = async function(...args) { settled = await reset.apply(this, args); return settled; };
Env.prototype.stepSeededTransition = async function(...args) { const result = await step.apply(this, args); settled = result.step_result; return result; };
(async () => {
  session = await Session.create({ battle_id: 'prompt25-native-witness', format: 'gen9randombattle', seed: [1, 2, 3, 4] });
  const boundaries = [];
  for (let index = 0; index <= 2; index++) {
    const row = {};
    for (const owner of owners) {
      const history = session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner), binding = history.boundaries.at(-1);
      assert.equal(binding.selected.request_record, producers[owner].at(-1));
      assert.equal(binding.selected.receipt.record, receipts[owner].at(-1));
      assert.deepEqual(JSON.parse(binding.selected.request_json), settled.requests[owner].raw);
      assert.deepEqual(binding.prefix, session.boundary.perspectives[owner].observation.protocol_prefix);
      row[owner] = { ...binding, session_occurrence: diagnosticToken(binding.session_occurrence), trace: binding.trace.map(literal),
        selected: literal(binding.selected), current: { ...binding.current, session_occurrence: diagnosticToken(binding.current.session_occurrence),
          delivery_reference: diagnosticToken(binding.current.delivery_reference), source: literal(binding.current.source) },
        actual_settled_raw: settled.requests[owner].raw, independent_producer_record: producers[owner].at(-1), independent_receipt_record: receipts[owner].at(-1) };
    }
    boundaries.push(row);
    if (index < 2) await session.step();
  }
  fs.writeFileSync(__dirname + '/perspective-fidelity-prompt25-literal-witnesses.json', JSON.stringify({
    scope: 'Genuine native Random Battle, initial and two accepted transitions; independent test taps. Diagnostic token labels are not transported authority or knowledge facts.', boundaries,
  }, null, 2) + '\n', 'utf8');
  console.log('both-owner literal producer/receipt/raw/prefix comparisons passed for three real boundaries');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  BattleStream.prototype.pushMessage = push; Extractor.prototype.consumeChunk = consume;
  Env.prototype.resetWithOptions = reset; Env.prototype.stepSeededTransition = step;
  await session?.close();
});
