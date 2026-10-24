import {Pokemon} from 'pokemon-showdown';
import {State} from 'pokemon-showdown/dist/sim/state';
import {isDeepStrictEqual as equal} from 'node:util';
import type {AssociationRows} from './owner_identity_crosswalk';
import type {SeededBattleSnapshot} from './transition';
import type {PipelineBoundary} from './pipeline_integration';
import type {PlayerID} from './types';

const owners = ['p1','p2'] as const;
const movesPin = Object.getOwnPropertyDescriptor(Pokemon.prototype,'moves')!;
const resetPin = Object.getOwnPropertyDescriptor(Pokemon.prototype,'clearVolatile')!;
const serializePin = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(State),'serializePokemon')!;
const decodePin = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(State),'deserializePokemon')!;
function need(value: unknown, reason: string): asserts value {if (!value) throw new Error('owned-moves/v1/'+reason);}
const frozen = <T>(value: T): T => {if (value && typeof value === 'object') {Object.values(value).forEach(frozen); Object.freeze(value);} return value;};
type Lease = Readonly<{owner:PlayerID; roster:number; anchor:number; incarnation:1; subject:string}>;
type Actor = {actor:any; owner:PlayerID; roster:number; current:any[]; base:any[]; leases:Map<object,Lease>; initialized:boolean; admittedArray:boolean};
type Trace = {actor:Actor; array:any[]; slots:any[]; ids:string[]; output:any; emitted:string[]; reported:string[]; baseArray:any[]; baseRefs:any[]; virtual:boolean[]};
type SavedActor = {owner:PlayerID; roster:number; current:any[]; base:any[]; leases:Map<object,Lease>; initialized:boolean; admittedArray:boolean; raw:any; expected:any};
type Saved = {snapshot:SeededBattleSnapshot; actors:SavedActor[]};
type World = {battle:any; actors:Map<object,Actor>; rows?:AssociationRows; initial:boolean; traces:WeakMap<object,Trace>; undo:Array<()=>void>};
type Probe = {world:World; actors:SavedActor[]};
type Pending = {saved:Saved; input:any; decoded:Array<{source:SavedActor; actor:any; current:any[]; base:any[]}>};
export type OwnedMovesData = Readonly<{schema:'native-owner-moves/v1'; owner:PlayerID; roster:readonly any[]; moves:readonly any[]; option_links:readonly any[]}>;
type Preparation = {environment:object; parent:PipelineBoundary|null; boundary:PipelineBoundary; data:Record<PlayerID,OwnedMovesData>; checks:Array<()=>void>};

/** Private member of the request host. No caller-supplied map creates a lease. */
export class OwnedRequestMoveState {
  #worlds = new Map<object,World>();
  #serialized = new WeakMap<object,Probe>();
  #snapshots = new WeakMap<object,Saved>();
  #pending = new Map<object,Pending>();
  #prepared = new Map<object,Preparation>();
  #current:Record<PlayerID,OwnedMovesData>|undefined;
  #parent:PipelineBoundary|null = null;
  #ready:Preparation|undefined;
  #scope:object|undefined;

