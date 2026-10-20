'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {createHash} = require('node:crypto');
const {execFileSync} = require('node:child_process');
const [source, commit, destination] = process.argv.slice(2);
if (!source || !/^[a-f0-9]{40}$/.test(commit || '') || !destination) throw new Error('Expected checkout, full commit, destination');
const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'showdown-pack-'));
const hash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function copy(relative) {
  const input = path.join(source, relative);
  if (fs.statSync(input).isDirectory()) {
    for (const name of fs.readdirSync(input).sort()) copy(relative + '/' + name);
  } else if (!relative.endsWith('.map')) {
    fs.mkdirSync(path.dirname(path.join(stage, relative)), {recursive: true});
    fs.copyFileSync(input, path.join(stage, relative));
  }
}
for (const name of ['dist/sim', 'dist/data', 'dist/lib', 'dist/config/formats.js', 'LICENSE']) copy(name);
// Existing finite Trace checks inspect the same raw set input as the generator.
copy('data/random-battles/gen9/sets.json');
// Python action/tactical featurizers parse these source tables at runtime.
copy('data/moves.ts');
copy('data/pokedex.ts');
copy('data/items.ts');
// Finite source-exclusion tests inspect these exact simulator source routes.
copy('data/random-battles/gen9/teams.ts');
copy('data/abilities.ts');
copy('sim/pokemon.ts');
const upstream = JSON.parse(fs.readFileSync(path.join(source, 'package.json'), 'utf8'));
const lock = JSON.parse(fs.readFileSync(path.join(source, 'package-lock.json'), 'utf8'));
const pkg = {name: upstream.name, version: upstream.version, main: upstream.main, types: upstream.types,
  license: upstream.license, engine_commit: commit,
  dependencies: {'ts-chacha20': lock.packages['node_modules/ts-chacha20'].version}};
fs.writeFileSync(path.join(stage, 'package.json'), JSON.stringify(pkg, null, 2) + '\n');
const files = {};
function inventory(dir) {
  for (const name of fs.readdirSync(path.join(stage, dir)).sort()) {
    const relative = dir ? dir + '/' + name : name;
    if (fs.statSync(path.join(stage, relative)).isDirectory()) inventory(relative);
    else files[relative] = hash(path.join(stage, relative));
  }
}
inventory('');
fs.writeFileSync(path.join(stage, 'engine-files.json'), JSON.stringify({engine_commit: commit, files}, null, 2) + '\n');
fs.mkdirSync(destination, {recursive: true});
// npm's tar writer fixes timestamps and modes, independent of checkout timestamps.
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const result = JSON.parse(execFileSync(npm, ['pack', '--ignore-scripts', '--json'],
  {cwd: stage, encoding: 'utf8', shell: process.platform === 'win32'}));
const target = path.join(destination, `pokemon-showdown-${commit.slice(0, 8)}.tgz`);
fs.copyFileSync(path.join(stage, result[0].filename), target);
console.log(JSON.stringify({file: target, integrity: result[0].integrity, manifest_sha256: hash(path.join(stage, 'engine-files.json')), size: result[0].size}));
