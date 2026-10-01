#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
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
const reachabilityClasses = new Set([
  'direct_reachable', 'indirect_reachable', 'package_wide_only', 'raw_only', 'unsupported_stop', 'unknown',
]);
const formatProvenanceSources = [
  'config/config.js',
  'config/formats.ts',
  'data/random-battles/gen9/sets.json',
  'data/random-battles/gen9/teams.ts',
  'data/rulesets.ts',
  'dist/config/formats.js',
  'dist/data/random-battles/gen9/sets.json',
  'dist/data/random-battles/gen9/teams.js',
  'dist/data/rulesets.js',
  'dist/sim/battle.js',
  'dist/sim/teams.js',
  'sim/battle.ts',
  'sim/teams.ts',
];

function expectedReachabilityRoute(classification) {
  return {
    direct_reachable: 'candidate_path',
    indirect_reachable: 'callback_path',
    package_wide_only: 'out_of_scope',
    raw_only: 'preserve_raw',
    unsupported_stop: 'stop',
    unknown: 'stop',
  }[classification] || 'stop';
}

function routeReachability(formID, forms) {
  const form = forms.find((item) => item.id === formID);
  const classification = form?.classification || 'unknown';
  return { classification, route: expectedReachabilityRoute(classification) };
}

function randomSetCandidateIndex(randomSets) {
  const entries = Object.entries(randomSets || {});
  const setRows = entries.flatMap(([, species]) => species.sets || []);
  const normalize = (value) => String(value).toLowerCase().replace(/[^a-z0-9]/g, '');
  return {
    species: new Set(entries.map(([id]) => normalize(id))),
    moves: new Set(setRows.flatMap((set) => set.movepool || []).map(normalize)),
    abilities: new Set(setRows.flatMap((set) => set.abilities || []).map(normalize)),
    species_count: entries.length,
    set_count: setRows.length,
  };
}

function candidatePopulationErrors(expected, actual) {
  const found = [];
  for (const field of ['species_count', 'set_count', 'move_candidate_count', 'ability_candidate_count']) {
    if (expected?.[field] !== actual?.[field]) found.push(`Gen 9 random-set ${field} drift: ${actual?.[field]} != ${expected?.[field]}`);
  }
  return found;
}

function effectiveFormatErrors(expected, actual, candidateIndex) {
  const found = [];
  for (const field of ['id', 'name', 'mod', 'game_type', 'team']) {
    if (actual?.[field] !== expected?.[field]) found.push(`Effective format ${field} drift: ${actual?.[field]} != ${expected?.[field]}`);
  }
  if (actual?.team_size !== expected?.team_size) found.push(`Effective format team_size drift: ${actual?.team_size} != ${expected?.team_size}`);
  for (const form of expected?.forms || []) {
    if (form.candidate_ref) {
      const [kind, id] = form.candidate_ref.split(':', 2);
      const values = kind === 'move' ? candidateIndex?.moves : kind === 'ability' ? candidateIndex?.abilities : null;
      if (!values?.has(id)) found.push(`Direct random-set candidate ${form.candidate_ref} is absent from the selected Gen 9 set source.`);
    }
  }
  return found;
}

function reachabilityManifestErrors(value) {
  const found = [];
  const reachability = value.format_provenance;
  if (!reachability || reachability.schema_version !== 'gen9-random-reachability/v1') {
    return ['format reachability schema is missing or unsupported'];
  }
  const sourceFiles = reachability.source_files || [];
  for (const sourceFile of formatProvenanceSources) {
    if (!sourceFiles.includes(sourceFile)) found.push(`format provenance does not bind operative source ${sourceFile}`);
  }
  for (const sourceFile of sourceFiles) {
    if (typeof sourceFile !== 'string' || !sourceFile.trim()) found.push('format provenance contains an empty source path');
  }
  for (const root of ['config', 'dist/config']) {
    if (!(value.simulator?.source_roots || []).includes(root)) found.push(`format provenance source root ${root} is not in the simulator digest`);
  }
  const expectedClasses = new Set(reachabilityClasses);
  const seenClasses = new Set();
  for (const form of reachability.forms || []) {
    for (const field of ['id', 'classification', 'route', 'evidence']) {
      if (typeof form[field] !== 'string' || !form[field].trim()) found.push(`reachability form ${form.id || '<missing>'} missing ${field}`);
    }
    if (!Array.isArray(form.source_files) || !form.source_files.length || !Array.isArray(form.source_symbols) || !form.source_symbols.length) {
      found.push(`reachability form ${form.id || '<missing>'} lacks source evidence`);
    }
    if (!expectedClasses.has(form.classification)) found.push(`reachability form ${form.id || '<missing>'} has invalid classification`);
    else seenClasses.add(form.classification);
    if (form.route !== expectedReachabilityRoute(form.classification)) found.push(`reachability form ${form.id || '<missing>'} has unsafe route ${form.route}`);
  }
  for (const classification of reachabilityClasses) {
    if (!seenClasses.has(classification)) found.push(`format reachability has no ${classification} form`);
  }
  if (!reachability.forms?.length) found.push('format reachability has no forms');
  if (!reachability.candidate_population || !reachability.selection_trace?.length) found.push('random-set candidate/selection trace is missing');
  return found;
}

