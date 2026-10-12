"""Prompt12 blocker packet validation; no shared source/contract writes."""
import json,hashlib,subprocess,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PLAN=ROOT/'docs/planning'; prefix='perspective-fidelity-prompt12-'
env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONUTF8','PYTHONIOENCODING')}; env['PYTHONPATH']=str(ROOT/'trainer/src'); env['PYTHON']=sys.executable
commands=[]
for cwd,args,log in [
 ('sim-core',['npm.cmd','run','build'],'build.log'),
 ('.',['node','docs/planning/'+prefix+'legacy-witness.cjs'],'legacy-validation.log'),
 ('.',[sys.executable,'docs/planning/'+prefix+'reproduce.py'],'reproduction.log'),
 ('.',[sys.executable,'-m','unittest','trainer.tests.test_perspective_knowledge','trainer.tests.test_pipeline_record.PipelineRecordTest.test_valid_linked_bundle_builds_checkpoint_free_data_record','trainer.tests.test_pipeline_record.PipelineRecordTest.test_unicode_prefix_hashes_keep_typescript_and_data_envelopes_distinct'],'python-validation.log'),
 ('sim-core',['node','--test','--test-reporter=tap','dist/tests/perspective_knowledge.test.js'],'ts-validation.log'),
 ('.',[sys.executable,'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'],'contract.log'),
 ('.',['git','diff','--check'],'diff-check.log')]:
 start=time.monotonic(); result=subprocess.run(args,cwd=ROOT/cwd,env=env,capture_output=True,timeout=120)
 (PLAN/(prefix+log)).write_bytes(result.stdout+result.stderr)
 commands.append({'cwd':cwd,'argv':args,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'log':prefix+log})
 (PLAN/(prefix+'validation.json')).write_text(json.dumps({'encoding_overrides_unset':True,'python':sys.executable,'commands':commands},indent=2)+'\n',encoding='utf-8')
 print(log,'exit',result.returncode,flush=True); assert result.returncode==0,result.stderr.decode('utf-8',errors='replace')
base=json.loads((PLAN/(prefix+'baseline.json')).read_bytes()); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==base['head']
changes={p:{'before':h,'after':sha(ROOT/p) if (ROOT/p).is_file() else None} for p,h in base['hashes'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h}
assert not changes,changes
for p in base['owned']: assert not (ROOT/p).exists(),'unexpected runtime write '+p
(PLAN/(prefix+'local.diff')).write_bytes(b'')
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
external={p:sha(ROOT/p) for p in files if p not in base['hashes'] and not Path(p).name.startswith(prefix) and (ROOT/p).is_file()}
oldbase=json.loads((PLAN/'perspective-fidelity-prompt11r-hashes.json').read_bytes())
for p,entry in oldbase['candidate_files'].items(): assert sha(ROOT/p)==entry['after']
(PLAN/(prefix+'hashes.json')).write_text(json.dumps({'head':base['head'],'branch':base['branch'],'protected_unchanged':len(base['hashes']),'protected_changes':changes,'external_arrivals':external,'accepted_prompt11r_candidate_hashes':oldbase['candidate_files'],'runtime_candidate_created':False,'owned_runtime_paths_absent':base['owned'],'runtime_diff_sha256':sha(PLAN/(prefix+'local.diff'))},indent=2)+'\n',encoding='utf-8'); print('preserved',len(base['hashes']),'runtime writes0',flush=True)
