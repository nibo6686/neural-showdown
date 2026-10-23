'use strict';
const ignored = new Set(['t:', 'j', 'J', 'l', 'L', 'n', 'N', 'c', 'c:', 'raw', 'html', 'uhtml',
  'uhtmlchange', 'inactive', 'inactiveoff', 'player', 'gametype', 'gen', 'tier', 'rated', 'rule',
  'teampreview', 'seed', 'timer', 'debug', 'request', 'error', 'sideupdate', 'badge', '']);
const keep = line => line.startsWith('|') && !ignored.has(line.split('|')[1]);
function expectedPublic(replay) {
  const lines = replay.log.split(/\r?\n/);
  const end = lines.findIndex(line => /^\|-message\|.*(?: forfeited\.| lost due to inactivity\.)$/.test(line));
  return {lines: (end < 0 ? lines : lines.slice(0, end)).filter(keep),
    ending: end < 0 ? 'normal' : lines[end].includes('forfeited.') ? 'forfeit' : 'inactivity'};
}
module.exports = {keep, expectedPublic};