  attach(environment:object,battle:any,initial:boolean):void {
    need(!this.#worlds.has(environment),'duplicate-world');
    const world:World={battle,initial,actors:new Map(),traces:new WeakMap(),undo:[]}; this.#worlds.set(environment,world);
    const pending=this.#pending.get(environment);
    const freshOwners=new Map<object,SavedActor>();
    if (pending) for (const decoded of pending.decoded) {
      for(const slot of [...decoded.current,...decoded.base]) {need(!freshOwners.has(slot)||freshOwners.get(slot)===decoded.source,'foreign-reconstructed-slot');freshOwners.set(slot,decoded.source);}
      const source=decoded.source, before=[...source.current,...source.base], after=[...decoded.current,...decoded.base];
      const bijective=before.length===after.length && before.every((slot,i)=>before.every((other,j)=>(slot===other)===(after[i]===after[j])));
      const leases=new Map<object,Lease>();
      if (bijective) before.forEach((slot,i)=>{const lease=source.leases.get(slot);if(lease)leases.set(after[i],lease);});
      world.actors.set(decoded.actor,{actor:decoded.actor,owner:source.owner,roster:source.roster,current:decoded.actor.moveSlots,base:decoded.actor.baseMoveSlots,
        leases,initialized:source.initialized,admittedArray:bijective&&source.admittedArray});
    }
  }
  enroll(environment:object,rows:AssociationRows):void {
    const world=this.world(environment);need(!world.rows,'duplicate-enrollment');
    for (const owner of owners) rows[owner].objects.forEach((actor:any,i:number)=>{
      const held=world.actors.get(actor);
      if (world.initial) {
        need(!held,'duplicate-birth-actor');world.actors.set(actor,{actor,owner,roster:i+1,current:actor.moveSlots,base:actor.baseMoveSlots,leases:new Map(),initialized:false,admittedArray:true});
      } else need(held && held.owner===owner && held.roster===i+1,'foreign-reconstructed-actor');
    });
    need(world.actors.size===owners.reduce((n,owner)=>n+rows[owner].objects.length,0),'missing-decoder-actor');world.rows=rows;
    const slotOwners=new Map<object,Actor>();
    for(const held of world.actors.values())for(const slot of [...held.actor.moveSlots,...held.actor.baseMoveSlots]){need(!slotOwners.has(slot)||slotOwners.get(slot)===held,'foreign-slot-owner');slotOwners.set(slot,held);}
    this.#pending.delete(environment);
  }
  private world(environment:object):World {const world=this.#worlds.get(environment);need(world,'foreign-world');return world;}
  wrapActor(environment:object,actor:any):void {
    const world=this.world(environment);
    need(!Object.hasOwn(actor,'moves')&&!Object.hasOwn(actor,'clearVolatile')
      && equal(Object.getOwnPropertyDescriptor(Pokemon.prototype,'moves'),movesPin)
      && actor.clearVolatile===resetPin.value,'noncanonical-slot-writer');
    let reading:{array:any[];slots:any[];ids:string[];calls:number}|undefined;
    Object.defineProperty(actor,'moves',{configurable:true,get:()=>{
      const array=actor.moveSlots,slots=[...array],ids=movesPin.get!.call(actor);
      if (reading) {need(++reading.calls===1,'duplicate-roster-getter');reading.array=array;reading.slots=slots;reading.ids=ids;}
      return ids;
    }});
    world.undo.push(()=>{delete actor.moves;});
    const original=actor.clearVolatile;
    Object.defineProperty(actor,'clearVolatile',{configurable:true,writable:true,value:function(this:any,...args:any[]){
      need(this===actor,'foreign-reset');const base=actor.baseMoveSlots, refs=[...base];const result=original.apply(actor,args);
      const held=world.actors.get(actor);
      need(actor.baseMoveSlots===base && refs.length===actor.moveSlots.length && refs.every((slot,i)=>actor.moveSlots[i]===slot),'noncanonical-reset');
      if(held){held.current=actor.moveSlots;held.base=base;held.admittedArray=true;}return result;
    }});
    world.undo.push(()=>{delete actor.clearVolatile;});
    // The host calls this only around the pinned roster writer, never a probe.
    const get=actor.getSwitchRequestData, getDescriptor=Object.getOwnPropertyDescriptor(actor,'getSwitchRequestData');
    Object.defineProperty(actor,'getSwitchRequestData',{configurable:true,writable:true,value:function(this:any,...args:any[]){
      need(this===actor,'foreign-roster-this');if(args[0]===true)return get.apply(actor,args);
      need(!reading,'nested-roster-writer');reading={array:[],slots:[],ids:[],calls:0};
      try {
        const output=get.apply(actor,args), capture=reading, held=world.actors.get(actor);
        need(held && capture.calls===1 && capture.array===actor.moveSlots && capture.slots.every((slot,i)=>actor.moveSlots[i]===slot),'unbound-roster-getter');
        need(Array.isArray(output.moves)&&output.moves.length===capture.ids.length,'roster-decoration-shape');
        // Decoration belongs to this exact pinned call; literal IDs are inert.
        need(capture.ids.length===capture.slots.length && capture.ids.every((id,i)=>id===capture.slots[i].id),'roster-getter-value');
        if(!held.initialized){
          if(world.initial) capture.slots.forEach((slot,i)=>{
            if(!slot.virtual && actor.baseMoveSlots[i]===slot && !held.leases.has(slot)) held.leases.set(slot,Object.freeze({owner:held.owner,roster:held.roster,anchor:i+1,incarnation:1,subject:`${held.owner}:roster:${held.roster}:move:${i+1}:incarnation:1`}));
          });held.initialized=true;
        }
        if(held.current!==capture.array)held.admittedArray=false;
        world.traces.set(output,{actor:held,array:capture.array,slots:capture.slots,ids:[...capture.ids],output,emitted:output.moves,reported:[...output.moves],baseArray:actor.baseMoveSlots,baseRefs:[...actor.baseMoveSlots],virtual:capture.slots.map(slot=>!!slot.virtual)});return output;
      } finally {reading=undefined;}
    }});
    world.undo.push(()=>{if(getDescriptor)Object.defineProperty(actor,'getSwitchRequestData',getDescriptor);else delete actor.getSwitchRequestData;});
  }
  serialize(environment:object,battle:any,operation:()=>any):any {
    const world=this.world(environment);need(world.battle===battle && world.rows && !this.#scope,'foreign-or-nested-serialization');
    need(State.serializePokemon===serializePin.value,'foreign-serializer');this.#scope=environment;const actors:SavedActor[]=[],seen=new Set<object>();
    const descriptor=Object.getOwnPropertyDescriptor(State,'serializePokemon');
    Object.defineProperty(State,'serializePokemon',{configurable:true,writable:true,value:(actor:any)=>{
      const held=world.actors.get(actor);need(held&&!seen.has(actor),'foreign-or-duplicate-serializer-actor');seen.add(actor);
      const current=[...actor.moveSlots],base=[...actor.baseMoveSlots],array=actor.moveSlots,baseArray=actor.baseMoveSlots;
      const raw=serializePin.value.call(State,actor);
      need(actor.moveSlots===array&&actor.baseMoveSlots===baseArray&&current.every((slot,i)=>actor.moveSlots[i]===slot)&&base.every((slot,i)=>actor.baseMoveSlots[i]===slot),'changed-serialization-slots');
      actors.push({owner:held.owner,roster:held.roster,current,base,leases:new Map(held.leases),initialized:held.initialized,admittedArray:held.admittedArray&&held.current===array,raw,expected:structuredClone(raw)});return raw;
    }});
    try {
      const raw=operation();need(actors.length===world.actors.size,'missing-serialization-actor');
      need(raw.sides.every((side:any)=>side.pokemon.every((row:any)=>actors.filter(actor=>actor.raw===row).length===1)),'serialization-occurrence');
      this.#serialized.set(raw,{world,actors});return raw;
    } finally {if(descriptor)Object.defineProperty(State,'serializePokemon',descriptor);else delete (State as any).serializePokemon;this.#scope=undefined;}
  }
  recordSnapshot(environment:object,raw:any,snapshot:SeededBattleSnapshot):void {
    const probe=this.#serialized.get(raw);need(probe?.world===this.world(environment),'missing-serialization-probe');
    const actors:SavedActor[]=[];
    for(const side of raw.sides) for(const node of side.pokemon){
      const source=probe.actors.find(actor=>actor.raw===node);need(source&&equal(source.expected,node),'altered-serialization-node');
      actors.push(source);
    }
    need(equal(raw,snapshot.simulator_state),'snapshot-clone');this.#snapshots.set(snapshot,{snapshot,actors});
  }
  finalizeSnapshot(source:SeededBattleSnapshot,target:SeededBattleSnapshot):void {
    const held=this.#snapshots.get(source);need(held&&equal(source.simulator_state,target.simulator_state),'foreign-snapshot-transfer');this.#snapshots.set(target,{...held,snapshot:target});
  }
  decode(environment:object,snapshot:SeededBattleSnapshot,input:any,operation:()=>any):any {
    const saved=this.#snapshots.get(snapshot);need(saved&&!this.#scope&&!this.#pending.has(environment),'missing-or-foreign-restore-probe');
    const nodes=input.sides.flatMap((side:any)=>side.pokemon), map=new Map<object,SavedActor>();
    need(nodes.length===saved.actors.length,'restore-node-count');
    nodes.forEach((node:any,i:number)=>{need(equal(node,saved.actors[i].expected),'altered-restore-node');map.set(node,saved.actors[i]);});
    const pending:Pending={saved,input,decoded:[]};this.#pending.set(environment,pending);this.#scope=environment;
    need(State.deserializePokemon===decodePin.value,'foreign-deserializer');const descriptor=Object.getOwnPropertyDescriptor(State,'deserializePokemon');
    Object.defineProperty(State,'deserializePokemon',{configurable:true,writable:true,value:(node:any,actor:any)=>{
      const source=map.get(node);need(source&&!pending.decoded.some(row=>row.source===source||row.actor===actor),'foreign-or-duplicate-decode-node');
      const result=decodePin.value.call(State,node,actor);pending.decoded.push({source,actor,current:[...actor.moveSlots],base:[...actor.baseMoveSlots]});return result;
    }});
    try {const battle=operation();need(pending.decoded.length===saved.actors.length,'missing-decode-actor');return battle;}
    catch(error){this.#pending.delete(environment);throw error;}
    finally {if(descriptor)Object.defineProperty(State,'deserializePokemon',descriptor);else delete (State as any).deserializePokemon;this.#scope=undefined;}
  }
  prepare(key:object,environment:object,boundary:PipelineBoundary,captures:Partial<Record<PlayerID,any>>,deliveries:Record<PlayerID,any>):Record<PlayerID,OwnedMovesData> {
    const world=this.world(environment);need(world.rows,'unadmitted-world');const data={} as Record<PlayerID,OwnedMovesData>,checks:Array<()=>void>=[];
    for(const owner of owners){
      const prior=this.#current?.[owner], history=new Map<string,any>((prior?.moves||[]).map((row:any)=>[row.subject,{...row,pp:{...row.pp,freshness:row.pp.state==='known'?'last_known':'current'},max_pp:{...row.max_pp,freshness:row.max_pp.state==='known'?'last_known':'current'},membership:'suspended'}]));
      const roster:any[]=[],links:any[]=[],capture=captures[owner],delivery=deliveries[owner];
      for(const [index,actor] of world.rows[owner].objects.entries()){
        const row=capture?.rows.find((row:any)=>row.actor===actor),held=world.actors.get(actor)!;
        const trace:Trace|undefined=row?world.traces.get(row.data):undefined;
        const valid=!!trace;
        const fact=(value:any,known:boolean)=>({state:known?'known':'unknown',value:known?value:null,reason:known?'none':'not_emitted',freshness:'current',observed_at:known?delivery.boundary_cursor:null,sequence:known?delivery.current.sequence:null});
        const unbound:number[]=[];
        if(trace){
          const check=()=>need(trace.emitted===row.data.moves&&equal(trace.reported,row.data.moves)&&trace.array===actor.moveSlots&&trace.slots.length===actor.moveSlots.length&&trace.slots.every((slot,i)=>slot===actor.moveSlots[i]&&slot.id===trace.ids[i]&&!!slot.virtual===trace.virtual[i])&&trace.baseArray===actor.baseMoveSlots&&trace.baseRefs.length===actor.baseMoveSlots.length&&trace.baseRefs.every((slot,i)=>slot===actor.baseMoveSlots[i]),'stale-roster-trace');check();checks.push(check);
          trace.slots.forEach((slot,i)=>{
            const lease=held.admittedArray&&held.leases.get(slot);
            if(!lease||slot.virtual){unbound.push(i+1);return;}
            let record=history.get(lease.subject);
            if(!record)record={subject:lease.subject,anchor:lease.anchor,incarnation:lease.incarnation,pp:fact(null,false),max_pp:fact(null,false)};
            record={...record,membership:'present',reported_move_id:trace.reported[i]};
            const move=capture?.move;
            if(move?.ordinary&&move.actor===actor){const option=move.slots.findIndex((entry:any)=>entry.reference===slot);
              if(option>=0){record.pp=fact(move.rows[option].pp,true);record.max_pp=fact(move.rows[option].maxpp,true);links.push({option_index:option+1,subject:lease.subject,sequence:delivery.current.sequence,cursor:delivery.boundary_cursor});}}
            history.set(lease.subject,record);
          });
        }
        roster.push({subject:`${owner}:roster:${index+1}`,current_moves:fact(trace?.reported,valid),incarnation_coverage:!valid||unbound.length?'blocked':'ordinary_base',reason:!valid?'not_emitted':unbound.length?'unsupported_writer':'none',unbound_positions:unbound});
      }
      data[owner]=frozen({schema:'native-owner-moves/v1',owner,roster,moves:[...history.values()],option_links:links});
    }
    this.#prepared.set(key,{environment,parent:this.#parent,boundary,data,checks});return data;
  }
  preflight(key:object):void {const entry=this.#prepared.get(key);need(entry&&entry.parent===this.#parent,'foreign-preparation');entry.checks.forEach(check=>check());this.#ready=entry;}
  installReady():void {this.#current=this.#ready!.data;this.#parent=this.#ready!.boundary;this.#ready=undefined;this.#prepared.clear();}
  release(environment:object):void {this.#worlds.get(environment)?.undo.reverse().forEach(undo=>undo());this.#worlds.delete(environment);this.#pending.delete(environment);for(const [key,row] of this.#prepared)if(row.environment===environment)this.#prepared.delete(key);if(this.#ready?.environment===environment)this.#ready=undefined;}
  revoke():void {for(const environment of this.#worlds.keys())this.release(environment);this.#current=undefined;this.#snapshots=new WeakMap();this.#serialized=new WeakMap();this.#prepared.clear();this.#parent=null;}
}
