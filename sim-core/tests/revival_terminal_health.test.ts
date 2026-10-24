import assert from 'node:assert/strict';
import test from 'node:test';
import {assertPublicHealthMatchesEvidence, withTerminalOwner} from '../src/public_health';
import {NATIVE11_CONTEXT} from '../src/version_profile';

for (const owner of ['p1','p2'] as const) test(`revived bench exact HP survives a requestless terminal boundary for ${owner}`, () => {
  const prefix = [`|switch|${owner}a: Bench|Snorlax|100/100`, `|faint|${owner}a: Bench`,
    `|switch|${owner}a: Lead|Pawmot|100/100`, `|-heal|${owner}: Bench|50/100|[from] move: Revival Blessing`];
  const rows = [{ident:`${owner}: Lead`,active:true,hp_text:'100/100',hp_ratio:1,fainted:false,status:null},
    {ident:`${owner}: Bench`,active:false,hp_text:'131/263',hp_ratio:131/263,fainted:false,status:null}];
  const predecessor = {schema_version:'observable-battle-state/v2',battle_id:'revival-terminal',perspective:owner,protocol_prefix:prefix,
    request:{side:rows.map(row => ({ident:row.ident,condition:row.hp_text,active:row.active}))},view:{self_team:rows,opponent_team:[]}};
  const successor = {...predecessor,protocol_prefix:[...prefix,`|win|${owner}`],request:null,view:{self_team:structuredClone(rows),opponent_team:[],terminated:true}};
  const context = {predecessor,before:{step_index:1,branch_id:'before',state_fingerprint:'input'},
    after:{step_index:2,branch_id:'after',state_fingerprint:'output'},
    transition:{step_index:1,parent_branch_id:'before',branch_id:'after',input_state_fingerprint:'input',output_state_fingerprint:'output'}};
  const validate = (value: typeof successor, authority = true) => {
    const run = () => assertPublicHealthMatchesEvidence(value.protocol_prefix,owner,value.view,null,NATIVE11_CONTEXT);
    return authority ? withTerminalOwner(context,value,run) : run();
  };
  validate(successor);
  assert.throws(() => validate(successor,false), /Revival bench outcome/);
  const wrong = structuredClone(successor); wrong.view.self_team[1].hp_text='130/263'; wrong.view.self_team[1].hp_ratio=130/263;
  assert.throws(() => validate(wrong), /terminal bench HP/);
  const foreign = structuredClone(successor); foreign.perspective=owner === 'p1' ? 'p2' : 'p1';
  assert.throws(() => validate(foreign), /discontinuous/);
});
