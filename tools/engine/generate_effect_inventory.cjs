'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const ts = require(path.join(root, 'sim-core/node_modules/typescript'));
const hash = value => createHash('sha256').update(value).digest('hex');
const id = value => value.toLowerCase().replace(/[^a-z0-9]/g, '');
const read = file => fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
const fields = {volatileStatus:'move_volatile', sideCondition:'side_condition', slotCondition:'internal_effect',
  pseudoWeather:'pseudo_weather', terrain:'terrain', weather:'weather'};

// Source units include the whole declaring callback, rather than just the add()
// line: changing guards, arguments or cleanup must invalidate inherited review.
function scan(directory) {
  const units = new Map(), categories = new Map(), files = [], lifecycle = new Map();
  function add(effect, key, text, category) {
    effect = id(effect); if (!effect) return;
    if (!units.has(effect)) units.set(effect, new Map());
    units.get(effect).set(key, text);
    if (category) categories.set(effect, category);
  }
  function walk(dir) {
    for (const entry of fs.readdirSync(path.join(directory, dir), {withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))) {
      const file = `${dir}/${entry.name}`;
      if (entry.isDirectory()) walk(file);
      else if (entry.name.endsWith('.ts') || entry.name.endsWith('.json')) files.push(file);
    }
  }
  walk('sim'); walk('data');
  // Gen9 inherits base data, with only gen9 overrides. Older generations, CAP
  // and custom mods are scanned in the tree digest but are not active emitters.
  for (const file of files.filter(f=>f.endsWith('.ts') && (!f.startsWith('data/') || /^data\/[^/]+\.ts$/.test(f) || f.startsWith('data/mods/gen9/')))) {
    const source = ts.createSourceFile(file, read(path.join(directory,file)), ts.ScriptTarget.Latest, true);
    function visit(node, owner, ownerId, unit) {
      const name = node.name && (ts.isIdentifier(node.name) || ts.isStringLiteral(node.name)) ? node.name.text : null;
      if (ts.isVariableDeclaration(node) && ['Moves','Abilities','Items','Conditions','Rulesets'].includes(name)) owner = name;
      if (owner && ts.isPropertyAssignment(node) && ts.isObjectLiteralExpression(node.initializer)
          && node.parent.parent && ts.isVariableDeclaration(node.parent.parent)) ownerId = name;
      if (ts.isMethodDeclaration(node) || ts.isFunctionDeclaration(node)) unit = node;
      if (ts.isMethodDeclaration(node) && ['sim/pokemon.ts','sim/side.ts','sim/field.ts'].includes(file)
          && ['addVolatile','removeVolatile','clearVolatile','copyVolatileFrom','addSideCondition','removeSideCondition',
            'setWeather','clearWeather','setTerrain','clearTerrain','addPseudoWeather','removePseudoWeather'].includes(name)) {
        lifecycle.set(`${file}:${name}`,node.getText(source));
      }
      if (ownerId && ts.isPropertyAssignment(node) && name === 'condition') {
        add(ownerId, `${file}:${owner}.${ownerId}.condition`, node.getText(source), owner==='Conditions'?'move_volatile':undefined);
      }
      if (owner === 'Conditions' && ownerId && ts.isPropertyAssignment(node) && name === ownerId) {
        add(ownerId, `${file}:Conditions.${ownerId}`, node.getText(source));
      }
      const key = `${file}:${owner || 'core'}.${ownerId || ''}.${unit?.name?.getText(source) || name || 'value'}`;
      if (ts.isPropertyAssignment(node) && fields[name] && ts.isStringLiteral(node.initializer)) {
        add(node.initializer.text, key, (unit || node).getText(source), fields[name]);
      }
      if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
        const method = node.expression.name.text;
        const literal = node.arguments[0];
        if (literal && ts.isStringLiteral(literal)) {
          if (['addVolatile','removeVolatile','addSideCondition','removeSideCondition','setWeather','clearWeather','setTerrain','addPseudoWeather','removePseudoWeather'].includes(method)) {
            add(literal.text, key, (unit || node).getText(source), method.includes('SideCondition')?'side_condition':method.includes('Weather')?'weather':method==='setTerrain'?'terrain':method.includes('PseudoWeather')?'pseudo_weather':'move_volatile');
          }
          if (method === 'add' && ['-start','-end','-sidestart','-sideend','-weather','-fieldstart','-fieldend'].includes(literal.text)) {
            const index = ['-weather','-fieldstart','-fieldend'].includes(literal.text) ? 1 : 2;
            const value = node.arguments[index];
            if (value && ts.isStringLiteral(value)) {
              add(value.text.replace(/^(move|ability|item):\s*/i,''),key,(unit || node).getText(source));
            } else if (ownerId) add(ownerId,key,(unit || node).getText(source));
          }
        }
      }
      ts.forEachChild(node, child=>visit(child,owner,ownerId,unit));
    }
    visit(source);
  }
  return {units, categories, lifecycle, source_sha256: hash(files.map(file=>`${file}\0${read(path.join(directory,file))}\0`).join(''))};
}

