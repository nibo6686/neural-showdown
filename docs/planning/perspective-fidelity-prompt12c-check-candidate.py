"""Prompt12c scoped validation/preservation, no historical evidence regeneration."""
import difflib,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PLAN=ROOT/'docs/planning'; PREFIX='perspective-fidelity-prompt12c-'; FOLDER=ROOT/'docs/contracts/fixtures/perspective-knowledge-v1'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'trainer/src'))
from neural.perspective_knowledge import check_knowledge_structure,KnowledgeStructureError
from trainer.tests.test_perspective_knowledge import native_legacy_control,independent_canonical
write=lambda n,v:(PLAN/(PREFIX+n)).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONUTF8','PYTHONIOENCODING')}; env['PYTHONPATH']=str(ROOT/'trainer/src'); env['PYTHON']=sys.executable
commands=[]
for cwd,args,log in [
 ('sim-core',['npm.cmd','run','build'],'build.log'),
 ('.',['node','docs/planning/'+PREFIX+'legacy-witness.cjs'],'legacy-validation.log'),
 ('.',[sys.executable,'-m','unittest','trainer.tests.test_perspective_knowledge','trainer.tests.test_pipeline_record.PipelineRecordTest.test_valid_linked_bundle_builds_checkpoint_free_data_record','trainer.tests.test_pipeline_record.PipelineRecordTest.test_unicode_prefix_hashes_keep_typescript_and_data_envelopes_distinct'],'python-validation.log'),
 ('sim-core',['node','--test','--test-reporter=tap','dist/tests/perspective_knowledge.test.js'],'ts-validation.log'),
 ('.',[sys.executable,'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'],'contract.log'),
 ('.',['git','diff','--check'],'diff-check.log')]:
 start=time.monotonic(); result=subprocess.run(args,cwd=ROOT/cwd,env=env,capture_output=True,timeout=180)
 (PLAN/(PREFIX+log)).write_bytes(result.stdout+result.stderr)
 commands.append({'cwd':cwd,'argv':args,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'log':PREFIX+log})
 write('validation.json',{'encoding_overrides_unset':True,'python':sys.executable,'commands':commands})
 print(log,'exit',result.returncode,flush=True); assert result.returncode==0,result.stderr.decode('utf-8',errors='replace')
base=json.loads((PLAN/(PREFIX+'baseline.json')).read_bytes())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==base['head']
protected={p:h for p,h in base['hashes'].items() if p not in base['owned']}
changes={p:{'before':h,'after':sha(ROOT/p) if (ROOT/p).is_file() else None} for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h}; assert not changes,changes
# Independent JSON-path delta restricts edits to the nine literal regex leaves.
old=json.loads((PLAN/(PREFIX+'baseline-1.txt')).read_bytes()); new=json.loads((FOLDER/'schema.json').read_bytes())
expected={'owner_binding.observation_id':'obs-','owner_binding.belief_id':'belief-','owner_binding.actor_record_id':'datarec-','binding.input_observation':'obs-','binding.successor_observation':'obs-','binding.input_belief':'belief-','binding.successor_belief':'belief-','binding.transition':'transition-','binding.actor_record':'datarec-'}
def differences(a,b,path=()):
 if type(a)!=type(b): return [(path,a,b)]
 if isinstance(a,dict):
  assert set(a)==set(b),path
  return [x for k in a for x in differences(a[k],b[k],path+(k,))]
 if isinstance(a,list):
  assert len(a)==len(b),path
  return [x for i in range(len(a)) for x in differences(a[i],b[i],path+(i,))]
 return [] if a==b else [(path,a,b)]
delta=differences(old,new); expectedpaths={}
for field,prefix in expected.items():
 kind,key=field.split('.'); node=old['$defs'][kind]['properties'][key]
 path=('$defs',kind,'properties',key)+(('anyOf',0) if 'anyOf' in node else ())+('pattern',)
 expectedpaths[path]='^(?:sha256:|'+prefix+')[0-9a-f]{64}$'
