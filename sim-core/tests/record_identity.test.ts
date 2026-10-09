import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { projectBeliefState, serializeBeliefState } from '../src/belief_state';
import { canonicalActionFromLegalAction } from '../src/canonical_action';

function canonical(value: any): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
const hash = (x: any) => createHash('sha256').update(canonical(x)).digest('hex');
const obsId = (o: any) => 'obs-' + hash(Object.fromEntries(Object.entries(o).filter(([k]) => !['observation_id', 'protocol_prefix'].includes(k))));
function sealBeliefs(b: any) {
  for (const key of ['input_belief', 'successor_belief']) {
    if (key === 'successor_belief') b[key].parent_belief_id = b.input_belief.belief_id;
    b[key].belief_id = 'belief-' + hash(Object.fromEntries(Object.entries(b[key]).filter(([k]) => k !== 'belief_id')));
  }
}
function python(value: any, code?: string) {
  return spawnSync(process.env.PYTHON || 'python3', code ? ['-c', code] : ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(value), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
}
function rejected(b: any, pattern = /identity|reference|version|schema|history/i) {
  const p = python(b); assert.equal(p.status, 2, p.stdout + p.stderr); assert.equal(p.stdout, ''); assert.match(p.stderr, pattern);
}
for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`${version} Python verifies current, successor and nested identities before publication`, async () => {
    const session = await createPipelineIntegrationSession({ battle_id: 'identity-é-😀', format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: version });
    try {
      const actions = Object.fromEntries((['p1', 'p2'] as const).map(p => {
        const request = session.boundary.perspectives[p].observation.request!;
        return [p, canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0])];
      })) as Parameters<typeof session.step>[0];
      const result = await session.step(actions);
      for (const actor of ['p1', 'p2'] as const) {
        const original: any = result.record_bundles[actor]; const before = JSON.stringify(original);
        const good = python(original); assert.equal(good.status, 0, good.stderr);
        assert.equal(JSON.parse(good.stdout).observation_id, original.input_observation.observation_id);
        assert.equal(python(original).stdout, good.stdout);
        for (const location of ['input_observation', 'successor_observation', 'input_belief', 'successor_belief']) {
          const b = structuredClone(original); b[location].battle_id += '-tampered'; rejected(b, /identity|battle/i);
        }
        for (const location of ['input_belief', 'successor_belief']) {
          for (const field of ['event_cursor', 'source_kind', 'snapshot_phase', 'protocol_prefix_hash', 'schema_version']) {
            const b = structuredClone(original); b[location].observation[field] = field === 'event_cursor' ? 0 : 'tampered'; sealBeliefs(b); rejected(b);
          }
          const candidate = structuredClone(original);
          candidate[location].candidates.push({ category: 'ability', subject_key: 'p2: target', value: 'Pressure', candidate_id: 'hyp-' + '0'.repeat(64), disposition: 'possible', evidence_ids: [] });
          sealBeliefs(candidate); rejected(candidate);
          const evidence = structuredClone(original);
          evidence[location].evidence.push({ perspective: actor, category: 'ability', subject_key: 'p2: target', value: 'Pressure', assertion: 'supports', provenance: { kind: 'prior_knowledge', source_id: 'test', source_version: '1', source_digest: '0'.repeat(64) }, evidence_id: 'evidence-' + '0'.repeat(64) });
          sealBeliefs(evidence); rejected(evidence);
        }
        const history = structuredClone(original);
        history.successor_belief.observation_history[0].observation_id = 'obs-' + '0'.repeat(64);
        sealBeliefs(history); rejected(history);
        if (version.endsWith('/v2')) {
          const downgrade = structuredClone(original);
          for (const which of ['input', 'successor']) {
            downgrade[which + '_observation'].schema_version = 'observable-battle-state/v1';
            for (const p of downgrade[which + '_observation'].view.opponent_team) delete p.public_boosts;
            for (const r of [downgrade[which + '_belief'].observation, ...downgrade[which + '_belief'].observation_history]) r.schema_version = 'observable-battle-state/v1';
          }
          rejected(downgrade);
          const replacements = new Map<string, string>();
          for (const which of ['input', 'successor']) { const o = downgrade[which + '_observation']; replacements.set(o.observation_id, obsId(o)); }
          const repaired = JSON.parse(JSON.stringify(downgrade), (_k, v) => typeof v === 'string' ? replacements.get(v) || v : v);
          rejected(repaired, /belief content identity mismatch/);
        } else {
          const legacy = structuredClone(original);
          for (const which of ['input', 'successor']) for (const ref of [legacy[which + '_belief'].observation, ...legacy[which + '_belief'].observation_history]) delete ref.schema_version;
          sealBeliefs(legacy);
          const frozen = JSON.stringify(legacy); const valid = python(legacy); assert.equal(valid.status, 0, valid.stderr);
          assert.equal(JSON.parse(valid.stdout).belief_id, legacy.input_belief.belief_id);
          assert.equal(JSON.stringify(legacy), frozen);
          for (const v of [null, 'observable-battle-state/v999', 'observable-battle-state/v2']) {
            const invalid = structuredClone(legacy); invalid.input_belief.observation.schema_version = v; sealBeliefs(invalid); rejected(invalid);
          }
        }
        const nested = structuredClone(original);
        const projected = projectBeliefState({ observation: original.input_observation, candidates: [{ category: 'ability', subject_key: 'p2: target', value: 'Pressure' }], evidence: [{ perspective: actor, category: 'ability', subject_key: 'p2: target', value: 'Pressure', assertion: 'supports', provenance: { kind: 'prior_knowledge', source_id: 'identity-fixture', source_version: 'v1', source_digest: 'a'.repeat(64) } }] });
        for (const k of ['input_belief', 'successor_belief']) {
          nested[k].candidates = structuredClone(projected.candidates);
          nested[k].evidence = structuredClone(projected.evidence);
        }
        sealBeliefs(nested);
        const acceptedNested = python(nested); assert.equal(acceptedNested.status, 0, acceptedNested.stderr);
        const staleNested = structuredClone(nested); staleNested.successor_belief.evidence[0].value = 'Levitate'; sealBeliefs(staleNested); rejected(staleNested);
        const wrongCandidateJoin = structuredClone(nested); wrongCandidateJoin.successor_belief.candidates[0].evidence_ids = []; sealBeliefs(wrongCandidateJoin); rejected(wrongCandidateJoin);
        assert.equal(JSON.stringify(original), before);
      }
    } finally { await session.close(); }
  });
}

