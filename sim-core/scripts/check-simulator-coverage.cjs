#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json'), 'utf8'));
const pkgPath = require.resolve('pokemon-showdown/package.json', { paths: [root] });
const pkgRoot = path.dirname(pkgPath);
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
const lockEntry = lock.packages?.['node_modules/pokemon-showdown'];
const errors = [];
const validClassifications = new Set(['represented', 'raw-only', 'explicitly unsupported', 'unknown', 'silently omitted']);

function setDiff(actual, expected) {
  const a = new Set(actual);
  const e = new Set(expected);
  return { added: [...a].filter((x) => !e.has(x)).sort(), removed: [...e].filter((x) => !a.has(x)).sort() };
}

function treeDigest(dir) {
  const hash = crypto.createHash('sha256');
  const visit = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) visit(full);
      else if (entry.isFile() && /\.(ts|json|js)$/.test(entry.name)) {
        hash.update(path.relative(pkgRoot, full).split(path.sep).join('/'));
        hash.update('\0');
        hash.update(fs.readFileSync(full));
        hash.update('\0');
      }
    }
  };
  visit(dir);
  return hash.digest('hex');
}

function sourceInventory() {
  const roots = manifest.simulator.source_roots;
  const rootDigests = Object.fromEntries(roots.map((name) => [name, treeDigest(path.join(pkgRoot, name))]));
  const combined = crypto.createHash('sha256');
  for (const name of roots) combined.update(name).update('\0').update(rootDigests[name]);
  return { roots: rootDigests, digest: combined.digest('hex') };
}

function localSourceDigest(files) {
  const hash = crypto.createHash('sha256');
  for (const name of [...files].sort()) {
    const full = path.join(root, name);
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) throw new Error(`Missing local coverage source: ${name}`);
    hash.update(name).update('\0').update(fs.readFileSync(full)).update('\0');
  }
  return hash.digest('hex');
}

function staticEmitterTokens() {
  const found = new Set();
  const call = /\b(?:this|battle|target|source|pokemon|side|field)\.add\(\s*(['"`])([^'"`]+)\1/g;
  for (const top of ['sim', 'data']) {
    const walk = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.isFile() && full.endsWith('.ts')) {
          for (const match of fs.readFileSync(full, 'utf8').matchAll(call)) {
            const token = match[2].split('|')[0];
            if (token && !/[ ${}]/.test(token)) found.add(token);
          }
        }
      }
    };
    walk(path.join(pkgRoot, top));
  }
  return [...found].sort();
}

