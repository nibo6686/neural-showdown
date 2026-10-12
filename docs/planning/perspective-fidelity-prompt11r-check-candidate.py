"""Revision-only read-only validation and review packet; never regenerates fixtures."""
import difflib, hashlib, json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PLAN=ROOT/'docs/planning'; PREFIX='perspective-fidelity-prompt11r-'
sys.path.insert(0,str(ROOT/'trainer/src'))
from neural.perspective_knowledge import check_knowledge_structure, KnowledgeStructureError
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda name,data:(PLAN/(PREFIX+name)).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONUTF8','PYTHONIOENCODING')}
env['PYTHONPATH']=str(ROOT/'trainer/src'); env['PYTHON']=sys.executable
commands=[]
for cwd,args,log in [
 ('sim-core',['npm.cmd','run','build'],'build.log'),
 ('.',[sys.executable,'-m','unittest','trainer.tests.test_perspective_knowledge'],'python-validation.log'),
 ('sim-core',['node','--test','--test-reporter=tap','dist/tests/perspective_knowledge.test.js'],'ts-validation.log'),
 ('.',[sys.executable,'docs/planning/'+PREFIX+'reproduce.py','green'],'green.log'),
 ('.',[sys.executable,'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'],'contract.log'),
 ('.',['git','diff','--check'],'diff-check.log')]:
 start=time.monotonic(); result=subprocess.run(args,cwd=ROOT/cwd,env=env,capture_output=True,timeout=120)
 (PLAN/(PREFIX+log)).write_bytes(result.stdout+result.stderr)
 commands.append({'cwd':cwd,'argv':args,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'log':PREFIX+log})
 write('validation.json',{'encoding_overrides_unset':True,'python':sys.executable,'commands':commands})
 print(log,'exit',result.returncode,flush=True)
 assert result.returncode==0,result.stderr.decode('utf-8',errors='replace')
# Recheck each retained case against the original runtime differential packet.
old=json.loads((PLAN/'perspective-fidelity-prompt11-matrix.json').read_text(encoding='utf-8'))
folder=ROOT/'docs/contracts/fixtures/perspective-knowledge-v1'; matrix=[]
for row in old['cases']:
 value=json.loads((folder/row['file']).read_bytes())
 try: check_knowledge_structure(value,row['required']); status={'status':'structure_valid','code':None}
 except KnowledgeStructureError as e: status={'status':'structural_reject','code':str(e)}
 assert status==row['python'],row['file']
 matrix.append({**row,'python':status})
node="""const fs=require('fs'),path=require('path'), k=require('./sim-core/dist/src/perspective_knowledge.js');
const rows=JSON.parse(fs.readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(rows.map(r=>{try{k.checkKnowledgeStructure(k.parseKnowledgeJson(fs.readFileSync(path.join('docs/contracts/fixtures/perspective-knowledge-v1',r.file))),r.required??undefined);return {status:'structure_valid',code:null}}catch(e){return {status:'structural_reject',code:e.message}}})));"""
result=subprocess.run(['node','-e',node],input=json.dumps(matrix).encode(),capture_output=True,cwd=ROOT,env=env,timeout=60); assert result.returncode==0
for row,ts in zip(matrix,json.loads(result.stdout)):
 assert row['python']==ts==row['typescript'],row['file']
write('matrix.json',{**old,'cases':matrix,'matches_original_case_classifications':True})
base=json.loads((PLAN/(PREFIX+'baseline.json')).read_text(encoding='utf-8'))
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==base['head']
protected={p:h for p,h in base['hashes'].items() if p not in base['owned']}
changes={p:{'baseline':h,'current':sha(ROOT/p) if (ROOT/p).is_file() else None} for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h}
assert not changes,changes
candidate={}; diff=[]
for i,p in enumerate(base['owned']):
 prior=(PLAN/(PREFIX+'baseline-'+str(i)+'.txt')).read_text(encoding='utf-8'); current=(ROOT/p).read_text(encoding='utf-8')
 candidate[p]={'before':base['hashes'][p],'after':sha(ROOT/p)}
 assert all(line.rstrip()==line for line in current.splitlines()),p
 diff.extend(difflib.unified_diff(prior.splitlines(keepends=True),current.splitlines(keepends=True),fromfile='candidate-before/'+p,tofile='candidate-after/'+p))
(PLAN/(PREFIX+'local.diff')).write_text(''.join(diff),encoding='utf-8')
oldbase=json.loads((PLAN/'perspective-fidelity-prompt11-baseline.json').read_text(encoding='utf-8'))
lead_changes={p:{'original_prompt11_baseline':h,'revision_baseline':base['hashes'].get(p)} for p,h in oldbase['hashes'].items() if base['hashes'].get(p)!=h}
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
external={p:sha(ROOT/p) for p in files if p not in base['hashes'] and not Path(p).name.startswith(PREFIX) and (ROOT/p).is_file()}
write('hashes.json',{'head':base['head'],'branch':base['branch'],'candidate_files':candidate,'protected_unchanged':len(protected),'protected_changes':changes,'external_arrivals':external,'lead_changes_before_revision':lead_changes,'diff_sha256':sha(PLAN/(PREFIX+'local.diff')),'original_prompt11_evidence_preserved':{p:h for p,h in protected.items() if Path(p).name.startswith('perspective-fidelity-prompt11-')}})
print('matrix',len(matrix),'protected',len(protected),'changed',len(candidate),'lead historical differences',list(lead_changes),flush=True)
