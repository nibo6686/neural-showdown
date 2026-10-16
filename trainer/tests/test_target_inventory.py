"""Static candidate inspection and historical reader/lookup parity, no native engine execution."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from neural.version_profile import historical_lookup_data,load_inactive_target_inventory
ROOT=Path(__file__).resolve().parents[2]
def test_historical_fresh_process_and_literals():
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'trainer/src')
    for k in list(env):
        if k in ('PYTHONUTF8','PYTHONIOENCODING') or k.startswith(('REPORT_','PROMPT')):env.pop(k)
    code="""
import json
from pathlib import Path
from neural.version_profile import historical_lookup_data
from neural import pipeline_record as r
original=Path.read_bytes
def guarded(self,*a,**kw):
    if 'node_modules/pokemon-showdown' in str(self):raise AssertionError('installed engine lookup prohibited')
    return original(self,*a,**kw)
Path.read_bytes=guarded
lookup=historical_lookup_data();assert lookup['species']['pikachu']['types']==('Electric',)
f=json.loads(Path('docs/planning/perspective-fidelity-prompt31-reader-fixtures.json').read_text(encoding='utf-8'))
g=json.loads(Path('docs/planning/perspective-fidelity-prompt31-old-publication-goldens.json').read_text(encoding='utf-8'))
for name,fn in [('result',r.validate_historical_pipeline_episode_result),('sweep',r.validate_historical_pipeline_episode_publication_sweep)]:
    out=json.dumps(fn(f[name]),ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\\n';assert out==g[name]['api_literal']
print(json.dumps({'historical_outputs_preserved':True,'installed_lookup_access':False}))
"""
    p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True,timeout=20)
    assert p.returncode==0,p.stderr
    print('P35_WITNESS '+p.stdout.strip())

def test_candidate_integrity_and_immutability(tmp_path):
    candidate=load_inactive_target_inventory();assert candidate['adopted'] is False
    assert len(candidate['format_provenance']['candidate_population']['species'])==509
    with pytest.raises(TypeError):historical_lookup_data()['species']['pikachu']['types'][0]='Fire'
    old=json.loads((ROOT/'sim-core/simulator_coverage/pokemon-showdown-0.11.11-gen9randombattle.json').read_text(encoding='utf-8'))
    old['effect_discovery']['computed_add_volatile_calls']=[]
    path=tmp_path/'rehashable-omission.json';path.write_text(json.dumps(old))
    with pytest.raises(ValueError,match='version-asset-integrity'):load_inactive_target_inventory(path)
    with pytest.raises(ValueError,match='missing-version-asset'):load_inactive_target_inventory(tmp_path/'absent.json')
    print('P35_WITNESS '+json.dumps({'python_candidate_omission_rejected':True,'missing_rejected':True,'immutable_historical_data':True,'target_runtime':'UNEXECUTED'}))