function sourceRootDrift(name, actual, expected) {
  return actual === expected ? null : `Simulator source drift under ${name}: ${actual}`;
}

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

function normalizedTextBytes(bytes) {
  const text = bytes.toString('utf8');
  if (!Buffer.from(text, 'utf8').equals(bytes)) throw new Error('Local coverage source is not valid UTF-8.');
  return Buffer.from(text.replace(/\r\n/g, '\n'), 'utf8');
}

function localSourceDigest(files, sourceRoot = root) {
  const hash = crypto.createHash('sha256');
  for (const name of [...files].sort()) {
    const full = path.join(sourceRoot, name);
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) throw new Error(`Missing local coverage source: ${name}`);
    hash.update(name).update('\0').update(normalizedTextBytes(fs.readFileSync(full))).update('\0');
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

function effectInventoryItems(value) {
  return [...(value.condition_inventory || []), ...(value.effect_discovery?.additional_entries || [])];
}

const effectValueFields = new Set(['volatileStatus', 'sideCondition', 'pseudoWeather', 'terrain', 'weather', 'slotCondition']);

function collectNestedEffectIdentifiers(value, family, found = []) {
  if (!value || typeof value !== 'object') return found;
  for (const [key, child] of Object.entries(value)) {
    const childFamily = `${family}.${key}`;
    if (effectValueFields.has(key) && typeof child === 'string' && child.trim()) {
      found.push({ id: child.toLowerCase().replace(/[^a-z0-9]/g, ''), family: childFamily });
    }
    if (child && typeof child === 'object') collectNestedEffectIdentifiers(child, childFamily, found);
  }
  return found;
}

function resolvedEffectIdentifiers(dex) {
  const found = [];
  const unique = (entries) => [...new Map(entries.map((entry) => [entry.id, entry])).values()];
  for (const move of unique(dex.moves.all())) {
    for (const key of ['volatileStatus', 'sideCondition', 'pseudoWeather', 'terrain', 'weather', 'slotCondition']) {
      const value = move[key];
      if (typeof value === 'string' && value.trim()) found.push({ id: value.toLowerCase().replace(/[^a-z0-9]/g, ''), family: `Move.${key}` });
    }
    if (move.condition) found.push({ id: move.id, family: 'Move.condition' });
    found.push(...collectNestedEffectIdentifiers(move, 'Move'));
  }
  for (const [type, entries] of [['Ability', dex.abilities.all()], ['Item', dex.items.all()]]) {
    for (const entry of unique(entries)) {
      if (entry.condition) found.push({ id: entry.id, family: `${type}.condition` });
      found.push(...collectNestedEffectIdentifiers(entry, type));
    }
  }
  return found;
}

function effectFamilyMatches(actual, patterns) {
  const actualParts = actual.replace(/\.(\d+)\./g, '.[*].').split('.');
  return patterns.some((pattern) => {
    const expectedParts = pattern.replace(/\[\*\]/g, '.[*]').split('.');
    if (expectedParts.length !== actualParts.length) return false;
    return expectedParts.every((part, index) => part === '*'
      ? actualParts[index] !== ''
      : part === '[*]' ? actualParts[index] === '[*]' : part === actualParts[index]);
  });
}

function computedVolatileCallSites() {
  const files = ['data/moves.ts', 'data/abilities.ts', 'data/items.ts', 'data/conditions.ts', 'sim/battle-actions.ts', 'sim/battle.ts', 'sim/pokemon.ts'];
  const sites = [];
  const call = /\b[\w.]+\.addVolatile\(\s*([^,)]+)(?:,[^)]*)?\)/g;
  for (const sourceFile of files) {
    const source = fs.readFileSync(path.join(pkgRoot, sourceFile), 'utf8');
    for (const match of source.matchAll(call)) {
      const argument = match[1].trim();
      if (!/^['"]/.test(argument)) {
        const familyBySite = {
          'data/moves.ts|volatile': 'Move.callback.addVolatile(computed)',
          'data/abilities.ts|volatile': 'Ability.callback.addVolatile(computed)',
          'data/conditions.ts|effect.id': 'Condition.callback.addVolatile(computed)',
          'sim/battle-actions.ts|move.id': 'BattleActions.addVolatile(computed)',
          'sim/battle-actions.ts|moveData.volatileStatus': 'BattleActions.addVolatile(computed)',
          'sim/pokemon.ts|volatile': 'Pokemon.copyVolatile.addVolatile(computed)',
          'sim/pokemon.ts|linkedStatus': 'Pokemon.addLinkedStatus.addVolatile(computed)',
        };
        const key = `${sourceFile}|${argument}`;
        sites.push({ key, family: familyBySite[key] || 'unreviewed addVolatile family' });
      }
    }
  }
  return [...new Map(sites.map((site) => [site.key, site])).values()].sort((a, b) => a.key.localeCompare(b.key));
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
  const effectDiscovery = value.effect_discovery;
  if (!effectDiscovery || effectDiscovery.schema_version !== 'simulator-effect-inventory/v1') found.push('effect discovery schema is missing or unsupported');
  for (const family of effectDiscovery?.source_families || []) if (typeof family !== 'string' || !family.trim()) found.push('effect discovery contains an empty source family');
  if (!effectDiscovery?.source_families?.length) found.push('effect discovery has no source family patterns');
  const effectIDs = new Set((value.condition_inventory || []).map((item) => item.id));
  for (const item of effectDiscovery?.additional_entries || []) {
    for (const field of ['id', 'category', 'semantics_ref', 'classification', 'review_status', 'visibility', 'projection_path', 'evidence']) {
      if (!item[field]) found.push(`effect ${item.id || '<missing>'} missing ${field}`);
    }
    if (!item.source_files?.length || !item.source_symbols?.length) found.push(`effect ${item.id || '<missing>'} missing source location`);
    if (!validClassifications.has(item.classification)) found.push(`effect ${item.id} has invalid classification`);
    if (!value.condition_semantics?.[item.semantics_ref]) found.push(`effect ${item.id} has no semantic group`);
    if (effectIDs.has(item.id)) found.push(`effect ${item.id} duplicates an existing condition inventory ID`);
    effectIDs.add(item.id);
  }
  for (const item of effectDiscovery?.computed_add_volatile_calls || []) {
    for (const field of ['source_file', 'argument', 'family', 'disposition']) {
      if (typeof item[field] !== 'string' || !item[field].trim()) found.push(`computed addVolatile call missing ${field}`);
    }
    if (!['represented', 'raw-only', 'unknown fail closed at emitted protocol value'].includes(item.disposition)) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} has no explicit disposition`);
    }
    if (item.disposition === 'represented' && (!Array.isArray(item.known_values) || !item.known_values.length || item.known_values.some((id) => !effectInventoryItems(value).some((entry) => entry.id === id && entry.classification === 'represented')))) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} lacks represented inventory values`);
    }
  }
  if (!effectDiscovery?.computed_add_volatile_calls?.length) found.push('effect discovery has no computed addVolatile call dispositions');
  for (const item of effectDiscovery?.special_values || []) {
    for (const field of ['id', 'source_file', 'projection_path', 'classification']) {
      if (typeof item[field] !== 'string' || !item[field].trim()) found.push(`special effect ${item.id || '<missing>'} missing ${field}`);
    }
    if (!Array.isArray(item.commands) || !item.commands.length || item.commands.some((command) => typeof command !== 'string' || !command.trim())) {
      found.push(`special effect ${item.id || '<missing>'} has no command scope`);
    }
    if (!validClassifications.has(item.classification)) found.push(`special effect ${item.id || '<missing>'} has invalid classification`);
  }
  const allEffectIDs = effectInventoryItems(value).map((item) => item.id);
  if (new Set(allEffectIDs).size !== allEffectIDs.length) found.push('effect inventory contains duplicate identifiers');
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
  found.push(...reachabilityManifestErrors(value));
  return found;
}

