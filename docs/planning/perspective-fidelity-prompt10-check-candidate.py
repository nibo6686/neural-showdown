"""Bounded candidate validation/preservation/diff packet; no runtime adoption."""
import difflib
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'docs/planning'
BASE=json.loads((PLAN/'perspective-fidelity-prompt10-baseline.json').read_text(encoding='utf-8'))
PYTHON='D:/Anaconda/envs/neuralgpu/python.exe'
env=dict(os.environ)
for key in ['PYTHONUTF8','PYTHONIOENCODING']: env.pop(key,None)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value): (PLAN/('perspective-fidelity-prompt10-'+name)).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
commands=[]
for args,expected in [
    ([PYTHON,'docs/planning/perspective-fidelity-prompt10-reproduce.py'],1),
    ([PYTHON,'docs/contracts/fixtures/perspective-knowledge-v1/author_fixtures.py'],0),
    ([PYTHON,'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'],0),
    (['git','diff','--check'],0),
]:
    result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    commands.append({'argv':args,'exit_code':result.returncode,'expected_exit':expected,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==expected,commands[-1]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head==BASE['head'],'HEAD changed'
owned=set(BASE['owned_existing'])
changed=[]; protected=[]
for name,expected in BASE['hashes'].items():
    path=ROOT/name
    actual=sha(path) if path.is_file() else None
    if actual!=expected:
        assert name in owned,'protected file changed '+name
        changed.append(name)
    elif name not in owned: protected.append(name)
for name in owned:
    snapshot=PLAN/'perspective-fidelity-prompt10-baseline-files'/name
    assert sha(snapshot)==BASE['hashes'][name],'baseline snapshot changed '+name
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
added=[n for n in names if n not in BASE['hashes']]
core=lambda n:n=='docs/contracts/PERSPECTIVE_KNOWLEDGE.md' or n.startswith('docs/contracts/fixtures/perspective-knowledge-v1/')
for name in added:
    assert core(name) or name.startswith('docs/planning/perspective-fidelity-prompt10-'),'out-of-scope new file '+name
core_names=sorted(set(changed+[n for n in added if core(n)]))
diff=[]; file_hashes={}
for name in core_names:
    before=(PLAN/'perspective-fidelity-prompt10-baseline-files'/name).read_text(encoding='utf-8').splitlines(keepends=True) if name in owned else []
    after=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
    assert all(line.rstrip('\r\n')==line.rstrip() for line in after),'candidate trailing whitespace '+name
    assert not after or after[-1].endswith('\n'),'candidate missing final newline '+name
    diff.extend(difflib.unified_diff(before,after,fromfile='candidate-before/'+name if before else '/dev/null',tofile='candidate-after/'+name))
    file_hashes[name]={'before':BASE['hashes'].get(name),'after':sha(ROOT/name)}
(PLAN/'perspective-fidelity-prompt10-local.diff').write_text(''.join(diff),encoding='utf-8')
dependencies=json.loads((PLAN/'perspective-fidelity-prompt9-dependencies.json').read_text(encoding='utf-8'))
for name,expected in dependencies['sources'].items(): assert sha(ROOT/name)==expected,'dependency changed '+name
new_sources=['sim-core/node_modules/pokemon-showdown/data/moves.ts','sim-core/node_modules/pokemon-showdown/data/conditions.ts','sim-core/node_modules/pokemon-showdown/sim/battle.ts']
write('dependencies.json',{'prior_dependencies_unchanged':len(dependencies['sources']),'selected_rules':{n:sha(ROOT/n) for n in new_sources},'network':False})
packet=json.loads((PLAN/'perspective-fidelity-prompt7-digest-inputs.json').read_text(encoding='utf-8'))
digest=hashlib.sha256(); drift=[]
for row in packet['inputs']:
    raw=(ROOT/row['repo_path']).read_bytes()
    digest.update(row['manifest_path'].encode()+b'\0'+raw.replace(b'\r\n',b'\n')+b'\0')
    if hashlib.sha256(raw).hexdigest()!=row['raw_sha256']: drift.append(row['repo_path'])
assert digest.hexdigest()=='8424f64d539a6528a18531f91ee5606200b69c0f98193d4c3e6fd86de2e0c7fc'
validation={'scope':'Contract/fixture only; no production acceptance','head':head,'encoding_overrides':{k:env.get(k) for k in ['PYTHONUTF8','PYTHONIOENCODING']},'commands':commands,
 'checker_results':json.loads(commands[2]['stdout']),'protected_unchanged':len(protected),'baseline_snapshots_unchanged':len(owned),
 'changed_existing':len(changed),'new_core_files':len([n for n in core_names if n not in owned]),'candidate_files_direct_whitespace_checked':len(core_names),'provenance_comparison_digest':digest.hexdigest(),'drift_inputs':drift,'attestation_updated':False}
write('validation.json',validation)
write('hashes.json',{'head':head,'candidate_relative':file_hashes,'protected_unchanged':{n:BASE['hashes'][n] for n in protected},'diff_sha256':sha(PLAN/'perspective-fidelity-prompt10-local.diff')})
print(json.dumps({k:v for k,v in validation.items() if k!='commands'}))
