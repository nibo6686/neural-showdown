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
const fce01Rows = Array.from({ length: 30 }, (_, index) => `C${String(index + 1).padStart(2, '0')}`);
// Registration is limited to independently reviewed finite source contracts.
const fce01RequiredBlockers = new Set();
const c22AuditScopeMarker = 'FCE-01-CALLBACK-COMPOSITION-TRUTH';
const scopedRegistrations = {
  C22: ['finite-callback-crosswalk', 'item-carrier-attribution', 'requestless-invalidation', 'false-base-rejection', 'partial-owned-authority'],
  C23: ['enumerated-B22-results', 'health-status-faint-representability', 'privacy-restoration', 'validated-terminal-authority'],
};
const c22ScopedRequirements = {
  witness: ['B17', 'Trace/plain/boost/Imposter/form', 'ability_callback.test.ts', 'pipeline_episode.test.ts', 'test_public_consequences.py', 'independent requestless invalidation review 2026-10-09'],
  typescript_python: ['TS v1/v2', 'Python v2 episode-observation', 'known/changed compatibility', 'No generic callback inference or hidden-default authority'],
  privacy_restoration: ['no public opponent ability inference'],
  records_agree: ['C22 scoped acceptance registered 2026-10-09', 'faithful_complete_episode:false'],
};
const c23ScopedRequirements = {
  witness: ['B22', 'wish.test.ts', 'healing_wish.test.ts', 'future_sight.test.ts', 'revival.test.ts'],
  typescript_python: [
    'enumerated B22 slot public-result sufficiency',
    'exact current owned health/public rounding',
    'representability',
    'validated terminal predecessor/action authority',
  ],
  privacy_restoration: ['no slot timers', 'Pending-slot maps', 'Privacy:', 'restoration'],
  records_agree: ['C23 scoped acceptance registered 2026-10-09', 'faithful_complete_episode:false'],
};
const c23AuditScopeMarker = 'FCE-01-C23-SLOT-RESULT-SUFFICIENCY';
const publicConsequenceCategories = new Set([
  'evidence-typed', 'raw', 'public-private consequence', 'source-unreachable', 'unsupported',
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

function sha256Text(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function selectedMoveValues(candidateIndex, dex) {
  const moves = [...candidateIndex.moves];
  return {
    twoturnmove_effect_id: moves.filter((id) => /addVolatile\(["']twoturnmove["']/.test(String(dex.moves.get(id).onTryMove))).sort(),
    cantusetwice: moves.filter((id) => dex.moves.get(id).flags?.cantusetwice).sort(),
    volatile_status: [...new Set(moves.map((id) => dex.moves.get(id).volatileStatus).filter(Boolean))].sort(),
  };
}

function selectedMoveVolatileOutputValues(candidateIndex, dex) {
  const found = new Set();
  for (const id of candidateIndex.moves) {
    const move = dex.moves.get(id);
    for (const value of [move.volatileStatus, move.self?.volatileStatus, move.secondary?.volatileStatus,
      ...(move.secondaries || []).map((secondary) => secondary.volatileStatus)]) {
      if (typeof value === 'string' && value) found.add(value.toLowerCase().replace(/[^a-z0-9]/g, ''));
    }
  }
  return [...found].sort();
}

function selectorSourceDigest(source) {
  const symbols = ['randomMoveset', 'shouldCullAbility', 'getAbility', 'getPriorityItem', 'getItem'];
  const chunks = symbols.map((symbol, index) => {
    const start = source.indexOf(`\n\t${symbol}(`);
    const nextStarts = symbols.slice(index + 1)
      .map((next) => source.indexOf(`\n\t${next}(`))
      .filter((offset) => offset >= 0);
    const end = nextStarts.length ? Math.min(...nextStarts) : source.indexOf('\n\trandomSet(', start);
    return start < 0 || end < start ? `missing:${symbol}` : source.slice(start, end);
  });
  return sha256Text(chunks.join('\n/* CE-03A selector boundary */\n'));
}

function generatorClosureErrors(expected, candidateIndex, dex) {
  const found = [];
  if (!expected || expected.schema_version !== 'gen9-random-generator-output/v1') {
    return ['CE-03A generator-to-output closure is missing or unsupported'];
  }
  for (const field of ['move_candidate_sha256', 'ability_candidate_sha256', 'selector_source_sha256']) {
    if (typeof expected[field] !== 'string' || !/^[a-f0-9]{64}$/.test(expected[field])) {
      found.push(`CE-03A generator closure has invalid ${field}`);
    }
  }
  if (expected.move_candidate_sha256 !== sha256Text([...candidateIndex.moves].sort().join('\n') + '\n')) {
    found.push('CE-03A direct generated move candidates changed without an explicit disposition.');
  }
  if (expected.ability_candidate_sha256 !== sha256Text([...candidateIndex.abilities].sort().join('\n') + '\n')) {
    found.push('CE-03A direct generated ability candidates changed without an explicit disposition.');
  }
  const source = fs.readFileSync(path.join(pkgRoot, 'data/random-battles/gen9/teams.ts'), 'utf8');
  const selectorFragments = expected.selector_source_fragments;
  if (!Array.isArray(selectorFragments) || !selectorFragments.length || selectorFragments.some((fragment) => typeof fragment !== 'string' || !fragment.trim())) {
    found.push('CE-03A generator closure has no selector source fragments.');
  } else {
    if (expected.selector_source_sha256 !== selectorSourceDigest(source)) {
      found.push('CE-03A generator selector or format guard changed without an explicit disposition.');
    }
    for (const fragment of selectorFragments) if (!source.includes(fragment)) {
      found.push(`CE-03A generator selector/format guard is absent: ${fragment}`);
    }
  }
  const actualValues = selectedMoveValues(candidateIndex, dex);
  if (!expected.finite_move_values || typeof expected.finite_move_values !== 'object') {
    found.push('CE-03A generator closure has no finite generated move values.');
  } else for (const [name, actual] of Object.entries(actualValues)) {
    const listed = expected.finite_move_values[name];
    if (!Array.isArray(listed) || JSON.stringify([...listed].sort()) !== JSON.stringify(actual)) {
      found.push(`CE-03A finite generated ${name} values changed without an explicit disposition.`);
    }
  }
  if (!Array.isArray(expected.paths) || !expected.paths.length) {
    found.push('CE-03A generator closure has no direct-path dispositions.');
  } else for (const pathItem of expected.paths) {
    for (const field of ['id', 'candidate_membership', 'selection', 'realizability', 'output_request_family', 'disposition']) {
      if (typeof pathItem?.[field] !== 'string' || !pathItem[field].trim()) {
        found.push(`CE-03A direct path ${pathItem?.id || '<missing>'} lacks ${field}`);
      }
    }
  }
  return found;
}

function publicItemEvidenceErrors(value) {
  const contract = value.public_item_evidence;
  const expected = {
    schema_version: 'public-item-evidence/v1',
    pinned_scope: 'pokemon-showdown@0.11.10 gen9randombattle/gen9 singles random',
    writers: ['-item', '-enditem', 'item', 'enditem'],
    opponent_presence: 'existing optional item:has-item only with eligible public held fact',
    absence: 'marker omitted after proven consumption/removal',
    unknown: 'fresh switch/drag appearance or no eligible writer; marker omitted',
    suppression: "existing owned item_suppressed equals prefix-established Magic Room only; never trust the candidate field map",
    terminal_identity: 'validated linked input/action/transition or full committed predecessor chain; exact prefix/perspective/stable ordered roster continuity; no mutable alias or standalone optional predecessor',
    terminal_privacy: 'nonserialized context, opposite view public identity only, temporary validation context discarded on failure',
    historical_carrier: "departed unrevealed appearance with eligible Illusion roster stays raw-only/unknown; current addressed item exact; no bench nickname attribution",
    incoming_terminal: "canonical submitted switch plus validated predecessor owned slot and transition; bare envelope without action rejects unrevealed incoming alias",
    private_restoration: "request-only history v1 preserved; submitted switch provenance uses private v2; no public identity/schema change or envelope authority",
    canonical_identity: 'existing observable v1/v2 and identity algorithms unchanged',
    acceptance: 'C22 and C23 accepted within registered finite scopes; FCE-01 source/evidence closure is separate from pending complete-chain validation',
  };
  if (!contract) return ['public item evidence contract is missing'];
  const found = [];
  for (const [field, expectedValue] of Object.entries(expected)) {
    if (JSON.stringify(contract[field]) !== JSON.stringify(expectedValue)) found.push(`public item evidence ${field} drifted without disposition`);
  }
  const files = ['src/public_item.ts', 'src/public_health.ts', 'src/state_extractor.ts', 'src/env_manager.ts', '../trainer/src/neural/public_item.py', '../trainer/src/neural/public_health.py',
    'tests/item_identity.test.ts', 'tests/public_consequence_test_helpers.ts', '../trainer/tests/test_public_consequences.py', '../trainer/tests/test_pipeline_record.py'];
  for (const file of files) if (!value.local_coverage_sources?.files?.includes(file)
    || !(contract.implementation_sources || []).includes(file) && !(contract.matrix_sources || []).includes(file)) {
    found.push(`public item evidence source is not coverage-bound: ${file}`);
  }
  return found;
}

function publicConsequenceMatrixErrors(value, candidateIndex, dex) {
  const found = [];
  const matrix = value.public_consequence_matrix;
  const expectedRows = new Map([
    ['ability-callback-roots', 'public-private consequence'],
    ['item-callback-roots', 'public-private consequence'],
    ['status-callback-consequences', 'public-private consequence'],
    ['callback-public-records', 'raw'],
    ['callback-public-typed-consequences', 'evidence-typed'],
    ['neutralizing-gas-global-ignore', 'source-unreachable'],
    ['wish-pending-slot', 'raw'],
    ['wish-resolution', 'evidence-typed'],
    ['healing-wish-replacement', 'public-private consequence'],
    ['future-sight-pending-slot', 'raw'],
    ['future-sight-resolution', 'public-private consequence'],
    ['revival-selection', 'public-private consequence'],
    ['revival-resolution', 'evidence-typed'],
    ['lunar-dance-no-route', 'source-unreachable'],
    ['doom-desire-no-route', 'source-unreachable'],
    ['z-healreplacement-no-route', 'source-unreachable'],
    ['unregistered-callback-or-slot-route', 'unsupported'],
  ]);
  if (!matrix || matrix.schema_version !== 'public-consequence-matrix/v1'
    || matrix.pinned_scope !== 'pokemon-showdown@0.11.10 gen9randombattle/gen9 singles random') {
    return ['public-consequence matrix is missing, unsupported, or unpinned'];
  }
  if (JSON.stringify(matrix.categories) !== JSON.stringify([
    'evidence-typed', 'raw', 'public-private consequence', 'source-unreachable', 'unsupported',
  ])) found.push('public-consequence matrix category vocabulary drifted');
  if (!Array.isArray(matrix.rows) || matrix.rows.length !== expectedRows.size) {
    found.push('public-consequence matrix does not cover the reviewed consequence classes');
  } else {
    const ids = matrix.rows.map((row) => row?.id).sort();
    if (JSON.stringify(ids) !== JSON.stringify([...expectedRows.keys()].sort())) {
      found.push('public-consequence matrix route IDs drifted');
    }
    for (const row of matrix.rows) {
      if (!publicConsequenceCategories.has(row?.category)) {
        found.push(`public-consequence row ${row?.id || '<missing>'} has an unsupported category`);
      }
      if (expectedRows.has(row?.id) && expectedRows.get(row.id) !== row.category) {
        found.push(`public-consequence row ${row.id} changed its source disposition`);
      }
      for (const field of ['id', 'route', 'source_symbols', 'public_consequence', 'capture', 'witnesses']) {
        if (typeof row?.[field] !== 'string' || !row[field].trim()) {
          found.push(`public-consequence row ${row?.id || '<missing>'} lacks ${field}`);
        }
      }
    }
  }
  const auditPath = path.resolve(root, '../docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md');
  let audit = '';
  try { audit = fs.readFileSync(auditPath, 'utf8'); } catch { /* reported as a missing crosswalk below */ }
  if (!audit.includes(`| **C22 callback composition** | **ACCEPTED SCOPED — ${c22AuditScopeMarker}**`)
    || !audit.includes('covers only the reviewed finite callback crosswalk, requestless invalidation, false-base rejection, and partial authority')
    || !audit.includes(`| **C23 slot-effect sufficiency** | **ACCEPTED SCOPED — ${c23AuditScopeMarker}**`)
    || !audit.includes('covers only enumerated B22 public slot outcomes, health/status/faint representation, privacy/restoration, and validated terminal owner/action authority')) {
    found.push('closure audit does not agree on bounded C22/C23 acceptance');
  }
  for (const row of matrix.rows || []) {
    if (!audit.includes(`| \`${row.id}\` | ${row.category} |`)) {
      found.push(`closure audit is missing public-consequence route/category ${row.id}`);
    }
  }

  const closure = value.format_provenance?.generator_to_output_closure;
  const identity = matrix.source_identity;
  const candidatePopulation = value.format_provenance?.candidate_population;
  for (const field of ['species_count', 'set_count', 'move_candidate_count', 'ability_candidate_count']) {
    if (matrix.candidate_population?.[field] !== candidatePopulation?.[field]) {
      found.push(`public-consequence matrix candidate population ${field} changed without disposition`);
    }
  }
  if (matrix.candidate_population?.item_source !== candidatePopulation?.item_source) {
    found.push('public-consequence matrix computed-item population route changed without disposition');
  }
  if (!identity || identity.source_tree_sha256 !== value.simulator?.source_tree_sha256
    || identity.move_candidate_sha256 !== closure?.move_candidate_sha256
    || identity.ability_candidate_sha256 !== closure?.ability_candidate_sha256
    || identity.selector_source_sha256 !== closure?.selector_source_sha256) {
    found.push('public-consequence matrix source identity disagrees with pinned generator closure');
  }
  const expectedSourceFiles = [
    'data/random-battles/gen9/sets.json', 'data/random-battles/gen9/teams.ts',
    'data/moves.ts', 'data/abilities.ts', 'data/items.ts', 'data/conditions.ts', 'sim/battle-actions.ts', 'sim/pokemon.ts',
  ];
  if (!identity?.route_file_sha256 || Object.keys(identity.route_file_sha256).sort().join('|') !== [...expectedSourceFiles].sort().join('|')) {
    found.push('public-consequence matrix does not bind every callback/slot source file');
  } else {
    for (const file of expectedSourceFiles) {
      let digest;
      try { digest = sha256Text(fs.readFileSync(path.join(pkgRoot, file))); } catch { digest = null; }
      if (!digest || identity.route_file_sha256[file] !== digest) {
        found.push(`public-consequence source route changed without disposition: ${file}`);
      }
    }
  }

  const abilityContract = value.public_ability_effectiveness;
  const flagIDs = (flag) => dex ? dex.abilities.all().filter((ability) => ability.flags[flag]).map((ability) => ability.id).sort() : [];
  if (!dex || abilityContract?.schema_version !== 'public-ability-effectiveness/v1'
    || JSON.stringify(abilityContract.cantsuppress) !== JSON.stringify(flagIDs('cantsuppress'))
    || JSON.stringify(abilityContract.notransform) !== JSON.stringify(flagIDs('notransform'))) {
    found.push('public ability-effectiveness exemptions drifted from pinned source');
  }
  if (candidateIndex?.abilities?.has('neutralizinggas')) {
    found.push('new generated Neutralizing Gas root invalidates its no-route disposition');
  }
  const gasFlags = dex?.abilities?.get('neutralizinggas').flags;
  if (dex && (!gasFlags.notrace || !gasFlags.notransform || !gasFlags.noentrain || !gasFlags.failroleplay || !gasFlags.failskillswap || !gasFlags.noreceiver)) {
    found.push('Neutralizing Gas copy/transfer exclusion flags drifted');
  }

  const selectedSlots = [...(candidateIndex?.moves || [])]
    .map((id) => ({ move_id: id, slot_condition: dex?.moves?.get(id)?.slotCondition }))
    .filter((entry) => typeof entry.slot_condition === 'string')
    .map((entry) => ({ ...entry, slot_condition: entry.slot_condition.toLowerCase().replace(/[^a-z0-9]/g, '') }))
    .sort((a, b) => a.move_id.localeCompare(b.move_id));
  const expectedSlots = [
    { move_id: 'healingwish', slot_condition: 'healingwish' },
    { move_id: 'revivalblessing', slot_condition: 'revivalblessing' },
    { move_id: 'wish', slot_condition: 'wish' },
  ];
  if (JSON.stringify(selectedSlots) !== JSON.stringify(expectedSlots)
    || JSON.stringify(matrix.candidate_slot_roots) !== JSON.stringify(expectedSlots)) {
    found.push('public slot-condition roots changed without source disposition');
  }
  for (const id of ['futuresight', 'lunardance', 'doomdesire', 'metronome', 'copycat', 'mirrormove']) {
    const present = candidateIndex?.moves?.has(id) || false;
    const expectedPresent = id === 'futuresight';
    if (present !== expectedPresent) found.push(`public slot/copy route candidate ${id} changed without source disposition`);
  }
  const movesSource = fs.readFileSync(path.join(pkgRoot, 'data/moves.ts'), 'utf8');
  const actionsSource = fs.readFileSync(path.join(pkgRoot, 'sim/battle-actions.ts'), 'utf8');
  const abilitiesSource = fs.readFileSync(path.join(pkgRoot, 'data/abilities.ts'), 'utf8');
  for (const fragment of [
    "slotCondition: 'Wish'", "slotCondition: 'healingwish'", "slotCondition: 'revivalblessing'",
    "addSlotCondition(target, 'futuremove')", "slotCondition: 'lunardance'",
  ]) if (!movesSource.includes(fragment)) found.push(`public slot source route fragment is absent: ${fragment}`);
  const doomStart = movesSource.indexOf('\tdoomdesire: {');
  const doomEnd = movesSource.indexOf('\n\t},\n\t', doomStart + 1);
  if (doomStart < 0 || doomEnd < 0
    || !movesSource.slice(doomStart, doomEnd).includes("addSlotCondition(target, 'futuremove')")) {
    found.push('Doom Desire imperative futuremove route changed without disposition');
  }
  if (!actionsSource.includes("addSlotCondition(pokemon, 'healreplacement'")
    || !actionsSource.includes('runZPower(move: ActiveMove, pokemon: Pokemon)')) {
    found.push('Z-only healreplacement source route changed without disposition');
  }
  if (!abilitiesSource.includes('neutralizinggas:') || !abilitiesSource.includes('pokemon.abilityState.ending = false')) {
    found.push('Neutralizing Gas callback source route changed without disposition');
  }
  return found;
}

function reachabilityManifestErrors(value, candidateIndex, dex) {
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
  if (candidateIndex && dex) found.push(...generatorClosureErrors(reachability.generator_to_output_closure, candidateIndex, dex));
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

function computedAddVolatileDispositionErrors(value, candidateIndex, dex, auditText) {
  const found = [];
  const expected = [
    { key: 'data/moves.ts|volatile', family: 'Move.callback.addVolatile(computed)', disposition: 'source-proven-unreachable', reachability: 'unreachable-in-gen9randombattle-singles', known_values: ['dragoncheer', 'focusenergy', 'gmaxchistrike', 'laserfocus'], proof: 'B05', tests: ['tests/psych_up.test.ts', 'tests/simulator_coverage.test.ts'], projection: 'private crit-copy values; no generated Psych Up route' },
    { key: 'data/abilities.ts|volatile', family: 'Ability.callback.addVolatile(computed)', disposition: 'source-proven-unreachable', reachability: 'unreachable-in-gen9randombattle-singles', known_values: ['dragoncheer', 'focusenergy', 'gmaxchistrike', 'laserfocus'], proof: 'B06', tests: ['tests/ability_callback.test.ts', 'tests/simulator_coverage.test.ts'], projection: 'private ally-copy values; singles has no operative ally route' },
    { key: 'data/conditions.ts|effect.id', family: 'Condition.callback.addVolatile(computed)', disposition: 'finite-reachable-raw-only', reachability: 'finite-reachable', known_values: ['meteorbeam', 'solarbeam'], proof: 'B09', tests: ['tests/singlemove.test.ts', 'tests/simulator_coverage.test.ts'], projection: 'private charge markers; retain emitted public move and prepare records only' },
    { key: 'sim/battle-actions.ts|move.id', family: 'BattleActions.addVolatile(computed)', disposition: 'finite-reachable-raw-only', reachability: 'finite-reachable', known_values: ['bloodmoon', 'gigatonhammer'], proof: 'B11', tests: ['tests/repeat_use.test.ts', 'tests/simulator_coverage.test.ts'], projection: 'exact raw repeat-use hint; request remains action authority' },
    { key: 'sim/battle-actions.ts|moveData.volatileStatus', family: 'BattleActions.addVolatile(computed)', disposition: 'finite-reachable-inventory', reachability: 'finite-reachable', known_values: ['confusion', 'curse', 'destinybond', 'disable', 'encore', 'flinch', 'glaiverush', 'healblock', 'leechseed', 'lockedmove', 'magnetrise', 'mustrecharge', 'noretreat', 'partiallytrapped', 'protect', 'roost', 'saltcure', 'sparklingaria', 'substitute', 'taunt', 'yawn'], proof: 'B12', tests: ['tests/simulator_coverage.test.ts', 'tests/pipeline_integration.test.ts'], projection: 'use each existing effect inventory classification; never widen the output grammar' },
    { key: 'sim/pokemon.ts|linkedStatus', family: 'Pokemon.addLinkedStatus.addVolatile(computed)', disposition: 'finite-reachable-raw-only', reachability: 'finite-reachable', known_values: ['trapper'], proof: 'B13', tests: ['tests/spirit_shackle.test.ts', 'tests/simulator_coverage.test.ts'], projection: 'internal/raw linkage only; source, target, and counters stay private' },
  ];
  const rows = value.effect_discovery?.computed_add_volatile_calls || [];
  const actualCalls = new Set(rows.map((item) => `${item.source_file}|${item.argument}`));
  const expectedCalls = new Set(expected.map((item) => item.key));
  const unexpected = setDiff([...actualCalls], [...expectedCalls]);
  // Pokemon.copyVolatile is a separately classified, already represented family.
  if (unexpected.added.some((key) => key !== 'sim/pokemon.ts|volatile')
    || unexpected.removed.length) found.push(`Computed addVolatile disposition set drift: ${JSON.stringify(unexpected)}`);

  const inventory = effectInventoryItems(value);
  const classificationByValue = Object.fromEntries(inventory.map((item) => [item.id, item.classification]));
  const outputValues = candidateIndex && dex ? selectedMoveVolatileOutputValues(candidateIndex, dex) : null;
  const chargeValues = candidateIndex && dex ? selectedMoveValues(candidateIndex, dex).twoturnmove_effect_id : null;
  const repeatValues = candidateIndex && dex ? selectedMoveValues(candidateIndex, dex).cantusetwice : null;
  for (const rule of expected) {
    const item = rows.find((candidate) => `${candidate.source_file}|${candidate.argument}` === rule.key);
    if (!item) continue;
    for (const field of ['family', 'disposition', 'reachability', 'proof', 'projection', 'fail_closed_behavior']) {
      const expectedValue = field === 'fail_closed_behavior'
        ? 'Unknown or newly reachable computed emissions reject before projection and Python publication.'
        : field === 'proof' ? rule.proof : field === 'projection' ? rule.projection : rule[field];
      if (item[field] !== expectedValue) found.push(`Computed addVolatile ${rule.key} ${field} drifted from ${rule.proof}.`);
    }
    if (!Array.isArray(item.known_values) || JSON.stringify([...item.known_values].sort()) !== JSON.stringify(rule.known_values)) {
      found.push(`Computed addVolatile ${rule.key} finite/source values drifted from ${rule.proof}.`);
    }
    if (!Array.isArray(item.test_refs) || JSON.stringify([...item.test_refs].sort()) !== JSON.stringify([...rule.tests].sort())) {
      found.push(`Computed addVolatile ${rule.key} focused test evidence drifted from ${rule.proof}.`);
    }
    const auditRow = (auditText || '').split(/\r?\n/).find((line) => line.startsWith(`| ${rule.proof} |`));
    const columns = auditRow?.split('|').map((column) => column.trim()) || [];
    const expectedAuditValues = rule.key === 'sim/battle-actions.ts|moveData.volatileStatus'
      ? outputValues : rule.key === 'data/conditions.ts|effect.id' ? chargeValues
        : rule.key === 'sim/battle-actions.ts|move.id' ? repeatValues : rule.known_values;
    const auditValues = (columns[5] || '').split(',').map((part) => part.trim()).filter(Boolean);
    for (const [column, expectedValue] of [[2, rule.key.split('|')[0]], [3, rule.key.split('|')[1]], [4, rule.disposition]]) {
      if (columns[column] !== expectedValue) found.push(`Audit/manifest computed addVolatile disposition drift at ${rule.proof}.`);
    }
    if (!auditRow || JSON.stringify(auditValues) !== JSON.stringify(expectedAuditValues || rule.known_values)) {
      found.push(`Audit/manifest computed addVolatile value evidence drift at ${rule.proof}.`);
    }
    if (auditRow && !rule.tests.every((testRef) => auditRow.includes(testRef))) {
      found.push(`Audit/manifest computed addVolatile test evidence drift at ${rule.proof}.`);
    }
    if (auditRow && !auditRow.includes('Unknown or newly reachable computed emissions reject before projection and Python publication.')) {
      found.push(`Audit/manifest computed addVolatile fail-closed rule drift at ${rule.proof}.`);
    }
  }
  if (candidateIndex && dex) {
    if (candidateIndex.moves.has('psychup')) found.push('B05 no-route proof invalid: Psych Up entered the random move candidates.');
    if (candidateIndex.abilities.has('costar') || value.format_provenance?.effective_format?.game_type !== 'singles') {
      found.push('B06 no-route proof invalid: Costar or a multi-active format became operative.');
    }
    if (JSON.stringify(chargeValues) !== JSON.stringify(['meteorbeam', 'solarbeam'])) found.push('B09 charge-marker source values changed.');
    if (JSON.stringify(repeatValues) !== JSON.stringify(['bloodmoon', 'gigatonhammer'])) found.push('B11 repeat-use source values changed.');
    if (JSON.stringify(outputValues) !== JSON.stringify(['confusion', 'curse', 'destinybond', 'disable', 'encore', 'flinch', 'glaiverush', 'healblock', 'leechseed', 'lockedmove', 'magnetrise', 'mustrecharge', 'noretreat', 'partiallytrapped', 'protect', 'roost', 'saltcure', 'sparklingaria', 'substitute', 'taunt', 'yawn'])) {
      found.push('B12 move-hit/self/secondary source values changed.');
    }
  }
  const volatileRule = expected.find((rule) => rule.key === 'sim/battle-actions.ts|moveData.volatileStatus');
  const volatileItem = rows.find((item) => `${item.source_file}|${item.argument}` === volatileRule.key);
  if (volatileItem && JSON.stringify(volatileItem.classification_by_value || {}) !== JSON.stringify(
    Object.fromEntries([...volatileItem.known_values].sort().map((id) => [id, classificationByValue[id] || 'unclassified'])))) {
    found.push('B12 manifest classifications disagree with the existing effect inventory.');
  }
  return found;
}

function manifestErrors(value, candidateIndex, dex) {
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
    if (!['represented', 'raw-only', 'unknown fail closed at emitted protocol value', 'source-proven-unreachable', 'finite-reachable-raw-only', 'finite-reachable-inventory'].includes(item.disposition)) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} has no explicit disposition`);
    }
    if (item.disposition === 'represented' && (!Array.isArray(item.known_values) || !item.known_values.length || item.known_values.some((id) => !effectInventoryItems(value).some((entry) => entry.id === id && entry.classification === 'represented')))) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} lacks represented inventory values`);
    }
    if (['source-proven-unreachable', 'finite-reachable-raw-only', 'finite-reachable-inventory'].includes(item.disposition)
      && (!Array.isArray(item.known_values) || !item.known_values.length || !item.proof || !item.reachability || !item.projection
        || !item.fail_closed_behavior || !Array.isArray(item.test_refs) || !item.test_refs.length)) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} lacks source disposition, evidence, or fail-closed metadata`);
    }
    if (item.disposition === 'finite-reachable-inventory' && (!item.classification_by_value || typeof item.classification_by_value !== 'object')) {
      found.push(`computed addVolatile call ${item.source_file || '<missing>'}|${item.argument || '<missing>'} lacks per-value inventory classifications`);
    }
  }
  if (!effectDiscovery?.computed_add_volatile_calls?.length) found.push('effect discovery has no computed addVolatile call dispositions');
  const coverageAuditPath = path.resolve(root, '../docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md');
  let coverageAudit = '';
  try { coverageAudit = fs.readFileSync(coverageAuditPath, 'utf8'); } catch (error) { found.push(`Could not read closure audit for computed addVolatile disposition checks: ${error.message}`); }
  found.push(...computedAddVolatileDispositionErrors(value, candidateIndex, dex, coverageAudit));
  const reconciliation = value.review?.fce01_reconciliation;
  if (!reconciliation || reconciliation.schema_version !== 'fce-01-reconciliation/v1') {
    found.push('FCE-01 reconciliation matrix is missing or unsupported');
  } else {
    if (reconciliation.pinned_scope !== 'pokemon-showdown@0.11.10 gen9randombattle/gen9 singles random') {
      found.push('FCE-01 reconciliation matrix has an unpinned source/config scope');
    }
    const rows = reconciliation.rows;
    if (!Array.isArray(rows) || rows.length !== fce01Rows.length) {
      found.push('FCE-01 reconciliation matrix does not cover every C01-C30 row');
    } else {
      const rowIDs = rows.map((row) => row?.id).sort();
      if (JSON.stringify(rowIDs) !== JSON.stringify([...fce01Rows].sort())) {
        found.push('FCE-01 reconciliation matrix row IDs drift from C01-C30');
      }
      for (const row of rows) {
        for (const field of ['id', 'family', 'disposition', 'pinned_source_config', 'witness', 'typescript_python', 'privacy_restoration', 'records_agree']) {
          if (typeof row?.[field] !== 'string' || !row[field].trim()) found.push(`FCE-01 reconciliation ${row?.id || '<missing>'} lacks ${field}`);
        }
        if (typeof row?.source_backed !== 'boolean') found.push(`FCE-01 reconciliation ${row?.id || '<missing>'} lacks source_backed`);
        if (!['accepted-scoped', 'unresolved-reachable-or-source-proof'].includes(row?.disposition)) {
          found.push(`FCE-01 reconciliation ${row?.id || '<missing>'} has an invalid disposition`);
        }
        const isRequiredBlocker = fce01RequiredBlockers.has(row?.id);
        if (isRequiredBlocker && (row.disposition !== 'unresolved-reachable-or-source-proof' || row.source_backed !== false)) {
          found.push(`FCE-01 reconciliation ${row.id} promoted without its required aggregate source/lifecycle closure`);
        }
        if (row.disposition === 'accepted-scoped' && row.source_backed !== true) {
          found.push(`FCE-01 reconciliation ${row.id} acceptance is not source-backed`);
        }
        if (scopedRegistrations[row?.id]) {
          if (JSON.stringify(row.accepted_scope) !== JSON.stringify(scopedRegistrations[row.id])) {
            found.push(`FCE-01 ${row.id} accepted scope drifted or expanded`);
          }
        }
        if (row?.id === 'C22') {
          if (row.disposition !== 'accepted-scoped' || row.source_backed !== true) {
            found.push('FCE-01 C22 bounded callback registration must be accepted-scoped and source-backed');
          }
          for (const [field, fragments] of Object.entries(c22ScopedRequirements)) {
            for (const fragment of fragments) {
              if (typeof row[field] !== 'string' || !row[field].includes(fragment)) {
                found.push(`FCE-01 C22 scoped acceptance lacks ${field} evidence: ${fragment}`);
              }
            }
          }
        }
        if (row?.id === 'C23') {
          if (row.disposition !== 'accepted-scoped' || row.source_backed !== true) {
            found.push('FCE-01 C23 bounded slot-result registration must be accepted-scoped and source-backed');
          }
          for (const [field, fragments] of Object.entries(c23ScopedRequirements)) {
            for (const fragment of fragments) {
              if (typeof row[field] !== 'string' || !row[field].includes(fragment)) {
                found.push(`FCE-01 C23 scoped acceptance lacks ${field} evidence: ${fragment}`);
              }
            }
          }
        }
        if (!isRequiredBlocker && row.disposition === 'unresolved-reachable-or-source-proof') {
          found.push(`FCE-01 reconciliation ${row.id || '<missing>'} is an undocumented aggregate blocker`);
        }
      }
      const unresolved = rows.filter((row) => row.disposition === 'unresolved-reachable-or-source-proof');
      if (reconciliation.aggregate_disposition !== (unresolved.length ? 'blocked' : 'zero-unresolved')) {
        found.push('FCE-01 aggregate disposition does not match its unresolved rows');
      }
    }
  }
  for (const item of effectDiscovery?.special_values || []) {
    for (const field of ['id', 'source_file', 'projection_path', 'classification']) {
      if (typeof item[field] !== 'string' || !item[field].trim()) found.push(`special effect ${item.id || '<missing>'} missing ${field}`);
    }
    if (!Array.isArray(item.commands) || !item.commands.length || item.commands.some((command) => typeof command !== 'string' || !command.trim())) {
      found.push(`special effect ${item.id || '<missing>'} has no command scope`);
    }
    if (!validClassifications.has(item.classification)) found.push(`special effect ${item.id || '<missing>'} has invalid classification`);
  }
  found.push(...publicTypedStateLifecycleErrors(value, candidateIndex, dex));
  found.push(...publicConsequenceMatrixErrors(value, candidateIndex, dex));
  found.push(...publicItemEvidenceErrors(value));
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
  found.push(...reachabilityManifestErrors(value, candidateIndex, dex));
  return found;
}

function publicTypedStateLifecycleErrors(value, candidateIndex, dex) {
  const found = [];
  const contract = value.public_typed_state_lifecycle;
  const allowed = new Set(['evidence-derived-typed', 'raw-only', 'source-proven-unreachable', 'unsupported-fail-closed']);
  const expectedTypedSideIDs = ['auroraveil', 'lightscreen', 'reflect', 'spikes', 'stealthrock', 'stickyweb', 'tailwind', 'toxicspikes'];
  if (!contract || contract.schema_version !== 'public-typed-state-lifecycle/v1') {
    return ['public typed-state lifecycle contract is missing or unsupported'];
  }
  const source = contract.source_identity;
  if (source?.package !== 'pokemon-showdown' || source?.version !== value.simulator?.version
    || source?.format !== value.format_provenance?.effective_format?.id || source?.mod !== value.format?.mod
    || source?.game_type !== value.format?.game_type || source?.source_tree_sha256 !== value.simulator?.source_tree_sha256
    || source?.move_candidate_sha256 !== value.format_provenance?.generator_to_output_closure?.move_candidate_sha256) {
    found.push('public typed-state lifecycle source/config identity is not pinned to this manifest');
  }
  const inventory = effectInventoryItems(value).filter((item) => ['move_volatile', 'side_condition'].includes(item.category));
  const expectedKeys = inventory.map((item) => `${item.category}:${item.id}`).sort();
  const rows = contract.entries;
  if (!Array.isArray(rows)) return [...found, 'public typed-state lifecycle entries are missing'];
  const keys = rows.map((row) => `${row?.family}:${row?.id}`).sort();
  if (JSON.stringify(keys) !== JSON.stringify(expectedKeys) || new Set(keys).size !== keys.length) {
    found.push('public typed-state lifecycle matrix does not cover each current volatile and side-condition ID exactly once');
  }
  const rootedSides = new Set();
  for (const moveID of candidateIndex?.moves || []) {
    const move = dex.moves.get(moveID);
    for (const id of [move.sideCondition, move.self?.sideCondition, move.secondary?.sideCondition,
      ...(move.secondaries || []).map((secondary) => secondary.sideCondition)]) {
      if (typeof id === 'string' && id) rootedSides.add(String(id).toLowerCase().replace(/[^a-z0-9]/g, ''));
    }
  }
  const typedSides = [];
  const typedVolatiles = [];
  for (const row of rows) {
    const key = `${row?.family}:${row?.id}`;
    if (!allowed.has(row?.disposition)) found.push(`public typed-state lifecycle ${key} has an invalid disposition`);
    for (const field of ['start', 'reapply', 'ordinary_end', 'effect_specific_expiry', 'silent_removal',
      'transfer_copy', 'switch', 'drag', 'faint', 're_entry', 'replacement', 'terminal']) {
      if (typeof row?.[field] !== 'string' || !row[field].trim()) {
        found.push(`public typed-state lifecycle ${key} lacks ${field} semantics`);
      }
    }
    if (row?.cap !== null && (!Number.isSafeInteger(row?.cap) || row.cap < 1)) {
      found.push(`public typed-state lifecycle ${key} has an invalid typed cap`);
    }
    for (const field of ['equivalence_class', 'route', 'sources', 'tests', 'mode']) {
      const data = row?.[field];
      if (field === 'sources' || field === 'tests') {
        if (!Array.isArray(data) || !data.length) found.push(`public typed-state lifecycle ${key} lacks ${field}`);
      } else if (typeof data !== 'string' || !data.trim()) found.push(`public typed-state lifecycle ${key} lacks ${field}`);
    }
    if (row?.family === 'move_volatile') {
      const expectedDisposition = row.id === 'substitute' ? 'evidence-derived-typed' : 'raw-only';
      if (row.disposition !== expectedDisposition) {
        found.push(`volatile ${row.id} lifecycle classification drifted from its reviewed typed/raw-only boundary`);
      }
      if (row.disposition === 'evidence-derived-typed') typedVolatiles.push(row.id);
      if (row.id === 'substitute') {
        if (row.disposition !== 'evidence-derived-typed' || row.mode !== 'presence'
          || row.equivalence_class !== 'substitute-start-end-switch-clear-shed-tail-only-copy'
          || row.transfer !== 'only exact switch tag [from] Shed Tail copies Substitute to the entering active Pokémon; donor clears') {
          found.push('Substitute lifecycle must retain only the bounded typed Shed Tail transfer rule');
        }
      } else if (row.disposition === 'evidence-derived-typed') {
        found.push(`volatile ${row.id} was promoted without an effect-specific public lifecycle rule`);
      }
    } else if (row?.family === 'side_condition') {
      const expectedDisposition = expectedTypedSideIDs.includes(row.id)
        ? 'evidence-derived-typed' : 'unsupported-fail-closed';
      if (row.disposition !== expectedDisposition) {
        found.push(`side-condition ${row.id} lifecycle classification drifted from its reviewed typed/unsupported boundary`);
      }
      if (row.disposition === 'evidence-derived-typed') typedSides.push(row.id);
      if (rootedSides.has(row.id) !== (row.disposition === 'evidence-derived-typed')) {
        found.push(`side-condition ${row.id} typed disposition disagrees with generated random-set roots`);
      }
      if (row.disposition === 'evidence-derived-typed') {
        const expectedCap = ({ spikes: 3, toxicspikes: 2, stealthrock: 1, stickyweb: 1 })[row.id] || 1;
        if (row.cap !== expectedCap || !['presence', 'count'].includes(row.mode)
          || row.mode !== (expectedCap > 1 ? 'count' : 'presence')) {
          found.push(`side-condition ${row.id} has inconsistent public cap/mode`);
        }
      }
      if (row.disposition === 'raw-only' && rootedSides.has(row.id)) {
        found.push(`generated side-condition root ${row.id} was downgraded without an evidence-derived rule`);
      }
    }
  }
  if (JSON.stringify(typedVolatiles.sort()) !== JSON.stringify(['substitute'])) {
    found.push('public typed-state lifecycle volatile typed set must remain the bounded Substitute exception');
  }
  if (JSON.stringify(typedSides.sort()) !== JSON.stringify([...rootedSides].sort())) {
    found.push('public typed-state lifecycle side-condition typed set does not equal the generated direct-root set');
  }
  if (JSON.stringify([...rootedSides].sort()) !== JSON.stringify(expectedTypedSideIDs)) {
    found.push('generated side-condition roots changed without an effect-specific lifecycle review');
  }
  if (JSON.stringify([...(contract.court_change_ids || [])].sort()) !== JSON.stringify(typedSides.sort())) {
    found.push('Court Change typed transfer set disagrees with evidence-derived side conditions');
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

for (const issue of manifestErrors(manifest, candidateIndex, dex)) errors.push(`Manifest incomplete: ${issue}`);

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
  tests.push(['digest-only update does not attest semantic review', manifestErrors(digestOnlyManifest, candidateIndex, dex).some((item) => item.includes('source digest is not bound'))]);
  const localDigestOnlyManifest = JSON.parse(JSON.stringify(manifest));
  localDigestOnlyManifest.local_coverage_sources.sha256 = '__new_unreviewed_digest__';
  tests.push(['local digest-only update does not attest semantic review', manifestErrors(localDigestOnlyManifest, candidateIndex, dex).some((item) => item.includes('local coverage sources are not bound'))]);
  const missingFce01Matrix = JSON.parse(JSON.stringify(manifest));
  delete missingFce01Matrix.review.fce01_reconciliation;
  tests.push(['missing FCE-01 reconciliation matrix fails closed', manifestErrors(missingFce01Matrix, candidateIndex, dex)
    .some((item) => item.includes('FCE-01 reconciliation matrix is missing'))]);
  const unsupportedC23Scope = JSON.parse(JSON.stringify(manifest));
  unsupportedC23Scope.review.fce01_reconciliation.rows.find((row) => row.id === 'C23').typescript_python =
    'Slot outcomes accepted without health/status/faint representation or terminal owner/action authority.';
  tests.push(['C23 acceptance without enumerated result and terminal authority scope fails closed',
    manifestErrors(unsupportedC23Scope, candidateIndex, dex)
      .some((item) => item.includes('FCE-01 C23 scoped acceptance lacks typescript_python evidence'))]);
  const falseC23Closure = JSON.parse(JSON.stringify(manifest));
  const falseC23Row = falseC23Closure.review.fce01_reconciliation.rows.find((row) => row.id === 'C23');
  falseC23Row.disposition = 'unresolved-reachable-or-source-proof';
  falseC23Row.source_backed = false;
  tests.push(['C23 accepted semantic scope cannot be registered as unresolved or false-closed',
    manifestErrors(falseC23Closure, candidateIndex, dex)
      .some((item) => item.includes('FCE-01 C23 bounded slot-result registration must be accepted-scoped and source-backed'))]);
  const missingConsequenceMatrix = JSON.parse(JSON.stringify(manifest));
  delete missingConsequenceMatrix.public_consequence_matrix;
  tests.push(['missing public-consequence matrix fails closed', manifestErrors(missingConsequenceMatrix, candidateIndex, dex)
    .some((item) => item.includes('public-consequence matrix is missing'))]);
  const changedConsequenceCategory = JSON.parse(JSON.stringify(manifest));
  changedConsequenceCategory.public_consequence_matrix.rows.find((row) => row.id === 'wish-resolution').category = 'raw';
  tests.push(['slot consequence category drift fails closed', manifestErrors(changedConsequenceCategory, candidateIndex, dex)
    .some((item) => item.includes('wish-resolution changed its source disposition'))]);
  tests.push(['new generated slot root fails closed', publicConsequenceMatrixErrors(manifest,
    { ...candidateIndex, moves: new Set([...candidateIndex.moves, 'lunardance']) }, dex)
    .some((item) => item.includes('public slot-condition roots changed') || item.includes('candidate lunardance changed'))]);
  const changedAbilityExemptions = JSON.parse(JSON.stringify(manifest));
  changedAbilityExemptions.public_ability_effectiveness.cantsuppress = [];
  tests.push(['ability suppression exemption drift fails closed', manifestErrors(changedAbilityExemptions, candidateIndex, dex)
    .some((item) => item.includes('ability-effectiveness exemptions drifted'))]);
  tests.push(['new generated Gas seed fails closed', publicConsequenceMatrixErrors(manifest,
    { ...candidateIndex, abilities: new Set([...candidateIndex.abilities, 'neutralizinggas']) }, dex)
    .some((item) => item.includes('Neutralizing Gas root'))]);
  for (const field of ['opponent_presence', 'unknown', 'absence', 'suppression', 'terminal_identity', 'terminal_privacy', 'historical_carrier', 'incoming_terminal', 'private_restoration']) {
    const changedItemEvidence = JSON.parse(JSON.stringify(manifest));
    changedItemEvidence.public_item_evidence[field] = '__unreviewed_item_or_identity_rule__';
    tests.push([`item/terminal ${field} drift fails closed`, publicItemEvidenceErrors(changedItemEvidence)
      .some((item) => item.includes(`${field} drifted`))]);
  }
  const missingItemMatrixSource = JSON.parse(JSON.stringify(manifest));
  missingItemMatrixSource.local_coverage_sources.files = missingItemMatrixSource.local_coverage_sources.files.filter((file) => file !== 'tests/item_identity.test.ts');
  tests.push(['item/terminal matrix source omission fails closed', publicItemEvidenceErrors(missingItemMatrixSource)
    .some((item) => item.includes('source is not coverage-bound'))]);
  const changedCallbackSourceDigest = JSON.parse(JSON.stringify(manifest));
  changedCallbackSourceDigest.public_consequence_matrix.source_identity.route_file_sha256['data/items.ts'] = '__unreviewed_callback_route__';
  tests.push(['callback route source digest drift fails closed', manifestErrors(changedCallbackSourceDigest, candidateIndex, dex)
    .some((item) => item.includes('public-consequence source route changed'))]);
  const falselyClosedFce01 = JSON.parse(JSON.stringify(manifest));
  falselyClosedFce01.review.fce01_reconciliation.aggregate_disposition = 'blocked';
  tests.push(['FCE-01 aggregate disposition cannot hide resolved/unresolved drift', manifestErrors(falselyClosedFce01, candidateIndex, dex)
    .some((item) => item.includes('FCE-01 aggregate disposition does not match'))]);
  const missingLifecycleEntry = JSON.parse(JSON.stringify(manifest));
  missingLifecycleEntry.public_typed_state_lifecycle.entries.pop();
  tests.push(['missing typed lifecycle ID fails closed', manifestErrors(missingLifecycleEntry, candidateIndex, dex)
    .some((item) => item.includes('matrix does not cover each current volatile and side-condition ID'))]);
  const missingLifecycleSemantics = JSON.parse(JSON.stringify(manifest));
  delete missingLifecycleSemantics.public_typed_state_lifecycle.entries
    .find((item) => item.id === 'confusion' && item.family === 'move_volatile').terminal;
  tests.push(['missing lifecycle class semantics fail closed', manifestErrors(missingLifecycleSemantics, candidateIndex, dex)
    .some((item) => item.includes('move_volatile:confusion lacks terminal semantics'))]);
  const falselyTypedVolatile = JSON.parse(JSON.stringify(manifest));
  falselyTypedVolatile.public_typed_state_lifecycle.entries.find((item) => item.id === 'confusion' && item.family === 'move_volatile').disposition = 'evidence-derived-typed';
  tests.push(['volatile lifecycle promotion without effect-specific evidence fails closed', manifestErrors(falselyTypedVolatile, candidateIndex, dex)
    .some((item) => item.includes('volatile confusion was promoted'))]);
  const changedVolatileClassification = JSON.parse(JSON.stringify(manifest));
  changedVolatileClassification.public_typed_state_lifecycle.entries
    .find((item) => item.id === 'confusion' && item.family === 'move_volatile').disposition = 'unsupported-fail-closed';
  tests.push(['raw-only volatile classification drift fails closed', manifestErrors(changedVolatileClassification, candidateIndex, dex)
    .some((item) => item.includes('volatile confusion lifecycle classification drifted'))]);
  const falselyTypedUnrootedSide = JSON.parse(JSON.stringify(manifest));
  falselyTypedUnrootedSide.public_typed_state_lifecycle.entries.find((item) => item.id === 'matblock' && item.family === 'side_condition').disposition = 'evidence-derived-typed';
  tests.push(['side lifecycle promotion without generated root fails closed', manifestErrors(falselyTypedUnrootedSide, candidateIndex, dex)
    .some((item) => item.includes('side-condition matblock typed disposition disagrees'))]);
  const changedSideClassification = JSON.parse(JSON.stringify(manifest));
  changedSideClassification.public_typed_state_lifecycle.entries
    .find((item) => item.id === 'matblock' && item.family === 'side_condition').disposition = 'raw-only';
  tests.push(['unsupported side-condition classification drift fails closed', manifestErrors(changedSideClassification, candidateIndex, dex)
    .some((item) => item.includes('side-condition matblock lifecycle classification drifted'))]);
  tests.push(['a new direct side-condition root fails closed', publicTypedStateLifecycleErrors(manifest,
    { ...candidateIndex, moves: new Set([...candidateIndex.moves, 'matblock']) }, dex)
    .some((item) => item.includes('generated side-condition roots changed'))]);
  for (const id of ['C22', 'C23']) {
    const expanded = JSON.parse(JSON.stringify(manifest));
    expanded.review.fce01_reconciliation.rows.find((row) => row.id === id).accepted_scope.push('generic-hidden-callback-inference');
    tests.push([`${id} unsupported scope expansion fails closed`, manifestErrors(expanded, candidateIndex, dex)
      .some((item) => item.includes(`FCE-01 ${id} accepted scope drifted or expanded`))]);
  }
  const inventedAcceptance = JSON.parse(JSON.stringify(manifest));
  inventedAcceptance.review.fce01_reconciliation.rows.find((row) => row.id === 'C22').source_backed = false;
  tests.push(['invented C22 acceptance fails closed', manifestErrors(inventedAcceptance, candidateIndex, dex)
    .some((item) => item.includes('C22 bounded callback registration must be accepted-scoped and source-backed'))]);
  const unsupportedC22 = JSON.parse(JSON.stringify(manifest));
  unsupportedC22.review.fce01_reconciliation.rows.find((row) => row.id === 'C22').typescript_python = 'all callbacks accepted';
  tests.push(['C22 acceptance without finite authority evidence fails closed', manifestErrors(unsupportedC22, candidateIndex, dex)
    .some((item) => item.includes('C22 scoped acceptance lacks typescript_python evidence'))]);
  const newlyTrustedComputedEffect = JSON.parse(JSON.stringify(manifest));
  newlyTrustedComputedEffect.effect_discovery.computed_add_volatile_calls[0].disposition = 'represented';
  newlyTrustedComputedEffect.effect_discovery.computed_add_volatile_calls[0].known_values = [];
  tests.push(['computed addVolatile represented disposition requires classified values', manifestErrors(newlyTrustedComputedEffect, candidateIndex, dex).some((item) => item.includes('lacks represented inventory values'))]);
  const computedAuditText = fs.readFileSync(path.resolve(root, '../docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md'), 'utf8');
  tests.push(['B05/B06/B09/B11/B12/B13 dispositions and evidence agree across source, manifest, audit, and tests',
    computedAddVolatileDispositionErrors(manifest, candidateIndex, dex, computedAuditText).length === 0]);
  const computedDispositionCases = [
    ['B05', (entry) => { entry.disposition = 'raw-only'; }],
    ['B06', (entry) => { entry.known_values.pop(); }],
    ['B09', (entry) => { entry.known_values.push('__new_charge_marker__'); }],
    ['B11', (entry) => { entry.test_refs = []; }],
    ['B12', (entry) => { delete entry.classification_by_value.flinch; }],
    ['B13', (entry) => { entry.fail_closed_behavior = 'accept unreviewed volatile'; }],
  ];
  for (const [proof, mutate] of computedDispositionCases) {
    const changed = JSON.parse(JSON.stringify(manifest));
    const row = changed.effect_discovery.computed_add_volatile_calls.find((entry) => entry.proof === proof);
    mutate(row);
    tests.push([`${proof} computed volatile disposition drift fails closed`,
      computedAddVolatileDispositionErrors(changed, candidateIndex, dex, computedAuditText).length > 0]);
  }
  for (const rule of manifest.effect_discovery.computed_add_volatile_calls.filter((item) => item.proof)) {
    const row = computedAuditText.split(/\r?\n/).find((line) => line.startsWith(`| ${rule.proof} |`));
    const changedDisposition = rule.disposition === 'source-proven-unreachable'
      ? 'finite-reachable-raw-only' : 'source-proven-unreachable';
    const driftedAudit = row
      ? computedAuditText.replace(row, row.replace(`| ${rule.disposition} |`, `| ${changedDisposition} |`))
      : computedAuditText;
    tests.push([`${rule.proof} computed volatile audit disposition drift fails closed`,
      computedAddVolatileDispositionErrors(manifest, candidateIndex, dex, driftedAudit)
        .some((issue) => issue.includes(`Audit/manifest computed addVolatile disposition drift at ${rule.proof}`))]);
  }
  tests.push(['B05/B06 no-route proof fails closed when direct candidate roots appear',
    computedAddVolatileDispositionErrors(manifest,
      { ...candidateIndex, moves: new Set([...candidateIndex.moves, 'psychup']) }, dex, computedAuditText)
      .some((issue) => issue.includes('B05 no-route proof invalid'))]);
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
  tests.push(['CE-03A generated candidates, finite values, selectors, and guards match the manifest',
    generatorClosureErrors(manifest.format_provenance?.generator_to_output_closure, candidateIndex, dex).length === 0]);
  const changedGeneratorCandidateManifest = JSON.parse(JSON.stringify(manifest.format_provenance?.generator_to_output_closure));
  changedGeneratorCandidateManifest.move_candidate_sha256 = '__unreviewed_direct_candidate_set__';
  tests.push(['CE-03A changed generated candidate set fails closed',
    generatorClosureErrors(changedGeneratorCandidateManifest, candidateIndex, dex).some((issue) => issue.includes('direct generated move candidates changed'))]);
  const changedGeneratorValuesManifest = JSON.parse(JSON.stringify(manifest.format_provenance?.generator_to_output_closure));
  changedGeneratorValuesManifest.finite_move_values.cantusetwice = [];
  tests.push(['CE-03A changed finite generated value fails closed',
    generatorClosureErrors(changedGeneratorValuesManifest, candidateIndex, dex).some((issue) => issue.includes('finite generated cantusetwice values changed'))]);
  const changedGeneratorGuardManifest = JSON.parse(JSON.stringify(manifest.format_provenance?.generator_to_output_closure));
  changedGeneratorGuardManifest.selector_source_fragments = ['__changed_isDoubles_guard__'];
  tests.push(['CE-03A changed item/ability format guard fails closed',
    generatorClosureErrors(changedGeneratorGuardManifest, candidateIndex, dex).some((issue) => issue.includes('selector/format guard is absent'))]);
  const representativeForms = [
    { id: 'candidate:bodypress', classification: 'direct_reachable' },
    { id: 'callback:magicbounce-reflection', classification: 'indirect_reachable' },
    { id: 'condition:dynamax', classification: 'package_wide_only' },
    { id: 'protocol:-singleturn', classification: 'raw_only' },
    { id: 'protocol:-singlemove', classification: 'raw_only' },
    { id: 'protocol:-singlemove-unsupported-form', classification: 'unsupported_stop' },
    { id: 'computed:addVolatile-unresolved', classification: 'unknown' },
  ];
  const expectedRoutes = ['candidate_path', 'callback_path', 'out_of_scope', 'preserve_raw', 'preserve_raw', 'stop', 'stop'];
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