function generate({source, historical, check=false}) {
  if (!source || !historical) throw new Error('Required: --source=<full b8f23c99 checkout> --historical-source=<unpacked npm 0.11.10>');
  source=path.resolve(source);historical=path.resolve(historical);
  const commit = execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
  if (commit !== 'b8f23c99629132611ba59e99480cb148ea8c5d3d') throw new Error('Wrong engine commit');
  if (execFileSync('git',['-C',source,'status','--porcelain','--untracked-files=no'],{encoding:'utf8'}).trim()) throw new Error('Modified engine source');
  const old = JSON.parse(read(path.join(root,'sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json')));
  for(const top of ['sim','data']) {
    const digest=createHash('sha256');
    function visit(dir) {
      for(const entry of fs.readdirSync(path.join(historical,dir),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))) {
        const relative=`${dir}/${entry.name}`;
        if(entry.isDirectory())visit(relative);
        else if(/\.(ts|json|js)$/.test(entry.name))digest.update(relative).update('\0').update(fs.readFileSync(path.join(historical,relative))).update('\0');
      }
    }
    visit(top);
    if(digest.digest('hex')!==old.simulator.source_root_sha256[top])throw new Error('Historical source tree mismatch: '+top);
  }
  // Verify the historical comparison roots against their reviewed digests.
  for (const file of ['data/moves.ts','data/abilities.ts','data/items.ts','data/conditions.ts','sim/pokemon.ts','sim/battle-actions.ts']) {
    const expected = old.public_consequence_matrix.source_identity.route_file_sha256[file];
    if (hash(read(path.join(historical,file))) !== expected) throw new Error('Historical source mismatch: '+file);
  }
  const before = scan(historical), after = scan(source);
  // Dynamic finite public values have their own inventory IDs. They inherit no
  // review merely because the generating callback already existed historically.
  const dynamic = new Map();
  const {Dex} = require(path.join(source,'dist/sim/dex.js'));
  const dex = Dex.mod('gen9'); dex.includeData();
  for(const move of dex.moves.all()) if(move.volatileStatus==='partiallytrapped') dynamic.set(move.id,'partiallytrapped');
  for(let count=1;count<=5;count++)dynamic.set(`fallen${count}`,'supremeoverlord');
  for(const [effect,emitter] of dynamic) {
    for(const data of [before,after])data.units.set(effect,data.units.get(emitter)||new Map());
    after.categories.set(effect,'move_volatile');
  }
  const value = structuredClone(old);
  value.simulator = {...old.simulator,version:'0.11.11',source_commit:commit,source_tree_sha256:after.source_sha256,
    source_roots:['sim','data'],source_root_sha256:undefined,reviewed_source_tree_sha256:undefined,
    package_declaration:'sim-core/package.json commit-pinned file dependency', installed_metadata:'Full Git source checkout',
    source_commit_note:'Full clean source checkout; per-effect source comparison below. Historical review is inherited for identical units or exact reviewed change classes.'};
  const entries = [...value.condition_inventory,...value.effect_discovery.additional_entries];
  const known = new Set(entries.map(e=>e.id));
  const reviewedIds = new Set([...known,...old.effect_discovery.special_values.map(e=>e.id)]);
  for (const [effect,category] of after.categories) if (!known.has(effect)) {
    value.effect_discovery.additional_entries.push({id:effect,category,classification:'unsupported-fail-closed',
      review_status:'unreviewed-new-inventory-id',semantics_ref:category,
      source_symbols:[...after.units.get(effect).keys()],source_files:[...new Set([...after.units.get(effect).keys()].map(k=>k.split(':')[0]))]});
    known.add(effect);
  }
  const all = [...value.condition_inventory,...value.effect_discovery.additional_entries];
  const special = value.effect_discovery.special_values;
  for (const row of special) {
    const base = row.id.replace(/(?:atk|def|spa|spd|spe)$/,'');
    const alias = base !== row.id && ['quarkdrive','protosynthesis'].includes(base) ? base : row.id === 'movefuturesight' ? 'futuremove' : null;
    if(alias) for(const data of [before,after]) data.units.set(row.id,new Map([
      ...(data.units.get(alias)||[]),...(row.id==='movefuturesight'?(data.units.get('futuresight')||[]):[])]));
  }
  const comparison = [];
  const shared = [...new Set([...before.lifecycle.keys(),...after.lifecycle.keys()])].sort().map(key=>({
    source:key,before:before.lifecycle.get(key)??null,after:after.lifecycle.get(key)??null}));
  for (const effect of [...new Set([...all.map(e=>e.id),...special.map(e=>e.id)])].sort()) {
    const a = new Map(before.units.get(effect) || []), b = new Map(after.units.get(effect) || []);
    const category = all.find(e=>e.id===effect)?.category || 'special_value';
    const relevant = key => category==='side_condition' ? key.startsWith('sim/side.ts:')
      : ['move_volatile','internal_effect'].includes(category) ? key.startsWith('sim/pokemon.ts:')
      : category==='weather' ? /:(setWeather|clearWeather)$/.test(key)
      : category==='terrain' ? /:(setTerrain|clearTerrain)$/.test(key)
      : category==='pseudo_weather' ? /:(addPseudoWeather|removePseudoWeather)$/.test(key) : false;
    const shared_changes = shared.filter(d=>relevant(d.source)&&d.before!==d.after).map(d=>d.source);
    for(const d of shared.filter(d=>relevant(d.source))) {
      if(d.before!==null)a.set(d.source,d.before);if(d.after!==null)b.set(d.source,d.after);
    }
    const differences = [...new Set([...a.keys(),...b.keys()])].sort().filter(k=>a.get(k)!==b.get(k)).map(key=>({
      source:key,...(shared_changes.includes(key)?{shared_lifecycle_diff:key}:{before:a.get(key)??null,after:b.get(key)??null})}));
    const status = !reviewedIds.has(effect) || !before.units.get(effect)?.size ? 'new' : differences.length || !after.units.get(effect)?.size ? 'changed' : 'unchanged';
    comparison.push({id:effect,category,status,
      before_sha256:hash(JSON.stringify([...a].sort())),after_sha256:hash(JSON.stringify([...b].sort())),differences});
    if (status !== 'unchanged') {
      for (const row of all.filter(e=>e.id===effect)) row.classification='unsupported-fail-closed';
      for (const row of special.filter(e=>e.id===effect)) row.classification='unsupported-fail-closed';
      for (const row of value.public_typed_state_lifecycle.entries.filter(e=>e.id===effect)) row.disposition='unsupported-fail-closed';
    }
  }
  value.effect_source_comparison = {schema_version:'effect-source-comparison/v1',historical_source_sha256:before.source_sha256,
    source_sha256:after.source_sha256,scope:'Exact declaring callbacks, literal emitters and shared lifecycle methods in full sim/data source; no reachability promotion',
    shared_lifecycle:shared,entries:comparison};
  const reviews=JSON.parse(read(path.join(__dirname,'effect_class_reviews.json')));
  if(reviews.engine_commit!==commit)throw new Error('Class reviews require the reviewed engine commit');
  const approved=new Map(reviews.class_review.flatMap(c=>c.units.map(u=>[u.source,{...u,class:c.class}])));
  const matches=d=>{
    if(d.shared_lifecycle_diff)d=shared.find(s=>s.source===d.shared_lifecycle_diff);
    const reviewed=approved.get(d.source);
    return reviewed && reviewed.before_sha256===hash(d.before||'') && reviewed.after_sha256===hash(d.after||'');
  };
  const historicalRows=[...old.condition_inventory,...old.effect_discovery.additional_entries];
  for(const entry of comparison) {
    const solelyShared=entry.differences.every(d=>d.shared_lifecycle_diff);
    if(entry.status==='changed' && (solelyShared || reviews.semantic_ids.includes(entry.id)) && entry.differences.every(matches)) {
      entry.adoption='reviewed-class';
      for(const row of all.filter(r=>r.id===entry.id))Object.assign(row,{classification:historicalRows.find(r=>r.id===entry.id).classification,review_status:'class-reviewed'});
      for(const row of special.filter(r=>r.id===entry.id))row.classification=old.effect_discovery.special_values.find(r=>r.id===entry.id).classification;
      for(const row of value.public_typed_state_lifecycle.entries.filter(r=>r.id===entry.id))row.disposition=old.public_typed_state_lifecycle.entries.find(r=>r.id===entry.id&&r.family===row.family).disposition;
    } else if(entry.status!=='unchanged')entry.blocked_reason='Unreviewed source delta';
  }
  // Newly inventoried values expose public hints/results, never their private
  // binding source, turn counter or Supreme Overlord multiplier.
  for(const row of all.filter(r=>comparison.some(e=>e.id===r.id&&e.status==='new'))) {
    const entry=comparison.find(e=>e.id===row.id);
    const reviewed=reviews.new_ids.find(r=>r.id===row.id);
    if(!reviewed || reviewed.before_sha256!==entry.before_sha256 || reviewed.after_sha256!==entry.after_sha256)continue;
    row.classification='raw-only';row.review_status='reviewed-new-public-evidence';
    const lifecycle={...structuredClone(old.public_typed_state_lifecycle.entries.find(e=>e.id==='partiallytrapped')),
      id:row.id,disposition:'raw-only',tests:['sim-core/tests/effect_change_classes.test.ts']};
    const existing=value.public_typed_state_lifecycle.entries.find(e=>e.id===row.id);
    if(existing)Object.assign(existing,lifecycle);else value.public_typed_state_lifecycle.entries.push(lifecycle);
    entry.adoption='reviewed-new-raw-only';delete entry.blocked_reason;
  }
  for(const review of reviews.ability_state_reviews || []) {
    const entry=comparison.find(e=>e.id===review.id);
    if(!entry || entry.before_sha256!==review.before_sha256 || entry.after_sha256!==review.after_sha256)throw new Error('Ability state review source mismatch');
    const row=all.find(r=>r.id===review.id);
    Object.assign(row,{category:'ability_state',classification:'represented',review_status:'per-ID-semantic-reviewed'});
    value.public_typed_state_lifecycle.entries=value.public_typed_state_lifecycle.entries.filter(e=>e.id!==review.id);
    value.public_typed_state_lifecycle.entries.push({id:review.id,family:'ability_state',disposition:'evidence-derived-typed',mode:'presence',semantics:review.semantics,tests:review.tests});
    entry.category='ability_state';entry.adoption='per-ID-semantic-reviewed';delete entry.blocked_reason;
  }
  value.ability_state_reviews=reviews.ability_state_reviews;
  value.class_review=reviews.class_review;
  // Matrices remain historical evidence; explicitly annotate their per-ID adoption
  // rather than silently presenting their old provenance as native proof.
  for(const group of Object.values(value.condition_semantics)) group.native_source_comparison='effect_source_comparison.entries; unchanged or class-reviewed IDs inherit this historical semantic review';
  for (const key of ['format_provenance','public_typed_state_lifecycle','public_consequence_matrix','public_ability_effectiveness','public_item_evidence']) {
    value[key] = {...value[key],native_source_comparison:'effect_source_comparison.entries; unreviewed deltas unsupported-fail-closed; class_review names adopted changes; other claims remain historical only'};
  }
  if(!value.local_coverage_sources.files.includes('../docs/contracts/OBSERVABLE_STATE.md'))value.local_coverage_sources.files.push('../docs/contracts/OBSERVABLE_STATE.md');
  for (const file of ['src/engine_seed.ts','src/owned_request_moves.ts','tests/owned_request_moves.test.ts','tests/replay_session.test.ts','tests/switch_sources.test.ts','tests/switch_publication.test.ts','tests/drag_sources.test.ts','tests/revival_terminal_health.test.ts']) if (!value.local_coverage_sources.files.includes(file)) value.local_coverage_sources.files.push(file);
  const localHash=require('node:crypto').createHash('sha256');
  for(const name of [...value.local_coverage_sources.files].sort()) {
    const bytes=fs.readFileSync(path.resolve(root,'sim-core',name)), text=bytes.toString('utf8');
    if(!Buffer.from(text,'utf8').equals(bytes))throw new Error('Invalid UTF-8 local coverage source: '+name);
    localHash.update(name).update('\0').update(text.replace(/\r\n/g,'\n')).update('\0');
  }
  value.local_coverage_sources.sha256=localHash.digest('hex');
  value.local_coverage_sources.native_digest_scope='Current local bytes only; historical semantic review digest is retained separately';
  value.review_status='source-compared-with-fail-closed-deltas';
  const output=path.join(root,'sim-core/simulator_coverage/pokemon-showdown-b8f23c99-gen9randombattle.json');
  const bytes=JSON.stringify(value)+'\n';
  if(check) {if(read(output)!==bytes)throw new Error('Generated effect inventory differs');} else fs.writeFileSync(output,bytes);
  const summary={};for(const e of comparison){const counts=summary[e.category]??={unchanged:0,changed:0,new:0};counts[e.status]++;}
  console.log(JSON.stringify({sha256:hash(bytes),summary,blocked:comparison.filter(e=>e.blocked_reason).map(e=>e.id)}));
  return value;
}
module.exports={generate};
if(require.main===module) {
  const option=name=>process.argv.find(a=>a.startsWith(`--${name}=`))?.slice(name.length+3);
  generate({source:option('source'),historical:option('historical-source'),check:process.argv.includes('--check')});
}
