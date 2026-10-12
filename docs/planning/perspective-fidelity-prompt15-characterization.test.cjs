'use strict';
/* Prompt 15 characterization (test-owned, no production edit). Run: node --test docs/planning/perspective-fidelity-prompt15-characterization.test.cjs
   with PYTHON set to the neuralgpu interpreter and PYTHONPATH=trainer/src. Each test names whether it pins CURRENT behavior (a defect or limit)
   or a PROTOTYPE property (test-owned monkeypatch, never production). */
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const here = __dirname, root = path.resolve(here, '../..');
const env = { ...process.env }; delete env.PYTHONUTF8; delete env.PYTHONIOENCODING;
const node = (script, args = [], extra = {}) => {
  const r = spawnSync(process.execPath, [path.join(here, script), ...args], { cwd: root, env: { ...env, ...extra }, encoding: 'utf8', timeout: 240000 });
  assert.equal(r.status, 0, r.stderr);
  return r.stdout;
};
const py = () => process.env.PYTHON || 'python';

test('CURRENT_BEHAVIOR_DEFECT: a snapshot captured after a rejected switch restores the pre-rejection request', () => {
  const o = JSON.parse(node('perspective-fidelity-prompt15-probe-live.cjs'));
  assert.deepEqual(o.start_p1_flags, { maybeTrapped: true });
  assert.deepEqual(o.after_rejection_live_flags, { trapped: true });
  assert.deepEqual(o.restored_flags, { maybeTrapped: true });
  assert.equal(o.restored_equals_live, false);
  assert.equal(o.recaptured_fingerprint_equal, true); // restore is stable, just wrong
  assert.deepEqual(o.snapshot_keys_extra, []);
});

test('CURRENT_BEHAVIOR_DEFECT: Showdown serialization drops activeRequest and regenerates it', () => {
  const o = JSON.parse(node('perspective-fidelity-prompt15-probe-restore.cjs'));
  assert.equal(o.snapshot_has_activeRequest_key, false);
  assert.equal(o.restored_equals_live_last, false);
  assert.equal(o.restored_equals_live_prev, true); // the restored text is the PRE-rejection delivery
  assert.deepEqual(o.sim_pokemon_trapped_flags, { trapped: 'hidden', maybeTrapped: true });
});

test('PROTOTYPE: conditional sibling key restores the live request exactly and only for the mutated state', () => {
  const detect = JSON.parse(node('perspective-fidelity-prompt15-probe-live.cjs', [], { P15_MODE: 'detect' }));
  const fix = JSON.parse(node('perspective-fidelity-prompt15-probe-live.cjs', [], { P15_MODE: 'fix' }));
  assert.equal(detect.restored_equals_live, false);
  assert.equal(detect.snapshot_fingerprint, JSON.parse(node('perspective-fidelity-prompt15-probe-live.cjs')).snapshot_fingerprint); // detect mode changes no bytes
  assert.equal(fix.restored_equals_live, true);
  assert.deepEqual(fix.snapshot_keys_extra, ['__active_request_overrides']);
  assert.notEqual(fix.snapshot_fingerprint, detect.snapshot_fingerprint); // the mutated state gets a new fingerprint
  assert.equal(fix.recaptured_fingerprint_equal, true);
});

test('CURRENT_BEHAVIOR: a rejected hidden-disabled move re-emits a row with disabledSource; restore regenerates it without', () => {
  const none = node('perspective-fidelity-prompt15-probe-disabled.cjs');
  assert.match(none.replace(/\s+/g, ''), /"live_has_disabledSource":true/);
  assert.match(none.replace(/\s+/g, ''), /"restored_equals_live":false/);
});

test('PROTOTYPE: a delivery ledger tapped at the tracker gives fresh byte-exact text at every real pipeline boundary', () => {
  const out = path.join(require('node:os').tmpdir(), `p15-sidecar-${process.pid}.json`);
  node('perspective-fidelity-prompt15-probe-sidecar-run.cjs', [out, '11,12,13,14']);
  const data = JSON.parse(require('node:fs').readFileSync(out, 'utf8'));
  assert.ok(data.stats.boundaries >= 10);
  assert.equal(data.stats.roundtrip_mismatch, 0);
  assert.deepEqual(data.stats.refused, {});
  for (const row of data.rows) assert.ok(row.observation.view.terminated ? row.text === null : row.provenance === 'fresh_delivery');
  const r = spawnSync(py(), [path.join(here, 'perspective-fidelity-prompt15-probe-sidecar-validate.py'), out], { cwd: root, env: { ...env, PYTHONPATH: path.join(root, 'trainer/src') }, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  const v = JSON.parse(r.stdout);
  assert.equal(v.validated, data.rows.length); assert.equal(v.parity, data.rows.length); assert.deepEqual(v.failures, []);
});

test('CURRENT_BEHAVIOR: existing bundle validators reject any added sidecar key, nested raw_request and an unknown bundle version', () => {
  const fs = require('node:fs'), os = require('node:os');
  const dump = path.join(os.tmpdir(), `p15-bundles-${process.pid}.json`);
  const w = require('./perspective-fidelity-prompt13-witness.cjs');
  return w.captureCase(w.CASES.find((c) => c.id === 'ordinary_slots'), {}).then((c) => {
    fs.writeFileSync(dump, JSON.stringify(c));
    const r = spawnSync(py(), [path.join(here, 'perspective-fidelity-prompt15-probe-publication.py'), dump], { cwd: root, env: { ...env, PYTHONPATH: path.join(root, 'trainer/src') }, encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
    for (const row of Object.values(JSON.parse(r.stdout))) {
      assert.match(row.extra_sidecar_key, /^rejected: .*not exact/);
      assert.match(row.sidecar_with_raw_request_key_nested_in_extra, /^rejected: .*raw simulator data: raw_request/);
      assert.match(row.new_bundle_schema_version_v2, /^rejected: unsupported pipeline bundle schema/);
    }
  });
});
