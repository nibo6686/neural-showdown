"""Read-only, independently resealed proof of Prompt12 external-ID incompatibility."""
import copy,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'trainer/src'))
from trainer.tests.test_perspective_knowledge import fixture,reseal,independent_id,independent_canonical,revision_form
from neural.perspective_knowledge import check_knowledge_structure,KnowledgeStructureError
PLAN=ROOT/'docs/planning'; witnesses=json.loads((PLAN/'perspective-fidelity-prompt12-legacy-witness.json').read_bytes())['rows']
# Literal external positions independently compared with typed-references.json.
positions=[('boundary','observation_id','input_observation'),('boundary','belief_id','input_belief'),('boundary','actor_record_id','record_id'),('binding','input_observation','input_observation'),('binding','successor_observation','successor_observation'),('binding','input_belief','input_belief'),('binding','successor_belief','successor_belief'),('binding','transition','transition'),('binding','actor_record','record_id')]
rows=[]; payloads=[]
for witness in witnesses:
 for form in ('full','ordinary','compact'):
  control=revision_form(fixture('sim-full.json'),form)
  assert check_knowledge_structure(control)['structure_valid']
  for kind,field,legacyfield in positions:
   audit=fixture('sim-full.json')
   if kind=='boundary':
    target=next(b for b in audit['tables']['boundary'] if b['index']==0)['bindings'][0 if witness['owner']=='p1' else 1]
   else: target=next(b for b in audit['tables']['binding'] if b['owner']==witness['owner'])
   target[field]=witness[legacyfield]; audit=revision_form(audit,form)
   assert audit['id']==independent_id(audit)
   for table in audit['tables'].values():
    for row in table if isinstance(table,list) else table.values(): assert row['id']==independent_id(row)
   before=independent_canonical(audit)
   try: check_knowledge_structure(audit); raise AssertionError('actual legacy ID unexpectedly accepted')
   except KnowledgeStructureError as error: py=str(error)
   assert before==independent_canonical(audit)
   rows.append({'owner':witness['owner'],'version':witness['version'],'form':form,'path':kind+'.'+field,'actual_legacy_id':witness[legacyfield],'frozen_pattern':'^sha256:[0-9a-f]{64}$','matches_frozen_pattern':bool(re.fullmatch(r'sha256:[0-9a-f]{64}',witness[legacyfield])),'python_guard':py,'all_identities_independently_resealed':True})
   payloads.append(audit)
node="const fs=require('fs'),k=require('./sim-core/dist/src/perspective_knowledge.js'); const a=JSON.parse(fs.readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(a.map(v=>{const before=JSON.stringify(v); try{k.checkKnowledgeStructure(v);return {accepted:true}}catch(e){return {accepted:false,guard:e.message,immutable:JSON.stringify(v)===before}}})));"
p=subprocess.run(['node','-e',node],cwd=ROOT,input=json.dumps(payloads,ensure_ascii=False).encode('utf-8'),capture_output=True,timeout=60); assert p.returncode==0,p.stderr
for row,ts in zip(rows,json.loads(p.stdout)):
 assert ts=={'accepted':False,'guard':row['python_guard'],'immutable':True}
 assert not row['matches_frozen_pattern']; row['typescript']=ts
packet={'scope':'Contract scalar incompatibility; canary mutations are not genuine source-join positives','legacy_positive_controls':4,'resealed_schema_reject_controls':len(rows),'both_owners':True,'both_legacy_schemas':True,'all_knowledge_forms':True,'rows':rows}
(PLAN/'perspective-fidelity-prompt12-blocker-matrix.json').write_text(json.dumps(packet,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:v for k,v in packet.items() if k!='rows'}))
