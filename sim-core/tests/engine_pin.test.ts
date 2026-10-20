import assert from 'node:assert/strict';
import test from 'node:test';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {installedNativeProfile, NATIVE_ENGINE_COMMIT, NATIVE_ENGINE_INTEGRITY} from '../src/version_profile';

test('P0.4 installed native runtime has the commit and vendored integrity', () => {
  const runtime = installedNativeProfile();
  assert.equal(runtime.engine_commit, NATIVE_ENGINE_COMMIT);
  assert.equal(runtime.integrity, NATIVE_ENGINE_INTEGRITY);
  assert.equal(runtime.reader.profile.id, 'native11');
});

// Child-local filesystem views leave the shared install untouched, including under parallel tests.
function rejectView(mode: string, expected: string): void {
  const script = `
    const fs = require('node:fs'), assert = require('node:assert/strict');
    const {installedNativeProfile} = require('./dist/src/version_profile');
    const read = fs.readFileSync, list = fs.readdirSync;
    fs.readFileSync = function(file, options) {
      const name = String(file).replaceAll('\\\\', '/');
      let value = read.call(this, file, options);
      if (${JSON.stringify(mode)} === 'npm' && name.endsWith('/pokemon-showdown/package.json')) {
        const pkg = JSON.parse(value); delete pkg.engine_commit;
        pkg.gitHead = '739a5e1fee432ad80ff7136d70cca993be358b59';
        value = JSON.stringify(pkg);
      }
      if (${JSON.stringify(mode)} === 'bytes' && name.endsWith('/pokemon-showdown/dist/sim/battle.js')) value = Buffer.concat([Buffer.from(value), Buffer.from('\\n// altered')]);
      if (${JSON.stringify(mode)} === 'lock' && name.endsWith('/node_modules/.package-lock.json')) {
        const lock = JSON.parse(value); lock.packages['node_modules/pokemon-showdown'].integrity = 'sha512-npm-release'; value = JSON.stringify(lock);
      }
      return value;
    };
    fs.readdirSync = function(dir, options) {
      const names = list.call(this, dir, options);
      if (${JSON.stringify(mode)} === 'extra' && String(dir).replaceAll('\\\\', '/').endsWith('/pokemon-showdown/dist/config')) names.push('custom-formats.js');
      return names;
    };
    const stat = fs.lstatSync;
    fs.lstatSync = function(file, ...args) {
      if (${JSON.stringify(mode)} === 'extra' && String(file).endsWith('custom-formats.js')) return {isSymbolicLink:()=>false,isDirectory:()=>false};
      return stat.call(this,file,...args);
    };
    assert.throws(() => installedNativeProfile(), new RegExp(${JSON.stringify(expected)}));
  `;
  const result = spawnSync(process.execPath, ['-e', script], {cwd: path.resolve(__dirname, '../..'), encoding: 'utf8', timeout: 30000});
  assert.equal(result.status, 0, result.stderr || String(result.error));
}
test('P0.4 rejects npm 0.11.11 despite its identical version', () => rejectView('npm', 'installed-runtime-mismatch'));
test('P0.4 rejects changed installed bytes despite valid commit and locks', () => rejectView('bytes', 'installed-runtime-content'));
test('P0.4 rejects installed lock disagreement', () => rejectView('lock', 'installed-runtime-mismatch'));
test('P0.4 rejects an unlisted optional custom formats module', () => rejectView('extra', 'installed-runtime-content'));