function manifestErrors(value) {
  const found = [];
  const requiredFields = ['id', 'category', 'source_files', 'source_symbols', 'semantics_ref', 'classification', 'review_status'];
  if (value.manifest_schema !== 'simulator-coverage/v2') found.push('unsupported manifest schema');
  if (!value.simulator || value.simulator.source_tree_sha256 !== value.simulator.reviewed_source_tree_sha256) found.push('source digest is not bound to a separate semantic-review digest');
  if (!value.local_coverage_sources || value.local_coverage_sources.sha256 !== value.local_coverage_sources.reviewed_sha256) found.push('local coverage sources are not bound to a separate semantic-review digest');
  if (!value.review || value.review.status !== value.review_status || value.review.reviewed_source_tree_sha256 !== value.simulator?.reviewed_source_tree_sha256) found.push('review attestation is missing or digest-mismatched');
  for (const item of value.condition_inventory || []) {
    for (const field of requiredFields) if (item[field] === undefined || item[field] === null || item[field] === '') found.push(`condition ${item.id || '<missing>'} missing ${field}`);
    if (!value.condition_semantics?.[item.semantics_ref]) found.push(`condition ${item.id} has no semantic group`);
    if (!validClassifications.has(item.classification)) found.push(`condition ${item.id} has invalid classification`);
    if (item.review_status !== 'reviewed_with_documented_gaps') found.push(`condition ${item.id} is not reviewed`);
  }
  const groupFields = ['sources', 'symbols', 'lifecycle', 'visibility', 'observable', 'belief', 'legal', 'raw', 'classification', 'implementation', 'tests'];
  for (const [name, group] of Object.entries(value.condition_semantics || {})) {
    for (const field of groupFields) if (group[field] === undefined || group[field] === null || group[field] === '') found.push(`condition group ${name} missing ${field}`);
    if (!validClassifications.has(group.classification)) found.push(`condition group ${name} has invalid classification`);
  }
  for (const item of value.protocol?.commands || []) {
    if (!value.protocol.grammar_groups?.[item.grammar_group]) found.push(`protocol ${item.token} has no grammar group`);
    if (!validClassifications.has(item.classification)) found.push(`protocol ${item.token} has invalid classification`);
    if (!item.parser_support || item.review_status !== 'reviewed_with_documented_gaps') found.push(`protocol ${item.token} lacks parser/review disposition`);
    if (!item.record_grammar?.required || !item.record_grammar?.optional || !item.record_grammar?.shape) found.push(`protocol ${item.token} lacks required/optional field grammar`);
    for (const field of ['target_semantics', 'visibility', 'authoritative_state_effect', 'belief_effect', 'legal_action_effect', 'fixture_reference']) {
      if (!item[field]) found.push(`protocol ${item.token} missing ${field}`);
    }
  }
  for (const [name, group] of Object.entries(value.protocol?.grammar_groups || {})) {
    for (const field of ['grammar', 'visibility', 'state', 'legal', 'fixture']) if (!group[field]) found.push(`protocol group ${name} missing ${field}`);
  }
  for (const item of value.protocol?.emitted_static_tokens || []) {
    if (!item.token || !item.source_files?.length || !item.scope || !item.classification || item.review_status !== 'reviewed_with_documented_gaps') found.push(`emitter ${item.token || '<missing>'} lacks reviewed source/scope/classification`);
  }
  return found;
}

// Verify the package pin separately from hashes of the installed source/runtime trees.
if (!lockEntry?.integrity || !lockEntry?.resolved) errors.push('Lockfile does not contain the simulator resolved tarball and integrity.');
const declaration = packageJson.dependencies?.['pokemon-showdown'];
if (pkg.version !== manifest.simulator.version || lockEntry?.version !== manifest.simulator.version || declaration !== manifest.simulator.version) {
  errors.push(`Simulator pin mismatch: package=${pkg.version}, lock=${lockEntry?.version}, declaration=${declaration}, manifest=${manifest.simulator.version}`);
}
if (manifest.format?.id !== 'gen9randombattle' || manifest.format?.game_type !== 'singles' || manifest.format?.mod !== 'gen9') errors.push('Unsupported or inconsistent format scope.');

const { Dex } = require('pokemon-showdown');
const dex = Dex.mod(manifest.format.mod);
const format = Dex.formats.get(manifest.format.id);
if (!format.exists || format.mod !== manifest.format.mod || format.gameType !== manifest.format.game_type || format.team !== manifest.format.team) errors.push('Installed format metadata does not match the coverage manifest.');

for (const issue of manifestErrors(manifest)) errors.push(`Manifest incomplete: ${issue}`);

const registryChecks = [
  ['condition_ids', Object.keys(dex.data.Conditions)],
  ['move_volatile_status', dex.moves.all().map((move) => move.volatileStatus).filter(Boolean)],
  ['move_secondary_volatile_status', dex.moves.all().flatMap((move) => (move.secondaries || []).map((secondary) => secondary.volatileStatus).filter(Boolean))],
  ['side_condition', dex.moves.all().map((move) => move.sideCondition).filter(Boolean)],
  ['pseudo_weather', dex.moves.all().map((move) => move.pseudoWeather).filter(Boolean)],
  ['terrain', dex.moves.all().map((move) => move.terrain).filter(Boolean)],
];
for (const [name, values] of registryChecks) {
  const actual = [...new Set(values)].sort();
  const expected = [...(manifest.registries?.[name] || [])].sort();
  const mismatch = setDiff(actual, expected);
  if (mismatch.added.length || mismatch.removed.length) errors.push(`${name} drift: ${JSON.stringify(mismatch)}`);
}
for (const [name, values] of Object.entries(manifest.registries || {})) {
  if (!Array.isArray(values)) errors.push(`Registry ${name} is not an array.`);
  else for (const value of values) if (!manifest.condition_inventory.some((item) => item.id === value)) errors.push(`Registry ${name} contains unclassified ID ${value}.`);
}

