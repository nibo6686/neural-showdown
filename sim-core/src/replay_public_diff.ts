import type {Battle} from 'pokemon-showdown';
import type {BattleView, PlayerID} from './types';
import {NATIVE11_CONTEXT} from './version_profile';
import {PUBLIC_BOOST_KEYS, publicBoostEvidence} from './public_boosts';
import {assertPublicFieldMatchesEvidence} from './public_field';
import {projectPublicHealth} from './public_health';
import {publicTeamIdent} from './typed_state_lifecycle';

export interface PublicMismatch { owner: PlayerID; turn: number; fact: string; effect_id: string; actual: unknown; extracted: unknown }
/** Read-only oracle. Truth never enters a tracker, request, feature or dataset. */
export function compareReplayPublicState(battle: Battle, view: BattleView, prefix: string[]): {checks:number; mismatches:PublicMismatch[]} {
  const owner=view.player, mismatches:PublicMismatch[]=[];let checks=0;
  const compare=(fact:string,id:string,actual:unknown,extracted:unknown)=>{
    checks++;if(JSON.stringify(actual)!==JSON.stringify(extracted))mismatches.push({owner,turn:battle.turn,fact,effect_id:id,actual,extracted});
  };
  assertPublicFieldMatchesEvidence(prefix,view.field,NATIVE11_CONTEXT);
  const boostEvidence=publicBoostEvidence(prefix,NATIVE11_CONTEXT), health=projectPublicHealth(prefix);
  compare('weather',battle.field.weather||'none',battle.field.weather||null,view.field.weather==='none'?null:view.field.weather);
  compare('terrain',battle.field.terrain||'none',battle.field.terrain||null,view.field.terrain);
  const terrains=new Set(['electricterrain','grassyterrain','mistyterrain','psychicterrain']);
  // Rule implementations such as Sleep Clause live in the same internal map
  // but do not announce a public field lifecycle.
  const publicPseudo=(id:string)=>NATIVE11_CONTEXT.effects[id]?.category==='pseudo_weather' && NATIVE11_CONTEXT.effects[id]?.classification==='represented';
  compare('pseudo-weather','field',Object.keys(battle.field.pseudoWeather).filter(publicPseudo).sort(),view.field.pseudo_weather.filter(id=>!terrains.has(id)).sort());
  const lifecycle=NATIVE11_CONTEXT.inventory.public_typed_state_lifecycle.entries.filter((e:any)=>e.disposition==='evidence-derived-typed');
  for(const side of battle.sides) {
    const own=side.id===owner, relative=own?'self':'opponent';
    for(const entry of lifecycle.filter((e:any)=>e.family==='side_condition')) {
      const state=side.sideConditions[entry.id];
      compare('side-condition',`${side.id}:${entry.id}`,state?(entry.mode==='count'?state.layers:1):0,view.field.side_conditions[relative][entry.id]||0);
    }
    const truth=side.active[0], row=(own?view.self_team:view.opponent_team).find(p=>p.active);
    if(!truth || !row) { if(truth?.hp)compare('active',side.id,true,!!row);continue; }
    const ident=publicTeamIdent(row.ident), announcedHealth=health[ident];
    if(own || announcedHealth?.hp_text!==undefined) {
      const condition=truth.getHealth()[own?'secret':'shared'];
      compare('hp',side.id,condition.split(' ')[0],row.hp_text?.split(' ')[0]);
    }
    if(!truth.hp)continue;
    compare('status',side.id,truth.status||null,row.status);
    const publicBoosts=boostEvidence.get(ident);
    for(const key of PUBLIC_BOOST_KEYS)if(publicBoosts && publicBoosts[key]!==null) {
      // Switch/reset evidence establishes zero even when the sparse view omits it.
      compare('boost',`${side.id}:${key}`,truth.boosts[key],row.boosts[key]??0);
    }
    for(const entry of lifecycle.filter((e:any)=>e.family==='move_volatile'))compare('volatile',`${side.id}:${entry.id}`,!!truth.volatiles[entry.id],row.volatiles.includes(entry.id));
  }
  return {checks,mismatches};
}