assert len(delta)==9 and {path for path,a,b in delta}==set(expectedpaths)
for path,a,b in delta: assert a=='^sha256:[0-9a-f]{64}$' and b==expectedpaths[path]
write('schema-delta.json',{'only_nine_pattern_leaves':True,'requiredness_nullability_unchanged':True,'paths':[{'path':list(path),'before':a,'after':b} for path,a,b in delta]})
oldpin=sha(PLAN/(PREFIX+'baseline-1.txt')); newpin=sha(FOLDER/'schema.json')
for index,name in [(2,'sim-core/src/perspective_knowledge.ts'),(3,'trainer/src/neural/perspective_knowledge.py')]:
 assert (ROOT/name).read_bytes()==(PLAN/(PREFIX+'baseline-'+str(index)+'.txt')).read_bytes().replace(oldpin.encode(),newpin.encode())
# Retained historical runtime case classifications and codes must match exactly.
oldmatrix=json.loads((PLAN/'perspective-fidelity-prompt11-matrix.json').read_bytes()); cases=[]
for row in oldmatrix['cases']:
 value=json.loads((FOLDER/row['file']).read_bytes())
 try: check_knowledge_structure(value,row['required']); status={'status':'structure_valid','code':None}
 except KnowledgeStructureError as e: status={'status':'structural_reject','code':str(e)}
 assert status==row['python'],row['file']; cases.append({**row,'python':status})
node="""const fs=require('fs'),path=require('path'),k=require('./sim-core/dist/src/perspective_knowledge.js');const rows=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(rows.map(r=>{try{k.checkKnowledgeStructure(k.parseKnowledgeJson(fs.readFileSync(path.join('docs/contracts/fixtures/perspective-knowledge-v1',r.file))),r.required??undefined);return {status:'structure_valid',code:null}}catch(e){return {status:'structural_reject',code:e.message}}})));"""
r=subprocess.run(['node','-e',node],cwd=ROOT,input=json.dumps(cases).encode(),capture_output=True,env=env,timeout=60); assert r.returncode==0
for row,ts in zip(cases,json.loads(r.stdout)): assert ts==row['typescript']==row['python'],row['file']
write('retained-matrix.json',{**oldmatrix,'cases':cases,'matches_original_case_classifications':True})
# Explicit full-closure native controls: no claim of genuine source chronology.
green=[]
for version in ('observable-battle-state/v1','observable-battle-state/v2'):
 for form in ('full','ordinary','compact'):
  audit=native_legacy_control(version,form); d=check_knowledge_structure(audit)
  green.append({'version':version,'form':form,'owners':['p1','p2'],'python':d,'all_native_external_domains':True,'scope':'Coordinated structural joins only; actual source/history/legacy authenticity unverified'})
write('green.json',green)
fresh=json.loads((PLAN/(PREFIX+'fresh-legacy-witness.json')).read_bytes())['rows']; held=json.loads((FOLDER/'legacy-id-regressions.json').read_bytes())['witnesses']
assert fresh==held,'fresh validated witness identity drift'
diff=[]; candidate={}
for i,name in enumerate(base['owned']):
 file=ROOT/name; current=file.read_text(encoding='utf-8'); prior=(PLAN/(PREFIX+'baseline-'+str(i)+'.txt')).read_text(encoding='utf-8') if name in base['hashes'] else ''
 assert all(line.rstrip()==line for line in current.splitlines()),name
 diff.extend(difflib.unified_diff(prior.splitlines(keepends=True),current.splitlines(keepends=True),fromfile='candidate-before/'+name if prior else '/dev/null',tofile='candidate-after/'+name))
 candidate[name]={'before':base['hashes'].get(name),'after':sha(file)}
(PLAN/(PREFIX+'local.diff')).write_text(''.join(diff),encoding='utf-8')
write('hashes.json',{'head':base['head'],'protected_unchanged':len(protected),'protected_changes':changes,'candidate_files':candidate,'schema_pin':{'before':oldpin,'after':newpin},'diff_sha256':sha(PLAN/(PREFIX+'local.diff')),'runtime_logic_unchanged':True,'source_seam_adopted':False})
print('protected',len(protected),'schema paths',len(delta),'retained cases',len(cases),'native controls',len(green),flush=True)