test('Python identity canonicalization matches TypeScript JSON scalar and UTF-16 semantics', () => {
  const numbers = [-0, 0, 1.0, 1e-6, 1e-7, 1e20, 1e21, 1e23, 1000000000000000100, Number.MIN_VALUE, Number.MAX_VALUE, 0.1, 1.2345678901234567];
  let n = 123456789;
  for (let i = 0; i < 1000; i++) { n = (Math.imul(n, 1664525) + 1013904223) >>> 0; numbers.push((n / 0xffffffff) * 10 ** ((i % 600) - 300)); }
  const fixtures: any[] = [{ '\ue000': 1, '\u{10000}': 2, '2': 3, '10': 4 }, { text: 'é e\u0301 😀 \ud800 \udfff\n\t' }, {}, { optional: null }, ...numbers];
  const p = python(fixtures, 'import json,sys\nfrom neural.ts_identity import canonical,digest\nx=json.load(sys.stdin)\nprint(json.dumps([[canonical(v),digest(v)] for v in x],ensure_ascii=True))');
  assert.equal(p.status, 0, p.stderr); assert.deepEqual(JSON.parse(p.stdout), fixtures.map(v => [canonical(v), hash(v)]));
  assert.notEqual(hash({}), hash({ optional: null }));
});


for (const version of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
  test(`${version} two-transition historical reference fields reject malformed values at every position`, async () => {
    const session = await createPipelineIntegrationSession({ battle_id: 'history-fields', format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: version });
    try {
      let original: any;
      for (let step = 0; step < 2; step++) {
        const actions = Object.fromEntries((['p1', 'p2'] as const).map(p => {
          const r = session.boundary.perspectives[p].observation.request!;
          return [p, canonicalActionFromLegalAction(r, r.legal_actions.available_indices[0])];
        })) as Parameters<typeof session.step>[0];
        original = (await session.step(actions)).record_bundles.p1;
      }
      const frozen = JSON.stringify(original);
      assert.equal(original.successor_belief.observation_history.length, 3);
      const valid = python(original); assert.equal(valid.status, 0, valid.stderr);
      assert.equal(serializeBeliefState(original.input_belief), canonical(original.input_belief));
      const fields = ['schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase'];
      const cases: [string, (r: any, b: any) => void][] = [];
      for (const field of fields) {
        if (field !== 'schema_version' || version.endsWith('/v2')) cases.push([`missing ${field}`, r => { delete r[field]; }]);
        for (const value of [null, true, 1.5, [], {}]) cases.push([`${field} ${JSON.stringify(value)}`, r => { r[field] = value; }]);
      }
      cases.push(
        ['unknown schema', r => { r.schema_version = 'observable-battle-state/v999'; }],
        ['mixed schema', r => { r.schema_version = version.endsWith('/v2') ? 'observable-battle-state/v1' : 'observable-battle-state/v2'; }],
        ['invalid source', r => { r.source_kind = 'invalid'; }],
        ['invalid phase', r => { r.snapshot_phase = 'invalid'; }],
        ['malformed ID', r => { r.observation_id = 'obs-' + 'A'.repeat(64); }],
        ['ID trailing newline', r => { r.observation_id += '\n'; }],
        ['malformed hash', r => { r.protocol_prefix_hash = 'A'.repeat(64); }],
        ['wrong prefix hash', r => { r.protocol_prefix_hash = '0'.repeat(64); }],
        ['string cursor', r => { r.event_cursor = String(r.event_cursor); }],
        ['fraction cursor', r => { r.event_cursor = 0.5; }],
        ['unsafe cursor', r => { r.event_cursor = Number.MAX_SAFE_INTEGER + 1; }],
        ['out of bounds', (r, b) => { r.event_cursor = b.successor_observation.event_cursor + 1; }],
        ['negative cursor with matching slice', (r, b) => { r.event_cursor = -1; r.protocol_prefix_hash = hash(b.input_belief.source_protocol_prefix.slice(0, -1)); }],
        ['extra field', r => { r.extra = 1; }],
      );
      for (let index = 0; index < 3; index++) for (const [label, mutate] of cases) {
        const b = structuredClone(original);
        for (const key of ['input_belief', 'successor_belief']) {
          const history = b[key].observation_history;
          if (history[index]) {
            mutate(history[index], b);
            if (index === history.length - 1) b[key].observation = structuredClone(history[index]);
          }
        }
        sealBeliefs(b);
        assert.throws(() => serializeBeliefState(index < 2 ? b.input_belief : b.successor_belief), /./, `${index}: ${label}`);
        rejected(b, /identity|reference|version|schema|history|cursor|prefix/i);
      }
      for (const mutation of ['duplicate', 'decreasing', 'null-entry', 'empty', 'not-array', 'last-current']) {
        const b = structuredClone(original);
        for (const key of ['input_belief', 'successor_belief']) {
          const h = b[key].observation_history;
          if (mutation === 'duplicate') h[0] = structuredClone(h[1]);
          if (mutation === 'decreasing') { h[1].event_cursor = 0; h[1].protocol_prefix_hash = hash([]); }
          if (mutation === 'null-entry') h[0] = null;
          if (mutation === 'empty') b[key].observation_history = [];
          if (mutation === 'not-array') b[key].observation_history = {};
          if (mutation === 'last-current') h[h.length - 1].snapshot_phase = 'other';
        }
        sealBeliefs(b); assert.throws(() => serializeBeliefState(b.input_belief)); rejected(b);
      }
      // All supported domains are legal for an older reference whose payload is not supplied.
      for (const source of ['sim_core', 'replay', 'live']) for (const phase of ['pre_decision', 'post_resolution', 'forced_switch', 'terminal', 'other']) {
        const b = structuredClone(original);
        for (const key of ['input_belief', 'successor_belief']) Object.assign(b[key].observation_history[0], { source_kind: source, snapshot_phase: phase });
        sealBeliefs(b); serializeBeliefState(b.input_belief); const ok = python(b); assert.equal(ok.status, 0, ok.stderr);
      }
      if (version.endsWith('/v1')) {
        const b = structuredClone(original);
        for (const key of ['input_belief', 'successor_belief']) for (const r of [b[key].observation, ...b[key].observation_history]) delete r.schema_version;
        sealBeliefs(b); const before = JSON.stringify(b); const ok = python(b); assert.equal(ok.status, 0, ok.stderr);
        assert.equal(JSON.parse(ok.stdout).belief_id, b.input_belief.belief_id); assert.equal(JSON.stringify(b), before);
        b.input_belief.observation_history[0].source_kind = 'invalid'; b.successor_belief.observation_history[0].source_kind = 'invalid'; sealBeliefs(b); rejected(b);
      }
      assert.equal(JSON.stringify(original), frozen);
    } finally { await session.close(); }
  });
}
