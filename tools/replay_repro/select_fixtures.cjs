'use strict';
const fs = require('node:fs');
const path = require('node:path');

// Match evidence in public records, never hidden input-log teams or choices.
const move = names => log => new RegExp('\\|move\\|[^\\n|]+\\|(?:' + names + ')\\|').test(log);
const pivot = names => log => new RegExp('\\|switch\\|[^\\n]+\\|\\[from\\] (?:'+names+')(?:\\n|$)').test(log);
function drag(names){return log=>{
  let target=null;
  for(const line of log.split('\n')){
    const parts=line.split('|');
    if(parts[1]==='move')target=new RegExp('^(?:'+names+')$').test(parts[3])&&!line.includes('[miss]')?parts[4]?.slice(0,2):null;
    if(parts[1]==='drag'&&target===parts[2].slice(0,2))return true;
    if(parts[1]==='turn')target=null;
  }
  return false;
};}
function choiceLock(log) {
  const items=new Map(),moves=new Map();
  for(const line of log.split('\n')){
    const parts=line.split('|'),actor=parts[2];
    if(parts[1]==='-item') {items.set(actor,/^Choice (Band|Specs|Scarf)$/.test(parts[3]));moves.delete(actor);}
    if(['switch','drag','replace','-enditem'].includes(parts[1])) {items.delete(actor);moves.delete(actor);}
    if(parts[1]==='move' && items.get(actor)){
      if(moves.get(actor)===parts[3])return true;
      moves.set(actor,parts[3]);
    }
  }
  return false;
}
const targets = {
  ...Object.fromEntries(['U-turn','Volt Switch','Flip Turn','Parting Shot','Shed Tail','Teleport','Chilly Reception'].map(name => [name, pivot(name)])),
  'Roar/Whirlwind': drag('Roar|Whirlwind'), 'Dragon Tail/Circle Throw': drag('Dragon Tail|Circle Throw'),
  'Red Card': log => /\|(?:item: )?Red Card/.test(log),
  'Eject Button/Pack': log => /\|(?:item: )?Eject (?:Button|Pack)/.test(log),
  'Emergency Exit/Wimp Out': log => /ability: (?:Emergency Exit|Wimp Out)/.test(log),
  'Illusion reveal': log => /\|replace\|/.test(log),
  'Transform/Imposter': log => /\|-transform\|/.test(log),
  'Trick/Switcheroo': move('Trick|Switcheroo'), 'Knock Off': move('Knock Off'),
  'Magician': log => /ability: Magician/.test(log), 'Pickpocket': log => /ability: Pickpocket/.test(log),
  'Revival Blessing': move('Revival Blessing'), 'Encore': log => /\|-start\|[^\n]+\|Encore/.test(log),
  'choice lock': choiceLock,
  'Recharge': log => /\|-mustrecharge\|/.test(log), 'Struggle': move('Struggle'),
  'Outrage/locked move': log => /\|-start\|[^\n]+\|(?:lockedmove|Outrage)/.test(log) || move('Outrage|Petal Dance|Thrash')(log),
  'Slow Start': log => /\|-start\|[^\n]+\|ability: Slow Start/.test(log),
  'weather': log => /\|-weather\|(?!none)/.test(log),
  'terrain': log => /\|-fieldstart\|move: \w+ Terrain/.test(log),
  'Trick Room': log => /\|-fieldstart\|move: Trick Room/.test(log),
  'hazards and removal': log => /\|-sidestart\|[^\n]+\|(?:move: )?(?:Stealth Rock|Spikes|Toxic Spikes|Sticky Web)/.test(log) && move('Rapid Spin|Defog')(log),
  'screens': log => /\|-sidestart\|[^\n]+\|(?:move: )?(?:Reflect|Light Screen|Aurora Veil)/.test(log),
  'Terastallization': log => /\|-terastallize\|/.test(log),
  'forfeit': log => / forfeited\./.test(log), 'inactivity': log => / lost due to inactivity\./.test(log),
  '40+ turns': log => /\|turn\|(?:[4-9]\d|\d{3,})\n/.test(log),
};

function selectFixtures(directory, destination) {
  const entries = fs.readFileSync(path.join(directory,'admission.jsonl'),'utf8').trim().split('\n').map(JSON.parse)
    .filter(row => row.admitted === true).sort((a,b) => a.turns-b.turns || a.id.localeCompare(b.id,'en'));
  const winners = new Map(), chosen = new Map();
  for (const row of entries) {
    const replay = JSON.parse(fs.readFileSync(path.join(directory,row.id+'.json'),'utf8'));
    for (const [target, matches] of Object.entries(targets)) if (!winners.has(target) && matches(replay.log)) {
      winners.set(target,row.id);
      if (!chosen.has(row.id)) chosen.set(row.id,{replay,row,targets:[]});
      chosen.get(row.id).targets.push(target);
    }
    if (winners.size === Object.keys(targets).length) break;
  }
  fs.mkdirSync(destination,{recursive:true});
  const manifest = {schema_version:'replay-real/v1', selection:'fewest admitted turns, then replay ID (en lexical)',
    absent_targets:Object.keys(targets).filter(target => !winners.has(target)), fixtures:[]};
  for (const [id,{replay,row,targets:covered}] of chosen) {
    fs.writeFileSync(path.join(destination,id+'.json'),JSON.stringify(replay)+'\n');
    manifest.fixtures.push({id,rating:row.rating,server_commit:row.server_commit,turns:row.turns,targets:covered,
      ...(covered.includes('40+ turns') ? {long_only:true,budget_reason:'40-turn full adopted-K replay exceeds the curated fast budget; opt in with NEURAL_LONG_TESTS=1'} : {}),
      reason:'Shortest admitted public-log match for each listed target'});
  }
  fs.writeFileSync(path.join(destination,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  return manifest;
}
if(require.main===module) console.log(JSON.stringify(selectFixtures(process.argv[2],process.argv[3]),null,2));
module.exports={targets,selectFixtures};
