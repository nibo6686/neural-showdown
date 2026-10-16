import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import ts from 'typescript';

const root = path.resolve(__dirname, '../../..');
const read = (file: string): any => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const fixtures = 'docs/contracts/fixtures/perspective-knowledge-v1/';
const applications = read(fixtures + 'property-contexts.json');
const profiles = read(fixtures + 'profiles.json');
const registry = read('docs/contracts/knowledge-coverage.json');
const fields = ['property', 'family', 'context', 'perspective', 'status', 'provider', 'tests', 'limits', 'blocked_by', 'impact'].sort();
const key = (row: any): string => [row.property, row.context, row.perspective].join('/');
const identity = (row: any) => ({ property: row.property, family: row.family, context: row.context, perspective: row.perspective });
const negative = /unknown|omitt|foreign|reject|copied|stale|wrong.owner/i;
const nonempty = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

function expectedRows(): any[] {
  const families = new Map<string, string>();
  for (const profile of profiles) for (const obligation of profile.obligations) for (const property of obligation.properties) {
    assert.ok(!families.has(property) || families.get(property) === obligation.family, 'unambiguous family');
    families.set(property, obligation.family);
  }
  return Object.entries(applications).flatMap(([property, entries]: [string, any]) => entries.flatMap((entry: any) => {
    assert.ok(['owner', 'both'].includes(entry.scope));
    assert.ok(families.has(property));
    return (entry.scope === 'both' ? ['own', 'opponent'] : ['own']).map(perspective =>
      ({ property, family: families.get(property), context: entry.context, perspective }));
  }));
}

function fastSources(): Set<string> {
  const nodeFiles: string[] = read('sim-core/test-fast-files.json').files;
  const pythonFiles: string[] = read('tools/test-fast-python-files.json').files;
  for (const files of [nodeFiles, pythonFiles]) {
    assert.ok(files.length > 0);
    assert.equal(new Set(files).size, files.length, 'duplicate fast file');
    assert.ok(files.every(file => typeof file === 'string' && !/[?*]/.test(file) && !file.includes('..') && !path.isAbsolute(file)), 'explicit relative fast paths');
  }
  return new Set([...nodeFiles.map(file => 'sim-core/' + file.replace(/^dist\/tests\/(.+)\.js$/, 'tests/$1.ts')), ...pythonFiles]);
}

function namedTests(file: string): Set<string> {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  const names = new Set<string>();
  if (file.endsWith('.py')) {
    for (const match of source.matchAll(/^\s*(?:async\s+)?def\s+(test_\w+)\s*\(/gm)) names.add(match[1]);
  } else {
    const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true);
    function visit(node: ts.Node): void {
      if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && ['test', 'it'].includes(node.expression.text)
        && node.arguments[0] && ts.isStringLiteralLike(node.arguments[0])) names.add(node.arguments[0].text);
      ts.forEachChild(node, visit);
    }
    visit(tree);
  }
  return names;
}

function validate(value: any, fast = fastSources()): void {
  assert.deepEqual(Object.keys(value).sort(), ['rows', 'schema']);
  assert.equal(value.schema, 'knowledge-coverage/v1');
  assert.ok(Array.isArray(value.rows));
  const expected = expectedRows();
  const actual = value.rows.map(identity).sort((a: any, b: any) => key(a).localeCompare(key(b)));
  assert.equal(new Set(value.rows.map(key)).size, value.rows.length, 'duplicate registry row');
  assert.deepEqual(actual, expected.sort((a, b) => key(a).localeCompare(key(b))), 'exact contract applications');
  const testsByFile = new Map<string, Set<string>>();
  for (const row of value.rows) {
    assert.deepEqual(Object.keys(row).sort(), fields, key(row));
    assert.ok(['adopted', 'blocked', 'legitimately_unknown', 'missing'].includes(row.status), 'status');
    assert.ok(['high', 'medium', 'low'].includes(row.impact), 'impact');
    assert.ok(row.provider === null || (nonempty(row.provider) && /^[^:]+:[^:]+$/.test(row.provider)), 'provider file:function');
    if (row.provider) assert.ok(fs.existsSync(path.join(root, row.provider.split(':')[0])), 'provider file exists');
    assert.ok(nonempty(row.limits), 'limits');
    assert.ok(row.blocked_by === null || nonempty(row.blocked_by), 'blocked_by');
    assert.ok(Array.isArray(row.tests) && row.tests.every(nonempty), 'tests array');
    assert.equal(new Set(row.tests).size, row.tests.length, 'duplicate test citation');
    if (row.status === 'adopted') {
      assert.ok(nonempty(row.provider), 'adopted provider');
      assert.ok(row.tests.length >= 2, 'adopted positive and negative tests');
      const names: string[] = [];
      for (const citation of row.tests) {
        const [file, name, extra] = citation.split('::');
        assert.ok(file && name && extra === undefined, 'file::exact test name');
        assert.ok(fast.has(file), 'cited file must run in test:fast: ' + file);
        if (!testsByFile.has(file)) testsByFile.set(file, namedTests(file));
        assert.ok(testsByFile.get(file)!.has(name), 'exact executable test name: ' + citation);
        names.push(name);
      }
      assert.ok(names.some(name => !negative.test(name)), 'positive test citation');
      assert.ok(names.some(name => negative.test(name)), 'negative test citation');
    }
    if (row.status === 'blocked') assert.ok(nonempty(row.blocked_by), 'blocked reason');
    if (row.status === 'legitimately_unknown') {
      const reasons = row.limits.match(/\b(hidden_opponent|hidden_timer|not_emitted)\b/g) ?? [];
      assert.ok(reasons.length, 'unknown reason named in limits');
      for (const profile of profiles) {
        const obligation = profile.obligations.find((entry: any) => entry.family === row.family);
        assert.ok(obligation, 'family profile obligation');
        const allowed = row.perspective === 'opponent' ? obligation.opponent_unknown : obligation.unknown;
        assert.ok(reasons.every((reason: string) => allowed.includes(reason)), 'profile permits unknown for perspective');
      }
    }
  }
}

