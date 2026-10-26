import {bornSession,playTo} from './born_session';
import path from 'node:path';
const {sessionFrames}=require(path.resolve(__dirname,'../../../../tools/replay_repro/export_frames.cjs'));
const base='Magikarp\nAbility: Swift Swim\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash';

/** Hidden differences enter at original birth, never by mutating a live snapshot. */
export async function invarianceCases(){
 const cases:any[]=[];
 for(const viewer of ['p1','p2'] as const){
  const hidden=viewer==='p1'?'p2':'p1',variants:any[]=[];
  for(const alternate of [false,true]){
   const reserve=alternate?'Reserve (Lapras) @ Sitrus Berry\nAbility: Water Absorb\nTera Type: Water\n- Growl':'Reserve (Gyarados) @ Leftovers\nAbility: Moxie\nTera Type: Fire\n- Splash';
   const changed=base.slice(0,base.indexOf('\n\n'))+'\n\n'+reserve;
   const recipients={p1:{},p2:{}};
   const session=await bornSession({teams:{p1:base,p2:base,[hidden]:changed},options:{battle_id:'W9L-invariance',
    observation_schema_version:'observable-battle-state/v2',knowledge_recipients:recipients,knowledge_profile:'native-owner-moves/v1'}});
   try{
    const frames=[sessionFrames(session,recipients).find((f:any)=>f.owner===viewer)];
    await playTo(session,[{p1:'move 1',p2:'move 1'}]);
    frames.push(sessionFrames(session,recipients).find((f:any)=>f.owner===viewer));
    await playTo(session,[{p1:'move 1',p2:'move 1',[hidden]:'switch 2'}]);
    frames.push(sessionFrames(session,recipients).find((f:any)=>f.owner===viewer));
    variants.push(frames);
   }finally{await session.close();}
  }
  cases.push({viewer,variants});
 }
 return cases;
}
