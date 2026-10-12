"""Read-only scoped preservation/differential packet; no fixture regeneration."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'docs/planning'
sys.path.insert(0,str(ROOT/'trainer/src'))
from neural.perspective_knowledge import CONTRACT_HASHES, check_knowledge_structure, KnowledgeStructureError

base=json.loads((PLAN/'perspective-fidelity-prompt11-baseline.json').read_text(encoding='utf-8'))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head==base['head']
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
for name,expected in base['hashes'].items(): assert (ROOT/name).is_file() and sha(ROOT/name)==expected,'protected changed '+name
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
external_additions=[name for name in files if name not in base['hashes'] and name not in base['owned'] and not name.startswith('docs/planning/perspective-fidelity-prompt11-')]
diff=[]; candidate={}
for name in base['owned']:
    file=ROOT/name; text=file.read_text(encoding='utf-8'); lines=text.splitlines(keepends=True)
    assert all(line.rstrip('\r\n')==line.rstrip() for line in lines),'whitespace '+name
    assert lines[-1].endswith('\n'),'newline '+name
    diff.extend(difflib.unified_diff([],lines,fromfile='/dev/null',tofile='candidate-after/'+name))
    candidate[name]={'before':None,'after':sha(file)}
(PLAN/'perspective-fidelity-prompt11-local.diff').write_text(''.join(diff),encoding='utf-8')
env={k:v for k,v in os.environ.items() if k.upper() not in ['PYTHONUTF8','PYTHONIOENCODING']}
env['PYTHONPATH']=str(ROOT/'trainer/src'); env['PYTHON']=str(Path(sys.executable))
commands=[]
for args in [[sys.executable,'docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py'],['git','diff','--check']]:
    result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
    commands.append({'argv':args,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==0,commands[-1]
folder=ROOT/'docs/contracts/fixtures/perspective-knowledge-v1'
positives=json.loads((folder/'case-manifest.json').read_text(encoding='utf-8'))['positive']
negatives=json.loads((folder/'negative-manifest.json').read_text(encoding='utf-8'))
cases=[{'file':n,'required':None,'document_expectation':'positive'} for n in positives]+[
    {'file':r['file'],'required':r['required_profile'],'document_expectation':r['rejection_code']} for r in negatives]
matrix=[]
for row in cases:
    wire=(folder/row['file']).read_bytes(); value=json.loads(wire)
    try: check_knowledge_structure(value,row['required']); status='structure_valid'; code=None
    except KnowledgeStructureError as error: status='structural_reject'; code=str(error)
    matrix.append({**row,'python':{'status':status,'code':code}})
node_code="""
const fs=require('node:fs'),path=require('node:path');
const core=require('./sim-core/dist/src/perspective_knowledge.js');
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(cases.map(r=>{
 try{core.checkKnowledgeStructure(core.parseKnowledgeJson(fs.readFileSync(path.join('docs/contracts/fixtures/perspective-knowledge-v1',r.file))),r.required??undefined);return {status:'structure_valid',code:null};}
 catch(e){return {status:'structural_reject',code:e.message};}
})));
"""
result=subprocess.run(['node','-e',node_code],cwd=ROOT,env=env,input=json.dumps(cases),capture_output=True,text=True,encoding='utf-8',timeout=60)
assert result.returncode==0,result.stderr
for row,node in zip(matrix,json.loads(result.stdout)):
    row['typescript']=node
    assert row['python']==node,'paired differential '+row['file']
for row in matrix[:len(positives)]: assert row['python']['status']=='structure_valid',row
semantic=[r['file'] for r in matrix[len(positives):] if r['python']['status']=='structure_valid']
packet={'scope':'Structural differential only; document semantic-negative expectations are not imported runtime authority',
        'positive':len(positives),'document_negative':len(negatives),'negative_structure_reject':len(negatives)-len(semantic),
        'semantic_or_assurance_unverified':semantic,'cases':matrix}
(PLAN/'perspective-fidelity-prompt11-matrix.json').write_text(json.dumps(packet,indent=2)+'\n',encoding='utf-8')
runtime_dependencies={str((folder/name).relative_to(ROOT)).replace('\\','/') : {'sha256':expected,'new_runtime_dependency':True} for name,expected in CONTRACT_HASHES.items()}
for name,row in runtime_dependencies.items(): assert sha(ROOT/name)==row['sha256']
outputs={'head':head,'protected_unchanged':len(base['hashes']),'candidate_files':candidate,
         'external_additions_not_written_by_this_task':{name:sha(ROOT/name) for name in external_additions},
         'diff_sha256':sha(PLAN/'perspective-fidelity-prompt11-local.diff'),'runtime_contract_data':runtime_dependencies,
         'manifest_or_attestation_updated':False,'matrix_summary':{k:v for k,v in packet.items() if k!='cases'},'commands':commands}
(PLAN/'perspective-fidelity-prompt11-hashes.json').write_text(json.dumps(outputs,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'protected_unchanged':len(base['hashes']),'candidate_files':len(candidate),'matrix':outputs['matrix_summary'],'contract_checker':json.loads(commands[0]['stdout']),'diff_check_exit':commands[1]['exit_code']}))
