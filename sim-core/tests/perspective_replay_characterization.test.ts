import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { PlayerStateExtractor } from '../src/state_extractor';
import { projectObservableBattleState, validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';
import type { BattleView, PlayerID } from '../src/types';

const root = path.resolve(__dirname, '../../..');
const fixtures = path.join(root, 'trainer/tests/fixtures/perspective-replay');
const ledger = JSON.parse(fs.readFileSync(path.join(fixtures, 'expected-ledger.json'), 'utf8'));
const requirements = process.env.PERSPECTIVE_REPLAY_REQUIREMENTS === '1';
const reportPath = process.env.PERSPECTIVE_REPLAY_REPORT;
const rows: any[] = [];
const originalRows: any[] = [];
const integrations: any[] = [];

function records(file: string): string[] {
  const bytes = fs.readFileSync(path.join(fixtures, file));
  const block = bytes.toString('utf8').match(/<script[^>]*class="battle-log-data"[^>]*>([\s\S]*?)<\/script>/)![1];
  return block.split(/\r?\n/).map(line => line.trim()).filter(line => line.startsWith('|'))
    .map(line => line.replace(/&rarr;/g, '→').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'"));
}

function actual(view: BattleView, entry: any): unknown {
  const [family, value] = entry.property.split(':');
  if (family === 'winner') return view.winner;
  if (family === 'player') return view.names[value as PlayerID];
  if (family === 'weather') return view.field.weather;
  if (family === 'hazard') return view.field.side_conditions[entry.subject === entry.owner ? 'self' : 'opponent'][value] || 0;
  const team = entry.subject.startsWith(entry.owner) ? view.self_team : view.opponent_team;
  const pokemon = team.find(p => p.ident === entry.subject);
  if (!pokemon) return { missing_subject: entry.subject };
  if (family === 'revealed_move') return pokemon.revealed_moves.some(m => m.toLowerCase().replace(/[^a-z0-9]/g, '') === value);
  if (family === 'volatile') return pokemon.volatiles.includes(value);
  if (family === 'boost') return pokemon.boosts[value] || 0;
  if (family === 'prepared') return null; // No prepared-move field in the existing BattleView contract.
  if (family === 'item_identity') return pokemon.item;
  return (pokemon as any)[family];
}

function category(entry: any): string {
  if (entry.property.startsWith('revealed_move:')) return 'identity/retention error';
  if (entry.property.startsWith('hp_')) return 'load/HP transport failure';
  return 'unsupported/lost structured family';
}

function equivalent(entry: any, observed: unknown): boolean {
  // Display names and the extractor's wire IDs denote the same public fact.
  if (['ability', 'item_identity', 'last_item', 'weather'].includes(entry.property) && typeof observed === 'string' && typeof entry.expected === 'string') {
    const id = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
    return id(observed) === id(entry.expected);
  }
  return JSON.stringify(observed) === JSON.stringify(entry.expected);
}

// Test-only diagnostic routing. Original inputs and every exclusion remain in the report.
// Slash decoding is justified by the HTML's independently rendered numeric HP, not a loader repair.
function runDiagnostic(raw: string[], owner: PlayerID, format: string, cursor: number) {
  const extractor = new PlayerStateExtractor('prompt17-diagnostic-é-Ω', format, owner);
  const prefix: string[] = [];
  const excluded: any[] = [];
  const snapshots: BattleView[] = [];
  for (let index = 0; index < cursor; index++) {
    const record = raw[index].replace(/\\\//g, '/');
    try { validateRawProtocolRecord(record); }
    catch (error) { excluded.push({ index, original: raw[index], decoded: record, stage: 'strict-record', error: String(error) }); snapshots.push(extractor.getView()); continue; }
    try { extractor.consumeChunk(record); prefix.push(record); }
    catch (error) { excluded.push({ index, original: raw[index], decoded: record, stage: 'extractor', error: String(error) }); }
    snapshots.push(extractor.getView());
  }
  return { extractor, prefix, excluded, snapshots };
}

function pythonCheck(observation: unknown) {
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONPATH: path.join(root, 'trainer/src') };
  delete env.PYTHONUTF8; delete env.PYTHONIOENCODING;
  const code = 'import sys,json,os\nfrom neural.pipeline_json_wire import load_json\nfrom neural.ts_identity import verify_observation\nfrom neural.pipeline_record import _prefix\nfrom neural.typed_state import validate_public_typed_state\nassert "PYTHONUTF8" not in os.environ and "PYTHONIOENCODING" not in os.environ\no=load_json(sys.stdin)\nassert "é-Ω" in o["battle_id"]\nverify_observation(o,"diagnostic")\n_prefix(o,"diagnostic")\nvalidate_public_typed_state(o,"diagnostic")\nprint(json.dumps({"ok":True,"owner":o["perspective"],"cursor":o["event_cursor"]}))';
  const child = spawnSync(process.env.PYTHON || 'D:\\Anaconda\\envs\\neuralgpu\\python.exe', ['-c', code], {
    input: Buffer.from(JSON.stringify(observation), 'utf8'), encoding: 'utf8', env, timeout: 30000,
  });
  assert.equal(child.error, undefined);
  return { exit_code: child.status, stdout: child.stdout, stderr: child.stderr };
}

test('supplied replay complete inputs, manual boundaries and explicitly reduced diagnostics', () => {
  for (const fixture of ledger.fixtures) {
    const raw = records(fixture.filename);
    assert.equal(raw.length, fixture.record_count);
    assert.equal(createHash('sha256').update(fs.readFileSync(path.join(fixtures, fixture.filename))).digest('hex'), fixture.sha256);
    assert.equal(raw[8], '|rated|');
    assert.equal(raw[fixture.winner_index], '|win|hasklne');
    for (const owner of ['p1', 'p2'] as PlayerID[]) {
      const untouched = new PlayerStateExtractor('prompt17-original', fixture.format, owner);
      let firstFailure: any = null;
      const originalFailures: any[] = [];
      const originalSnapshots: BattleView[] = [];
      for (let index = 0; index < raw.length; index++) {
        try { untouched.consumeChunk(raw[index]); }
        catch (error) {
          const failure = { index, record: raw[index], error: String(error) };
          firstFailure ??= failure; originalFailures.push(failure);
        }
        originalSnapshots.push(untouched.getView());
      }
      const grammar = raw.flatMap((record, index) => {
        try { validateRawProtocolRecord(record); return []; }
        catch (error) { return [{ index, record, error: String(error) }]; }
      });
      integrations.push({ fixture: fixture.key, owner, scope: fixture.scope, routing: 'complete original records; continued after exceptions for diagnostic trace, state NOT trusted', first_extractor_failure: firstFailure, extractor_failures: originalFailures, strict_failures: grammar });
      assert.ok(firstFailure, 'preserve complete-input requirement red');
      assert.ok(grammar.some(row => row.index === 8));
      for (const header of ['|j|x', '|join|x', '|rated|']) {
        const probe = new PlayerStateExtractor('header', fixture.format, owner);
        let extractorError: string | null = null;
        try { probe.consumeChunk(header); } catch (error) { extractorError = String(error); }
        assert.throws(() => validateRawProtocolRecord(header));
        integrations.push({ fixture: fixture.key, owner, header, extractor_error: extractorError, strict: 'rejects' });
      }
      const diagnostic = runDiagnostic(raw, owner, fixture.format, raw.length);
      integrations.push({ fixture: fixture.key, owner, routing: 'reduced slash-decoded diagnostic; NOT successful original ingestion', exclusions: diagnostic.excluded });
      for (const entry of fixture.entries.filter((e: any) => e.owner === owner)) {
        assert.equal(raw[entry.index], entry.evidence);
        assert.equal(entry.cursor, entry.index + 1);
        originalRows.push({ fixture: fixture.key, ...entry, routing: 'unmodified records; partial state after explicit exceptions, NOT trusted', actual: actual(originalSnapshots[entry.index], entry) });
        const observed = actual(diagnostic.snapshots[entry.index], entry);
        const matched = equivalent(entry, observed);
        rows.push({ fixture: fixture.key, ...entry, routing: 'reduced slash-decoded diagnostic', actual: observed, matches_requirement: matched, classification: matched ? 'positive' : category(entry) });
        const family = entry.property.split(':')[0];
        if (['active', 'hp_text', 'hazard', 'boost', 'types', 'terastallized', 'winner', 'player', 'item_state', 'last_item'].includes(family)
          || (family === 'ability' && [null, 'Pressure', 'Vessel of Ruin'].includes(entry.expected))
          || (family === 'item_identity' && [null, 'Air Balloon'].includes(entry.expected))
          || (family === 'revealed_move' && !((fixture.key === 'random' && [106, 243].includes(entry.index)) || (fixture.key === 'ou' && entry.index === 119)))) {
          assert.equal(matched, true, `Positive control regressed: ${fixture.key}/${owner}/${entry.index}/${entry.property}`);
        }
        if (entry.property === 'hp_text') {
          const hpEntry = { ...entry, property: 'hp_ratio' };
          const ratio = actual(diagnostic.snapshots[entry.index], hpEntry);
          const [numerator, denominator] = entry.expected.split('/').map(Number);
          assert.equal(ratio, numerator / denominator);
          integrations.push({ fixture: fixture.key, owner, original_cursor: entry.cursor, probe: 'numeric HP transport with independent source precision annotation', value: ratio, source_precision: entry.precision, structured_precision_metadata: 'unavailable in BattleView; not verified', exact_private_integer_hp: 'unverified; no addressed request exists' });
        }
      }
      // Both-owner suffix noninterference: identical causal prefixes, independently replayed.
      const cursor = fixture.key === 'random' ? 54 : 46;
      const changed = raw.slice();
      changed[fixture.winner_index] = '|win|future-suffix-change';
      const futureMove = changed.findIndex((record, index) => index >= cursor && record.startsWith('|move|'));
      changed[futureMove] = changed[futureMove].replace(/(\|move\|[^|]+\|)[^|]+/, '$1Splash');
      assert.deepEqual(runDiagnostic(raw, owner, fixture.format, cursor).extractor.getView(), runDiagnostic(changed, owner, fixture.format, cursor).extractor.getView());
      const fullChanged = runDiagnostic(changed, owner, fixture.format, changed.length);
      assert.deepEqual(diagnostic.snapshots[cursor - 1], fullChanged.snapshots[cursor - 1]);
      integrations.push({ fixture: fixture.key, owner, cursor, changed_indices: [futureMove, fixture.winner_index], probe: 'prefix-only extractor and retained snapshots remain causal; API accepts no full-source backfill input', result: 'positive', limitation: 'not a replay knowledge consumer/backfill proof' });
      // Probe real extractor state at several original cursors, no invented requests/envelopes.
      for (const cursor of [fixture.key === 'random' ? 20 : 42, fixture.key === 'random' ? 78 : 52, fixture.winner_index + 1]) {
        const state = runDiagnostic(raw, owner, fixture.format, cursor);
        const view = state.extractor.getView();
        try {
          validateObservableProtocolPrefix(state.prefix, owner, view, null);
          const observation = projectObservableBattleState({ schema_version: 'observable-battle-state/v2', source_kind: 'replay', battle_id: `prompt17-é-Ω-${fixture.key}`, perspective: owner,
            snapshot_phase: 'test-only-replay-characterization', protocol_prefix: state.prefix, view, request: null });
          const validation = pythonCheck(observation);
          assert.equal(validation.exit_code, 0, validation.stderr);
          let nextIndex = 0;
          const serializedOriginalIndices = observation.protocol_prefix.map(record => {
            while (nextIndex < cursor && (state.excluded.some(e => e.index === nextIndex) || raw[nextIndex].replace(/\\\//g, '/') !== record)) nextIndex++;
            assert.ok(nextIndex < cursor, 'Serialized prefix record must bind to an original source record in order');
            return nextIndex++;
          });
          integrations.push({ fixture: fixture.key, owner, original_cursor: cursor, pre_sanitization_cursor: state.prefix.length, serialized_cursor: observation.event_cursor, serialized_prefix: observation.protocol_prefix, serialized_original_indices: serializedOriginalIndices, observation_id: observation.observation_id, protocol_prefix_hash: observation.protocol_prefix_hash, wire_sha256: createHash('sha256').update(Buffer.from(JSON.stringify(observation), 'utf8')).digest('hex'), original_retained_indices: raw.slice(0, cursor).flatMap((_, i) => state.excluded.some(e => e.index === i) ? [] : [i]), routing: 'test-only TS JSON bytes -> Python load_json/identity/_prefix/typed-state', ...validation });
        } catch (error) {
          integrations.push({ fixture: fixture.key, owner, original_cursor: cursor, stage: 'prefix/projector', error: String(error), classification: 'unsupported/contradictory diagnostic state' });
        }
      }
    }
  }
  integrations.push({ stage: 'replay envelope -> perspective knowledge semantics', result: 'missing integration', assurance: 'source authority/original attribution/completeness/capture UNVERIFIED' });
  if (reportPath) fs.writeFileSync(reportPath, JSON.stringify({ readiness: false, mode: requirements ? 'semantic requirements' : 'characterization', rows, original_rows: originalRows, integrations }, null, 2) + '\n');
  assert.equal(integrations.filter(row => row.exit_code === 0).length, 10, 'All ten viable diagnostic TS-to-Python routes must validate; OU terminal blockers remain separate.');
  const positives = rows.filter(row => row.matches_requirement);
  const gaps = rows.filter(row => !row.matches_requirement);
  assert.ok(positives.length > 0);
  assert.ok(gaps.some(row => row.property === 'revealed_move:uturn'));
  assert.ok(gaps.some(row => row.property === 'revealed_move:icebeam'));
  assert.ok(gaps.some(row => row.property === 'prepared:chillyreception'));
  if (requirements) assert.deepEqual(gaps, [], 'Source-backed requirements remain red; see preserved per-record matrix.');
});

test('synthetic duplicate identity, Illusion and Transform must not authorize blind move inheritance', () => {
  for (const owner of ['p1', 'p2'] as PlayerID[]) {
    const extractor = new PlayerStateExtractor('synthetic', 'gen9randombattle', owner);
    const source = ['|switch|p1a: First|Pikachu|100/100', '|move|p1a: First|Thunderbolt|p2a: Target', '|switch|p1a: Second|Pikachu|100/100',
      '|switch|p2a: Target|Gengar|100/100', '|switch|p1a: Mask|Pikachu|100/100', '|move|p1a: Mask|Night Daze|p2a: Target', '|replace|p1a: Fox|Zoroark|100/100',
      '|switch|p1a: Copy|Ditto|100/100', '|-transform|p1a: Copy|p2a: Target', '|move|p1a: Copy|Shadow Ball|p2a: Target'];
    source.forEach(record => extractor.consumeChunk(record));
    const view = extractor.getView();
    const team = owner === 'p1' ? view.self_team : view.opponent_team;
    assert.equal(team.find(p => p.name === 'Second')!.revealed_moves.length, 0);
    assert.equal(team.find(p => p.name === 'Copy')!.transformed, true);
    assert.equal(team.find(p => p.name === 'Fox')!.illusion_revealed, true);
    assert.ok(team.find(p => p.name === 'Fox')!.revealed_moves.length > 0);
  }
});

test('bounded event-local slices reproduce the same source-backed gaps', () => {
  const probes: any[] = [];
  for (const slice of ledger.reproduction_slices) {
    const fixture = ledger.fixtures.find((f: any) => f.key === slice.fixture);
    const raw = records(fixture.filename);
    const local = slice.indices.map((index: number) => raw[index]);
    for (const owner of ['p1', 'p2'] as PlayerID[]) {
      const state = runDiagnostic(local, owner, fixture.format, local.length);
      const entries = fixture.entries.filter((e: any) => e.owner === owner && e.index === slice.indices.at(-1));
      const boundaries = entries.map((entry: any) => ({ ...entry, actual: actual(state.extractor.getView(), entry), matches_requirement: equivalent(entry, actual(state.extractor.getView(), entry)) }));
      probes.push({ name: slice.name, fixture: slice.fixture, owner, original_indices: slice.indices, original_records: local, decoded_records: local.map((s: string) => s.replace(/\\\//g, '/')), exclusions: state.excluded, boundaries, routing: 'isolated reduced event-local probe; NOT original ingestion' });
      if (slice.name === 'rated') assert.equal(state.excluded.length, 1);
      else assert.ok(boundaries.some((b: any) => !b.matches_requirement), `Expected diagnostic gap absent: ${slice.name}/${owner}`);
    }
  }
  if (reportPath) {
    const saved = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    saved.minimal_probes = probes;
    fs.writeFileSync(reportPath, JSON.stringify(saved, null, 2) + '\n');
  }
});