// Verify the package pin separately from hashes of the installed source/runtime trees.
if (!lockEntry?.integrity || !lockEntry?.resolved) errors.push('Lockfile does not contain the simulator resolved tarball and integrity.');
const declaration = packageJson.dependencies?.['pokemon-showdown'];
if (pkg.version !== manifest.simulator.version || lockEntry?.version !== manifest.simulator.version || declaration !== manifest.simulator.version) {
  errors.push(`Simulator pin mismatch: package=${pkg.version}, lock=${lockEntry?.version}, declaration=${declaration}, manifest=${manifest.simulator.version}`);
}
if (manifest.format?.id !== 'gen9randombattle' || manifest.format?.game_type !== 'singles' || manifest.format?.mod !== 'gen9') errors.push('Unsupported or inconsistent format scope.');

const { Dex, Teams } = require('pokemon-showdown');
const dex = Dex.mod(manifest.format.mod);
const format = Dex.formats.get(manifest.format.id);
if (!format.exists || format.mod !== manifest.format.mod || format.gameType !== manifest.format.game_type || format.team !== manifest.format.team) errors.push('Installed format metadata does not match the coverage manifest.');
const effectiveFormat = {
  id: format.id,
  name: format.name,
  mod: format.mod,
  game_type: format.gameType,
  team: format.team,
  team_size: Dex.formats.getRuleTable(format).maxTeamSize,
};
const gen9RandomTeams = Teams.getGenerator(format, [1, 2, 3, 4]);
const candidateIndex = randomSetCandidateIndex(gen9RandomTeams.randomSets);
const candidateSummary = {
  species_count: candidateIndex.species_count,
  set_count: candidateIndex.set_count,
  move_candidate_count: candidateIndex.moves.size,
  ability_candidate_count: candidateIndex.abilities.size,
};
errors.push(...effectiveFormatErrors(manifest.format_provenance?.effective_format, effectiveFormat, candidateIndex));
errors.push(...candidatePopulationErrors(manifest.format_provenance?.candidate_population, candidateSummary));
for (const sourceFile of formatProvenanceSources) {
  if (!fs.existsSync(path.join(pkgRoot, sourceFile))) errors.push(`Missing operative format/reachability source: ${sourceFile}`);
}

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
  else for (const value of values) if (!effectInventoryItems(manifest).some((item) => item.id === value)) errors.push(`Registry ${name} contains unclassified ID ${value}.`);
}