test('coverage registry exactly matches generated contract skeleton and scoped evidence', () => {
  validate(registry);
  const generated = spawnSync('D:\\Anaconda\\envs\\neuralgpu\\python.exe', ['tools/registry/generate_skeleton.py'], {
    cwd: root, encoding: 'utf8', timeout: 10_000,
    env: Object.fromEntries(Object.entries(process.env).filter(([name]) => !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(name))),
  });
  assert.equal(generated.status, 0, generated.stderr || generated.error?.message);
  assert.deepEqual(JSON.parse(generated.stdout).rows.map(identity), expectedRows());
  const statuses = Object.fromEntries(['adopted', 'blocked', 'legitimately_unknown', 'missing'].map(status =>
    [status, registry.rows.filter((row: any) => row.status === status).length]));
  const missingByImpact = Object.fromEntries(['high', 'medium', 'low'].map(impact =>
    [impact, registry.rows.filter((row: any) => row.status === 'missing' && row.impact === impact).length]));
  console.log('Knowledge coverage: ' + JSON.stringify({ total: registry.rows.length, statuses, missingByImpact }));
});

test('coverage validator rejects missing extra duplicate and malformed rows and unverified claims', () => {
  const attack = (change: (value: any) => void, message: string) => {
    const copy = structuredClone(registry); change(copy); assert.throws(() => validate(copy), message);
  };
  const adopted = (value: any) => value.rows.find((row: any) => row.status === 'adopted');
  const blocked = (value: any) => value.rows.find((row: any) => row.status === 'blocked');
  const unknown = (value: any) => value.rows.find((row: any) => row.status === 'legitimately_unknown');
  attack(value => value.rows.pop(), 'missing row');
  attack(value => value.rows.push({ ...value.rows[0], context: 'invented' }), 'extra row');
  attack(value => value.rows.push(value.rows[0]), 'duplicate row');
  attack(value => value.rows[0].family = 'K99', 'wrong family');
  attack(value => value.rows[0].surprise = false, 'unknown field');
  attack(value => value.rows[0].status = 'available', 'invalid status');
  attack(value => value.rows[0].impact = 'urgent', 'invalid impact');
  attack(value => adopted(value).provider = null, 'no adopted provider');
  attack(value => adopted(value).tests = adopted(value).tests.slice(0, 1), 'single test');
  attack(value => adopted(value).tests[0] += ' invented suffix', 'nonexistent exact test');
  attack(value => adopted(value).tests[0] = 'sim-core/tests/original_owner_loadout.test.ts::P59 generated original control', 'red file excluded');
  attack(value => { const row = adopted(value); row.tests = [row.tests[0], row.tests[0]]; }, 'duplicate tests');
  attack(value => { const row = adopted(value); row.tests = ['sim-core/tests/owned_request_details.test.ts::P60 generated both owners selected delivery restore and real callbacks', 'sim-core/tests/owned_request_details.test.ts::P60 forced Revival wait and terminal availability']; row.limits = 'Scoped values.'; }, 'no negative test');
  attack(value => blocked(value).blocked_by = ' ', 'empty blocker');
  attack(value => unknown(value).limits = 'Unavailable.', 'unnamed unknown reason');
  attack(value => unknown(value).limits = 'not_emitted', 'opponent reason forbidden');
  attack(value => { const row = value.rows.find((entry: any) => entry.property === 'starting_moves'); row.status = 'legitimately_unknown'; row.limits = 'not_emitted'; }, 'required original cannot be waived');
  const excluded = fastSources(); excluded.delete(registry.rows.find((row: any) => row.status === 'adopted').tests[0].split('::')[0]);
  assert.throws(() => validate(registry, excluded), /must run in test:fast/);
});
