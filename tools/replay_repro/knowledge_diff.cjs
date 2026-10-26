'use strict';
const {isDeepStrictEqual} = require('node:util');
const registry = require('../../docs/contracts/knowledge-coverage.json');
const {installedNativeProfile} = require('../../sim-core/dist/src/version_profile');
const {Teams} = require(installedNativeProfile().package_root);
const owners = ['p1', 'p2'], stats = ['atk', 'def', 'spa', 'spd', 'spe'];
const keyOf = row => [row.family, row.property, row.context, row.perspective].join('/');
const moveProperties = new Set(['current_moves','move_incarnation','pp','max_pp']);
const registered = registry.rows.filter(r => r.status === 'adopted' || r.status === 'legitimately_unknown');

/** Offline read-only oracle. Simulator truth never enters projections or chosen actions. */
function createKnowledgeDiff(session, {ownerMoves=false}={}) {
  // Old private profiles keep their previous oracle obligations and output.
  const hasMoves=ownerMoves;
  const relevant=registered.filter(row=>(!moveProperties.has(row.property)&&row.family!=='K08')||hasMoves);
  const observed=new Map();
  const rows = Object.fromEntries(relevant.map(row => [keyOf(row), {checks: 0, unknown: 0, mismatches: 0}]));
  const examples = [], starting = {};
  const initial = session.environment.battleStream.battle;
  for (const owner of owners) {
    const evidence = session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner);
    starting[owner] = evidence.raw_team.map((raw, index) => {
      const set = Teams.unpack(Teams.pack([structuredClone(raw)]))[0];
      const species = initial.dex.species.get(set.species);
      const slots = session.readNativeObjectHolding(session.getNativeObjectHolding(owner), owner).original_slots;
      const nativeSet = initial[owner].pokemon[slots.indexOf(index + 1)].set;
      const calculated = initial.spreadModify(species.baseStats, nativeSet);
      return {roster_species: raw.species, starting_moves: raw.moves, item: raw.item || null, ability: raw.ability,
        submitted_nature: raw.nature ?? null, submitted_happiness: raw.happiness ?? null,
        shiny: raw.shiny ?? null, ball: raw.pokeball ?? null,
        starting_tera: set.teraType || species.types[0], level: set.level || 100,
        calculated_stats: Object.fromEntries(stats.map(stat => [stat, calculated[stat]])), hp_max: species.maxHP || calculated.hp};
    });
  }
  function mismatch(key, frame, fact, expected, reason) {
    rows[key].mismatches++;
    if (examples.length < 10) examples.push({row: key, owner: frame.owner, boundary: frame.step_index,
      subject: fact?.subject, projected: fact, expected, reason});
  }
  function compare(current, frames) {
    const battle = current.environment.battleStream.battle;
    for (const frame of frames) {
      const owner = frame.owner, projection = frame.knowledge.projection;
      const association = current.readNativeObjectHolding(current.getNativeObjectHolding(owner), owner);
      const roster = new Map(association.original_slots.map((slot, position) => [slot, battle[owner].pokemon[position]]));
      for (const row of relevant) {
        if(row.family==='K08'){
          const key=keyOf(row),request=projection.owned_moves?.request;
          if(!request){mismatch(key,frame,null,null,'missing-request-flags');continue;}
          const history=current.readRequestDeliveryHistory(current.getRequestDeliveryHandle(owner),owner);
          const d=history.deliveries.find(d=>d.sequence===request.sequence),raw=d?JSON.parse(d.source.request_json).active?.[0]:null;
          const checkFlag=(f,object,property)=>{
            rows[key].checks++;const present=!!object&&Object.hasOwn(object,property);
            if(!f||f.present!==present||f.state!==(present?'known':'unknown')||f.value!==(present?object[property]:null)||f.reason!==(present?'none':'not_emitted'))mismatch(key,frame,f,{present,value:present?object[property]:null},'literal-flag-mismatch');
            if(!present)rows[key].unknown++;
          };
          if(row.property==='disabled'){
            for(const option of request.options||[]){
              if(row.context==='current'&&!option.subject){rows[key].unknown++;continue;}
              checkFlag(option.disabled,raw?.moves[option.option_index-1],'disabled');
            }
            if(!request.options)rows[key].unknown++;
          }else if(row.property==='lock'){
            rows[key].checks++;const expected=raw?raw.moves.flatMap((m,i)=>m.disabled===true?[]:[i+1]):null;
            if(request.restriction.state!==(raw?'known':'unknown')||!isDeepStrictEqual(request.restriction.permitted_options,expected))mismatch(key,frame,request.restriction,expected,'request-restriction-mismatch');
            let appearance=null,encore=false;
            for(const line of current.boundary.perspectives[owner].observation.protocol_prefix){const p=line.split('|');if(!p[2]?.startsWith(owner+'a: '))continue;
              if(['switch','drag','replace'].includes(p[1])){appearance=p[2];encore=false;}
              else if(p[2]===appearance){if(p[1]==='faint'){appearance=null;encore=false;}else if(p[3]==='Encore'&&p[1]==='-end')encore=false;else if(p.length===4&&p[3]==='Encore'&&p[1]==='-start')encore=true;}}
            const reason=request.restriction.reason,expectedReason=raw&&!raw.moves.some(m=>['recharge','struggle'].includes(m.id))&&appearance&&encore?'encore':null;
            if(reason.value!==expectedReason||reason.state!==(expectedReason?'known':'unknown'))mismatch(key,frame,reason,expectedReason,'unproven-lock-reason');
          }else checkFlag(request.emitted_flags[row.property],raw,row.property==='maybe_trapped'?'maybeTrapped':row.property);
          continue;
        }
        if(moveProperties.has(row.property)){
          const key=keyOf(row),moves=projection.owned_moves,history=current.readRequestDeliveryHistory(current.getRequestDeliveryHandle(owner),owner);
          const delivered=sequence=>{const d=history.deliveries.find(d=>d.sequence===sequence);return d?JSON.parse(d.source.request_json):null;};
          if(!moves){mismatch(key,frame,null,null,'missing-move-profile');continue;}
          if(row.property==='current_moves'){
            for(const inventory of moves.roster){const f=inventory.current_moves;if(f.state==='unknown'){rows[key].unknown++;continue;}
              rows[key].checks++;const slot=Number(inventory.subject.split(':')[2]),actor=roster.get(slot),position=battle[owner].pokemon.indexOf(actor);
              const raw=delivered(f.sequence),expected=raw?.side?.pokemon[position]?.moves;
              if(!isDeepStrictEqual(f.value,expected))mismatch(key,frame,inventory,expected,'roster-emission-mismatch');
            }continue;
          }
          if(row.property==='move_incarnation'){
            for(const m of moves.moves){if(m.membership!=='present'){rows[key].unknown++;continue;}rows[key].checks++;
              const actor=roster.get(Number(m.subject.split(':')[2])),base=actor?.baseMoveSlots[m.anchor-1];
              if(m.incarnation!==1||!base||base.virtual||!actor.moveSlots.includes(base))mismatch(key,frame,m,1,'native-base-incarnation-mismatch');
            }
            rows[key].unknown+=moves.roster.reduce((n,r)=>n+r.unbound_positions.length,0);continue;
          }
          if(row.context==='request'){
            const raw=delivered(projection.request.sequence);
            for(const option of projection.request.options||[]){rows[key].checks++;const projected=option[row.property],expected=raw?.active?.[0]?.moves[option.option_index-1]?.[row.property==='max_pp'?'maxpp':'pp'];
              if((projected.state==='known'?projected.value!==expected:projected.value!==null||projection.request.state!=='exact_options'))mismatch(key,frame,option,expected,'option-emission-mismatch');
            }
            if(!projection.request.options)rows[key].unknown++;continue;
          }
          for(const m of moves.moves){const f=m[row.property],obsKey=owner+'/'+m.subject+'/'+row.property;
            if(f.state==='unknown'){rows[key].unknown++;if(f.value!==null)mismatch(key,frame,m,null,'fabricated-unknown-PP');continue;}
            rows[key].checks++;let expected=observed.get(obsKey);
            if(f.freshness==='current'){
              const actor=roster.get(Number(m.subject.split(':')[2])),base=actor?.baseMoveSlots[m.anchor-1],index=actor?.moveSlots.indexOf(base),raw=delivered(f.sequence);
              const value=raw?.active?.[0]?.moves[index]?.[row.property==='max_pp'?'maxpp':'pp'];
              expected={value,sequence:f.sequence,observed_at:f.observed_at};observed.set(obsKey,expected);
              if(value!==base?.[row.property==='max_pp'?'maxpp':'pp'])mismatch(key,frame,m,base?.pp,'native-PP-emission-mismatch');
            }
            if(!expected||f.value!==expected.value||f.sequence!==expected.sequence||f.observed_at!==expected.observed_at)mismatch(key,frame,m,expected,'retained-PP-mismatch');
          }continue;
        }
        const key = keyOf(row), context = row.context === 'original' ? projection.starting : projection.current;
        const facts = context.filter(f => f.property === row.property && f.family === row.family
          && (row.perspective === 'own' ? f.owner === owner : f.owner !== owner));
        if (!facts.length) {
          if (row.status === 'adopted') mismatch(key, frame, null, null, 'adopted-row-missing');
          continue;
        }
        for (const fact of facts) {
          if (fact.state === 'unknown') {
            rows[key].unknown++;
            if (fact.value !== null) mismatch(key, frame, fact, null, 'fabricated-unknown-value');
            continue;
          }
          rows[key].checks++;
          if (row.status === 'legitimately_unknown') {mismatch(key, frame, fact, null, 'registry-unknown-value'); continue;}
          const slot = new RegExp(`^${owner}:roster:([1-6])$`).exec(fact.subject)?.[1];
          const actor = slot ? roster.get(Number(slot)) : undefined;
          let expected;
          if (row.property === 'roster_size') expected = starting[owner].length;
          else if (row.property === 'roster_order') expected = Number(slot);
          else if (row.context === 'original') expected = starting[owner][Number(slot) - 1]?.[row.property];
          else {
            if (!actor) {mismatch(key, frame, fact, null, 'foreign-or-unbound-subject'); continue;}
            const truth = {hp: actor.hp, fainted: actor.fainted, status: actor.status || null,
              ability: actor.ability || null, level: actor.level, gender: actor.gender || null,
              shiny: !!actor.set.shiny, ball: actor.pokeball, details: actor.details, hp_max: actor.maxhp,
              calculated_stats: Object.fromEntries(stats.map(stat => [stat, actor.baseStoredStats[stat]]))};
            expected = truth[row.property];
          }
          if (expected === undefined || !isDeepStrictEqual(fact.value?.data ?? null, expected)
            || (fact.state === 'known_absent') !== (expected === null)) mismatch(key, frame, fact, expected, 'truth-mismatch');
        }
      }
    }
  }
  return {compare, result: () => ({rows, checks: Object.values(rows).reduce((n, r) => n + r.checks, 0),
    mismatches: Object.values(rows).reduce((n, r) => n + r.mismatches, 0), examples})};
}
module.exports = {createKnowledgeDiff, keyOf};