const effectInventory = effectInventoryItems(manifest);
const effectIDSet = new Set(effectInventory.map((item) => item.id));
const discoveredEffectIdentifiers = resolvedEffectIdentifiers(dex);
for (const effect of discoveredEffectIdentifiers) {
  if (!effectIDSet.has(effect.id)) errors.push(`Unclassified nested simulator effect ${effect.id} from ${effect.family}.`);
  if (!effectFamilyMatches(effect.family, manifest.effect_discovery?.source_families || [])) {
    errors.push(`Unclassified nested simulator effect family ${effect.family}.`);
  }
}
const discoveredComputedCalls = computedVolatileCallSites();
const reviewedComputedCalls = manifest.effect_discovery?.computed_add_volatile_calls || [];
const reviewedComputedKeys = reviewedComputedCalls.map((item) => `${item.source_file}|${item.argument}`).sort();
const discoveredComputedKeys = discoveredComputedCalls.map((item) => item.key);
const dynamicCallDiff = setDiff(discoveredComputedKeys, reviewedComputedKeys);
if (dynamicCallDiff.added.length || dynamicCallDiff.removed.length) errors.push(`Computed addVolatile family drift: ${JSON.stringify(dynamicCallDiff)}`);
for (const discovered of discoveredComputedCalls) {
  const reviewed = reviewedComputedCalls.find((item) => `${item.source_file}|${item.argument}` === discovered.key);
  if (reviewed && reviewed.family !== discovered.family) errors.push(`Computed addVolatile family drift at ${discovered.key}: ${discovered.family} != ${reviewed.family}`);
}

