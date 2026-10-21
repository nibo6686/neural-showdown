#!/usr/bin/env node
'use strict';
const path = require('node:path');
const engine = path.resolve(__dirname, '../../sim-core/node_modules/pokemon-showdown');
const {Teams} = require(engine);
const commit = 'b8f23c99629132611ba59e99480cb148ea8c5d3d';
if (require(path.join(engine, 'package.json')).engine_commit !== commit) throw new Error('Witness search requires pinned b8f23c99 engine');
function findWitnessSeed(predicate, {start=1, max=5000, tail=[2,3,4]}={}) {
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(max) || start<1 || max<start || tail.length!==3 || !tail.every(Number.isSafeInteger)) throw new Error('Expected integer seed bounds and a three-integer tail');
  for (let n=start;n<=max;n++) {
    const seed=[n,...tail], team=Teams.generate('gen9randombattle',{seed});
    if (predicate(team,seed)) return {seed,team};
  }
  throw new Error(`No witness in seeds ${start}..${max}`);
}
module.exports={findWitnessSeed};
if (require.main===module) {
  const options=Object.fromEntries(process.argv.slice(2).map(arg=>{const i=arg.indexOf('=');if(i<0)throw new Error('Use --species=X --move=id --ability=X --item=X --slot=1 --max=5000');return [arg.slice(2,i),arg.slice(i+1)];}));
  for (const key of Object.keys(options)) if (!['species','move','ability','item','slot','start','max','tail'].includes(key)) throw new Error('Unknown search option: '+key);
  if (!['species','move','ability','item'].some(key=>options[key])) throw new Error('A witness predicate is required');
  const matches=set=>!!set && ['species','ability','item'].every(key=>!options[key]||set[key]===options[key]) && (!options.move||set.moves.includes(options.move));
  const result=findWitnessSeed(team=>options.slot?matches(team[Number(options.slot)-1]):team.some(matches),{start:Number(options.start||1),max:Number(options.max||5000),tail:options.tail?options.tail.split(',').map(Number):[2,3,4]});
  console.log(JSON.stringify(result));
}