const installedSource = sourceInventory();
for (const name of manifest.simulator.source_roots || []) if (installedSource.roots[name] !== manifest.simulator.source_root_sha256?.[name]) errors.push(`Simulator source drift under ${name}: ${installedSource.roots[name]}`);
if (installedSource.digest !== manifest.simulator.source_tree_sha256) errors.push(`Simulator source digest changed: ${installedSource.digest}`);
try {
  const localDigest = localSourceDigest(manifest.local_coverage_sources.files);
  if (localDigest !== manifest.local_coverage_sources.sha256) errors.push(`Local coverage source digest changed: ${localDigest}`);
} catch (error) {
  errors.push(error.message);
}

const emittedDiff = setDiff(staticEmitterTokens(), (manifest.protocol?.emitted_static_tokens || []).map((item) => item.token));
if (emittedDiff.added.length || emittedDiff.removed.length) errors.push(`Static emitter inventory drift: ${JSON.stringify(emittedDiff)}`);

const parser = fs.readFileSync(path.join(root, 'src/observable_state.ts'), 'utf8');
const allowlist = parser.match(/const SUPPORTED_RAW_COMMANDS = new Set\(\[([\s\S]*?)\]\);/);
if (!allowlist) errors.push('Could not locate observable parser token allowlist.');
else {
  const actual = [...allowlist[1].matchAll(/'([^']+)'/g)].map((item) => item[1]);
  const expected = (manifest.protocol?.commands || []).map((item) => item.token);
  const mismatch = setDiff(actual, expected);
  if (mismatch.added.length || mismatch.removed.length) errors.push(`Parser token classification drift: ${JSON.stringify(mismatch)}`);
}

if (process.argv.includes('--self-test')) {
  const tests = [];
  tests.push(['new condition ID', setDiff(['known', '__new_condition__'], ['known']).added.includes('__new_condition__')]);
  tests.push(['new protocol token', setDiff(['known', '__new_protocol__'], ['known']).added.includes('__new_protocol__')]);
  tests.push(['new emitter token', setDiff(['known', '__new_emitter__'], ['known']).added.includes('__new_emitter__')]);
  tests.push(['missing classification rejected', manifestErrors({ condition_inventory: [{ id: 'x' }] }).some((item) => item === 'condition x missing classification')]);
  const digestOnlyManifest = JSON.parse(JSON.stringify(manifest));
  digestOnlyManifest.simulator.source_tree_sha256 = '__new_unreviewed_digest__';
  tests.push(['digest-only update does not attest semantic review', manifestErrors(digestOnlyManifest).some((item) => item.includes('source digest is not bound'))]);
  const localDigestOnlyManifest = JSON.parse(JSON.stringify(manifest));
  localDigestOnlyManifest.local_coverage_sources.sha256 = '__new_unreviewed_digest__';
  tests.push(['local digest-only update does not attest semantic review', manifestErrors(localDigestOnlyManifest).some((item) => item.includes('local coverage sources are not bound'))]);
  for (const [name, passed] of tests) assert.equal(passed, true, `self-test failed: ${name}`);
  console.log(`Synthetic drift self-tests passed: ${tests.map(([name]) => name).join(', ')}`);
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else if (!process.argv.includes('--self-test')) {
  console.log(`Coverage matches ${manifest.simulator.name}@${manifest.simulator.version} / ${manifest.format.id}: ${manifest.condition_inventory.length} classified condition/effect IDs; ${manifest.protocol.commands.length} parser tokens; ${manifest.protocol.emitted_static_tokens.length} literal emitter tokens.`);
}