const installedSource = sourceInventory();
for (const name of manifest.simulator.source_roots || []) {
  const drift = sourceRootDrift(name, installedSource.roots[name], manifest.simulator.source_root_sha256?.[name]);
  if (drift) errors.push(drift);
}
if (installedSource.digest !== manifest.simulator.source_tree_sha256) errors.push(`Simulator source digest changed: ${installedSource.digest}`);
try {
  const localDigest = localSourceDigest(manifest.local_coverage_sources.files);
  if (localDigest !== manifest.local_coverage_sources.sha256) errors.push(`Local coverage source digest changed: ${localDigest}`);
} catch (error) {
  errors.push(error.message);
}

const emittedDiff = setDiff(staticEmitterTokens(), (manifest.protocol?.emitted_static_tokens || []).map((item) => item.token));
if (emittedDiff.added.length || emittedDiff.removed.length) errors.push(`Static emitter inventory drift: ${JSON.stringify(emittedDiff)}`);

const protocolContractPath = path.resolve(root, '../trainer/src/neural/protocol_contract.json');
try {
  const protocolContract = JSON.parse(fs.readFileSync(protocolContractPath, 'utf8'));
  const actual = protocolContract.supported_commands;
  const expected = (manifest.protocol?.commands || []).map((item) => item.token);
  if (!Array.isArray(actual) || new Set(actual).size !== actual.length) {
    errors.push('Shared protocol contract command list is malformed or contains duplicates.');
  } else {
    const mismatch = setDiff(actual, expected);
    if (mismatch.added.length || mismatch.removed.length) errors.push(`Parser token classification drift: ${JSON.stringify(mismatch)}`);
  }
  const contractUnsupported = (protocolContract.recognized_unsupported_commands || []).map((item) => item.token);
  const manifestUnsupported = (manifest.protocol?.recognized_unsupported_commands || []).map((item) => item.token);
  const unsupportedDiff = setDiff(contractUnsupported, manifestUnsupported);
  if (unsupportedDiff.added.length || unsupportedDiff.removed.length) errors.push(`Recognized unsupported protocol classification drift: ${JSON.stringify(unsupportedDiff)}`);
} catch (error) {
  errors.push(`Could not read the shared protocol contract: ${error.message}`);
}

if (process.argv.includes('--self-test') || process.argv.includes('--reachability-self-test')) {
  const tests = [];
  tests.push(['local source digest is CRLF-invariant',
    Buffer.compare(Buffer.from('a\nb\n'), normalizedTextBytes(Buffer.from('a\r\nb\r\n'))) === 0]);
  tests.push(['lone CR remains identity-bearing',
    Buffer.compare(Buffer.from('a\nb\n'), normalizedTextBytes(Buffer.from('a\rb\n'))) !== 0]);
  tests.push(['substantive text changes remain identity-bearing',
    Buffer.compare(normalizedTextBytes(Buffer.from('alpha\n')), normalizedTextBytes(Buffer.from('alpHa\n'))) !== 0]);
  let invalidUtf8Rejected = false;
  try { normalizedTextBytes(Buffer.from([0xff])); } catch { invalidUtf8Rejected = true; }
  tests.push(['invalid UTF-8 source is rejected', invalidUtf8Rejected]);
  const localSourceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simulator-coverage-local-source-'));
  const localLockName = 'trainer/requirements/simulator-record.txt';
  const localLockPath = path.join(localSourceRoot, localLockName);
  fs.mkdirSync(path.dirname(localLockPath), { recursive: true });
  try {
    fs.writeFileSync(localLockPath, 'pytest==8.4.2\n', 'utf8');
    const lockDigest = localSourceDigest([localLockName], localSourceRoot);
    fs.writeFileSync(localLockPath, 'pytest==8.4.3\n', 'utf8');
    const modifiedLockDigest = localSourceDigest([localLockName], localSourceRoot);
    tests.push(['listed lock content changes local source digest', lockDigest !== modifiedLockDigest]);
    tests.push(['omitting listed lock changes local source digest', lockDigest !== localSourceDigest([], localSourceRoot)]);
    fs.unlinkSync(localLockPath);
    let missingLockRejected = false;
    try { localSourceDigest([localLockName], localSourceRoot); } catch (error) {
      missingLockRejected = error.message.includes('Missing local coverage source');
    }
    tests.push(['missing listed lock source fails closed', missingLockRejected]);
  } finally {
    fs.rmSync(localSourceRoot, { recursive: true, force: true });
  }
  tests.push(['new condition ID', setDiff(['known', '__new_condition__'], ['known']).added.includes('__new_condition__')]);
  tests.push(['new protocol token', setDiff(['known', '__new_protocol__'], ['known']).added.includes('__new_protocol__')]);
  tests.push(['new emitter token', setDiff(['known', '__new_emitter__'], ['known']).added.includes('__new_emitter__')]);
  const nestedProbe = collectNestedEffectIdentifiers({ self: { secondary: { volatileStatus: '__synthetic_nested_effect__' } } }, 'Move');
  tests.push(['synthetic nested effect source is discovered', nestedProbe.some((item) => item.id === 'syntheticnestedeffect' && item.family === 'Move.self.secondary.volatileStatus')]);
  tests.push(['novel nested family is not covered by existing rules', !effectFamilyMatches('Move.hit.secondary.volatileStatus', manifest.effect_discovery?.source_families || [])]);
  const callbackProbe = collectNestedEffectIdentifiers({ fling: { volatileStatus: '__synthetic_callback_effect__' } }, 'Item');
  tests.push(['synthetic callback effect source is discovered', callbackProbe.some((item) => item.id === 'syntheticcallbackeffect' && item.family === 'Item.fling.volatileStatus')]);
  tests.push(['novel item callback family is not covered', !effectFamilyMatches('Item.futureCallback.volatileStatus', manifest.effect_discovery?.source_families || [])]);
  const abilityCallbackProbe = collectNestedEffectIdentifiers({ condition: { onStart: { volatileStatus: '__synthetic_ability_callback__' } } }, 'Ability');
  tests.push(['synthetic ability condition callback effect is discovered', abilityCallbackProbe.some((item) => item.id === 'syntheticabilitycallback' && item.family === 'Ability.condition.onStart.volatileStatus')]);
  tests.push(['unreviewed ability callback family remains fail-closed', !effectFamilyMatches('Ability.condition.onStart.volatileStatus', manifest.effect_discovery?.source_families || [])]);
  const realEffectInventory = new Set(effectInventoryItems(manifest).map((item) => item.id));
  const resolvedEffects = resolvedEffectIdentifiers(dex);
  tests.push(['resolved Item.condition is source-discovered and classified', resolvedEffects.some((item) => item.id === 'micleberry' && item.family === 'Item.condition') && realEffectInventory.has('micleberry')]);
  tests.push(['resolved Item callback volatile is source-discovered and classified', resolvedEffects.some((item) => item.id === 'flinch' && item.family === 'Item.fling.volatileStatus') && realEffectInventory.has('flinch')]);
  tests.push(['pinned Pokemon.copyVolatile callsite is scanned', discoveredComputedCalls.some((item) => item.key === 'sim/pokemon.ts|volatile' && item.family === 'Pokemon.copyVolatile.addVolatile(computed)')]);
  tests.push(['pinned Pokemon.addVolatile linked-status callsite is scanned', discoveredComputedCalls.some((item) => item.key === 'sim/pokemon.ts|linkedStatus' && item.family === 'Pokemon.addLinkedStatus.addVolatile(computed)')]);
  const mismatchedComputedFamilyManifest = JSON.parse(JSON.stringify(manifest));
  mismatchedComputedFamilyManifest.effect_discovery.computed_add_volatile_calls.find((item) => item.source_file === 'sim/pokemon.ts' && item.argument === 'volatile').family = 'unreviewed family';
  tests.push(['computed addVolatile family drift is rejected', discoveredComputedCalls.some((site) => {
    const reviewed = mismatchedComputedFamilyManifest.effect_discovery.computed_add_volatile_calls.find((item) => `${item.source_file}|${item.argument}` === site.key);
    return reviewed && reviewed.family !== site.family;
  })]);
  tests.push(['missing classification rejected', manifestErrors({ condition_inventory: [{ id: 'x' }] }).some((item) => item === 'condition x missing classification')]);
  const digestOnlyManifest = JSON.parse(JSON.stringify(manifest));
  digestOnlyManifest.simulator.source_tree_sha256 = '__new_unreviewed_digest__';
  tests.push(['digest-only update does not attest semantic review', manifestErrors(digestOnlyManifest).some((item) => item.includes('source digest is not bound'))]);
  const localDigestOnlyManifest = JSON.parse(JSON.stringify(manifest));
  localDigestOnlyManifest.local_coverage_sources.sha256 = '__new_unreviewed_digest__';
  tests.push(['local digest-only update does not attest semantic review', manifestErrors(localDigestOnlyManifest).some((item) => item.includes('local coverage sources are not bound'))]);
  const newlyTrustedComputedEffect = JSON.parse(JSON.stringify(manifest));
  newlyTrustedComputedEffect.effect_discovery.computed_add_volatile_calls[0].disposition = 'represented';
  tests.push(['computed addVolatile represented disposition requires classified values', manifestErrors(newlyTrustedComputedEffect).some((item) => item.includes('lacks represented inventory values'))]);
  tests.push(['operative format/config files are listed for provenance', formatProvenanceSources.every((sourceFile) => manifest.format_provenance?.source_files?.includes(sourceFile))]);
  tests.push(['installed effective random format matches the manifest', effectiveFormatErrors(manifest.format_provenance?.effective_format, effectiveFormat, candidateIndex).length === 0]);
  tests.push(['installed random-set candidate counts match the manifest', candidatePopulationErrors(manifest.format_provenance?.candidate_population, candidateSummary).length === 0]);
  tests.push(['operative format and random-team source files exist', formatProvenanceSources.every((sourceFile) => fs.existsSync(path.join(pkgRoot, sourceFile)))]);
  tests.push(['format config root drift fails closed', sourceRootDrift('config', '__changed_config__', '__reviewed_config__') !== null]);
  tests.push(['runtime format metadata drift fails closed', effectiveFormatErrors(
    { id: 'gen9randombattle', name: '[Gen 9] Random Battle', mod: 'gen9', game_type: 'singles', team: 'random', team_size: 6 },
    { id: 'gen9randombattle', name: '[Gen 9] Random Battle', mod: 'gen9', game_type: 'singles', team: 'custom', team_size: 6 },
    { moves: new Set(), abilities: new Set() },
  ).some((issue) => issue.includes('Effective format team drift'))]);
  tests.push(['direct candidate count drift fails closed', candidatePopulationErrors(
    { species_count: 507, set_count: 869, move_candidate_count: 350, ability_candidate_count: 203 },
    { species_count: 507, set_count: 869, move_candidate_count: 349, ability_candidate_count: 203 },
  ).some((issue) => issue.includes('move_candidate_count drift'))]);
  const representativeForms = [
    { id: 'candidate:bodypress', classification: 'direct_reachable' },
    { id: 'callback:magicbounce-reflection', classification: 'indirect_reachable' },
    { id: 'condition:dynamax', classification: 'package_wide_only' },
    { id: 'protocol:-singleturn', classification: 'raw_only' },
    { id: 'protocol:-singlemove', classification: 'unsupported_stop' },
    { id: 'computed:addVolatile-unresolved', classification: 'unknown' },
  ];
  const expectedRoutes = ['candidate_path', 'callback_path', 'out_of_scope', 'preserve_raw', 'stop', 'stop'];
  tests.push(['direct, indirect, package-only, raw-only, unsupported, and unknown forms route explicitly',
    representativeForms.every((form, index) => {
      const route = routeReachability(form.id, representativeForms);
      return route.classification === form.classification && route.route === expectedRoutes[index];
    })]);
  tests.push(['unlisted reachability form defaults to unknown stop', routeReachability('__unlisted__', representativeForms).route === 'stop']);
  for (const [name, passed] of tests) assert.equal(passed, true, `self-test failed: ${name}`);
  console.log(`Synthetic drift self-tests passed: ${tests.map(([name]) => name).join(', ')}`);
  if (process.argv.includes('--reachability-self-test')) process.exit(0);
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else if (!process.argv.includes('--self-test')) {
  console.log(`Coverage matches ${manifest.simulator.name}@${manifest.simulator.version} / ${manifest.format.id}: ${effectInventory.length} classified condition/effect IDs; ${manifest.protocol.commands.length} parser tokens; ${manifest.protocol.emitted_static_tokens.length} literal emitter tokens; ${discoveredComputedCalls.length} computed addVolatile families.`);
}
